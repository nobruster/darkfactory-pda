#!/usr/bin/env node

import { randomBytes } from "node:crypto";
import { chmod, mkdtemp, rm } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";

import { createAgentRegistry } from "./acp/agent-registry.mjs";
import { createRequestHandler } from "./app.mjs";
import { ArtifactStore } from "./artifact-store.mjs";
import {
  resolveServerConfig,
  SERVER_USAGE,
} from "./config.mjs";
import { createCvgRunner } from "./cvg.mjs";
import { createMethodologyProvider } from "./methodology.mjs";
import { createWorkspaceSnapshotValidator } from "./schema.mjs";
import { createAskService } from "./ask-service.mjs";
import { SnapshotService } from "./service.mjs";
import { buildWorkspaceSnapshot } from "./snapshot.mjs";

function acpEnvironment(base, { codex = false } = {}) {
  const allowed = [
    "HOME",
    "PATH",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TZ",
    "SHELL",
    "USER",
    "CODEX_HOME",
    "CLAUDE_CONFIG_DIR",
    "XDG_CONFIG_HOME",
  ];
  const environment = {};
  for (const name of allowed) {
    if (typeof base[name] === "string" && base[name].length > 0) {
      environment[name] = base[name];
    }
  }
  environment.NO_BROWSER = "1";
  environment.NO_COLOR = "1";
  if (codex) environment.INITIAL_AGENT_MODE = "read-only";
  return environment;
}

async function main() {
  let config;
  try {
    config = await resolveServerConfig({ argv: process.argv.slice(2) });
  } catch (error) {
    process.stderr.write(`cockpit: ${error.message}\n\n${SERVER_USAGE}`);
    process.exitCode = 2;
    return;
  }
  if (config.help) {
    process.stdout.write(SERVER_USAGE);
    return;
  }

  const runner = createCvgRunner({ config });
  let validateSnapshot;
  try {
    validateSnapshot = await createWorkspaceSnapshotValidator({ config });
  } catch (error) {
    process.stderr.write(`cockpit: ${error.message}\n`);
    process.exitCode = 2;
    return;
  }
  const artifactStore = new ArtifactStore({
    projectRoot: config.projectRoot,
  });
  const service = new SnapshotService({
    build: () =>
      buildWorkspaceSnapshot({
        runner,
        artifactStore,
        validateSnapshot,
      }),
  });
  const askSessionRoot = await mkdtemp(
    path.join(tmpdir(), "converge-cockpit-ask-"),
  );
  await chmod(askSessionRoot, 0o500);
  const registry = createAgentRegistry({
    projectRoot: config.projectRoot,
    sessionRoot: askSessionRoot,
    adapters: [
      {
        id: "codex",
        label: "Codex",
        executable: config.codexAcpBin,
        args: [],
        environment: acpEnvironment(process.env, { codex: true }),
        requiredMode: "read-only",
        contextIsolation: "unsupported",
        blockedReason:
          "Codex is disabled because this ACP adapter cannot suppress local read and search tools.",
      },
      {
        id: "claude",
        label: "Claude Agent",
        executable: config.claudeAcpBin,
        args: [],
        environment: acpEnvironment(process.env),
        requiredMode: "plan",
        disableBuiltInTools: true,
        contextIsolation: config.claudeAcpContextIsolation,
        ...(config.claudeAcpBlockedReason
          ? { blockedReason: config.claudeAcpBlockedReason }
          : {}),
      },
    ],
  });
  const askService = createAskService({
    registry,
    snapshotService: service,
    artifactStore,
    methodologyProvider: createMethodologyProvider({ runner }),
  });
  const askRequestToken = randomBytes(24).toString("base64url");
  const handler = createRequestHandler({
    config,
    service,
    artifactStore,
    askService,
    askRequestToken,
  });
  const server = createServer(handler);

  server.on("clientError", (_error, socket) => {
    socket.end("HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n");
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(config.port, config.host, resolve);
  });

  const displayHost = config.host === "::1" ? "[::1]" : config.host;
  process.stdout.write(
    `Converge Cockpit bridge\n` +
      `  mode    read-only\n` +
      `  project ${config.projectRoot}\n` +
      `  ask     ACP adapters configured; availability is checked on request\n` +
      `  api     http://${displayHost}:${config.port}/api/health\n`,
  );

  let stopping = false;
  const shutdown = async () => {
    if (stopping) return;
    stopping = true;
    await askService.close();
    await chmod(askSessionRoot, 0o700).catch(() => {});
    await rm(askSessionRoot, { recursive: true, force: true }).catch(() => {});
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 2_000).unref();
  };
  process.once("SIGINT", () => void shutdown());
  process.once("SIGTERM", () => void shutdown());
}

await main();
