import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { createAgentRegistry } from "./acp/agent-registry.mjs";

test("AgentRegistry freezes fixed executable, argv, cwd, and safe environment", async () => {
  const projectRoot = path.resolve(".");
  const sessionRoot = path.resolve("server/test-fixtures");
  const registry = createAgentRegistry({
    projectRoot,
    sessionRoot,
    adapters: [
      {
        id: "codex",
        label: "Codex",
        executable: process.execPath,
        args: ["fixed-adapter.mjs"],
        environment: {
          HOME: process.env.HOME,
          PATH: process.env.PATH,
          INITIAL_AGENT_MODE: "read-only",
          USER: process.env.USER,
        },
        requiredMode: "read-only",
        disableBuiltInTools: true,
        contextIsolation: "verified",
      },
    ],
  });
  const adapter = registry.get("codex");
  assert.equal(adapter.cwd, sessionRoot);
  assert.equal(adapter.requiredMode, "read-only");
  assert.equal(adapter.disableBuiltInTools, true);
  assert.equal(adapter.contextIsolation, "verified");
  assert.equal(adapter.environment.USER, process.env.USER);
  assert.deepEqual(adapter.args, ["fixed-adapter.mjs"]);
  assert.ok(Object.isFrozen(adapter));
  assert.ok(Object.isFrozen(adapter.args));
  assert.equal((await registry.list())[0].availability, "available");
  assert.equal(Object.hasOwn((await registry.list())[0], "executable"), false);
});

test("AgentRegistry exposes context-isolation failures as blocked", async () => {
  const projectRoot = path.resolve(".");
  const registry = createAgentRegistry({
    projectRoot,
    adapters: [
      {
        id: "codex",
        label: "Codex",
        executable: path.join(projectRoot, "missing-unverified-adapter"),
        args: [],
        environment: {
          HOME: process.env.HOME,
          PATH: process.env.PATH,
          INITIAL_AGENT_MODE: "read-only",
        },
        requiredMode: "read-only",
        contextIsolation: "unsupported",
        blockedReason: "The adapter cannot suppress local read tools.",
      },
    ],
  });

  const [agent] = await registry.list();
  assert.equal(agent.availability, "blocked");
  assert.equal(agent.reason, "The adapter cannot suppress local read tools.");
});

test("AgentRegistry rejects browser-like command strings, secrets, and write modes", () => {
  const projectRoot = path.resolve(".");
  assert.throws(
    () => createAgentRegistry({
      projectRoot,
      adapters: [{ id: "codex", label: "Codex", executable: "npx", args: [], environment: {} }],
    }),
    /absolute path/,
  );
  assert.throws(
    () => createAgentRegistry({
      projectRoot,
      adapters: [{
        id: "codex",
        label: "Codex",
        executable: process.execPath,
        args: [],
        environment: { OPENAI_API_KEY: "secret" },
      }],
    }),
    /not allowed/,
  );
  assert.throws(
    () => createAgentRegistry({
      projectRoot,
      adapters: [{
        id: "codex",
        label: "Codex",
        executable: process.execPath,
        args: [],
        environment: { INITIAL_AGENT_MODE: "agent-full-access" },
      }],
    }),
    /read-only/,
  );
  assert.throws(
    () =>
      createAgentRegistry({
        projectRoot,
        adapters: [
          {
            id: "codex",
            label: "Codex",
            executable: process.execPath,
            args: [],
            environment: {},
            requiredMode: "agent-full-access",
          },
        ],
      }),
    /requiredMode/,
  );
});
