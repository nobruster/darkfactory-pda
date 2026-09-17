#!/usr/bin/env node

import { spawn } from "node:child_process";
import { access } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const APP_ROOT = path.resolve(SCRIPT_DIR, "..");
const SERVER_ENTRY = path.join(APP_ROOT, "server", "index.mjs");
const VITE_ENTRY = path.join(APP_ROOT, "node_modules", "vite", "bin", "vite.js");

function readOptions(argv) {
  const options = {
    cvgHome: process.env.CVG_HOME,
    projectRoot: process.env.CVG_PROJECT_ROOT,
  };
  const forward = [];

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--cvg-home" || argument === "--project-root") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) {
        throw new Error(`${argument} requires a value`);
      }
      if (argument === "--cvg-home") {
        options.cvgHome = value;
      } else {
        options.projectRoot = value;
      }
      forward.push(argument, value);
      index += 1;
    } else if (argument.startsWith("--cvg-home=")) {
      options.cvgHome = argument.slice("--cvg-home=".length);
      forward.push(argument);
    } else if (argument.startsWith("--project-root=")) {
      options.projectRoot = argument.slice("--project-root=".length);
      forward.push(argument);
    } else {
      forward.push(argument);
    }
  }

  if (!options.cvgHome || !options.projectRoot) {
    throw new Error(
      "CVG_HOME and CVG_PROJECT_ROOT are required; pass --cvg-home and --project-root or set both environment variables",
    );
  }
  return { ...options, forward };
}

async function main() {
  const options = readOptions(process.argv.slice(2));
  try {
    await access(VITE_ENTRY);
  } catch {
    throw new Error(`Vite is not installed at ${VITE_ENTRY}; run npm install first`);
  }

  const environment = {
    ...process.env,
    CVG_HOME: options.cvgHome,
    CVG_PROJECT_ROOT: options.projectRoot,
  };
  const children = [
    spawn(process.execPath, [SERVER_ENTRY, ...options.forward], {
      cwd: APP_ROOT,
      env: environment,
      stdio: "inherit",
    }),
    spawn(process.execPath, [VITE_ENTRY, "--host", "127.0.0.1"], {
      cwd: APP_ROOT,
      env: environment,
      stdio: "inherit",
    }),
  ];

  let stopping = false;
  const stop = (signal = "SIGTERM") => {
    if (stopping) {
      return;
    }
    stopping = true;
    for (const child of children) {
      if (!child.killed) {
        child.kill(signal);
      }
    }
  };

  process.once("SIGINT", () => stop("SIGINT"));
  process.once("SIGTERM", () => stop("SIGTERM"));

  for (const child of children) {
    child.once("error", (error) => {
      process.stderr.write(`cockpit dev: ${error.message}\n`);
      process.exitCode = 1;
      stop();
    });
    child.once("exit", (code, signal) => {
      if (!stopping) {
        process.exitCode = code ?? (signal ? 1 : 0);
        stop();
      }
    });
  }

  await Promise.all(
    children.map(
      (child) =>
        new Promise((resolve) => {
          child.once("close", resolve);
        }),
    ),
  );
}

main().catch((error) => {
  process.stderr.write(`cockpit dev: ${error.message}\n`);
  process.exitCode = 2;
});
