import { constants } from "node:fs";
import { access, realpath } from "node:fs/promises";
import path from "node:path";

const AGENT_ID = /^[a-z0-9][a-z0-9-]{0,47}$/;
const SAFE_AGENT_MODES = new Set(["read-only", "plan"]);
const CONTEXT_ISOLATION = new Set(["verified", "unsupported"]);
const SAFE_ENVIRONMENT_NAMES = new Set([
  "CLAUDE_CONFIG_DIR",
  "CODEX_HOME",
  "CODEX_PATH",
  "HOME",
  "INITIAL_AGENT_MODE",
  "LANG",
  "LC_ALL",
  "LC_CTYPE",
  "NO_BROWSER",
  "NO_COLOR",
  "PATH",
  "SHELL",
  "TEMP",
  "TMP",
  "TMPDIR",
  "TZ",
  "USER",
  "XDG_CONFIG_HOME",
]);

function assertText(value, label, maxLength = 512) {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    value.length > maxLength ||
    value.includes("\0")
  ) {
    throw new TypeError(`${label} must be a non-empty bounded string`);
  }
  return value;
}

function freezeEnvironment(environment = {}) {
  if (
    typeof environment !== "object" ||
    environment === null ||
    Array.isArray(environment)
  ) {
    throw new TypeError("ACP adapter environment must be an object");
  }
  const result = {};
  for (const [name, value] of Object.entries(environment)) {
    if (!SAFE_ENVIRONMENT_NAMES.has(name)) {
      throw new TypeError(`ACP adapter environment variable is not allowed: ${name}`);
    }
    result[name] = assertText(value, `ACP adapter environment ${name}`, 4096);
  }
  if (
    Object.hasOwn(result, "INITIAL_AGENT_MODE") &&
    result.INITIAL_AGENT_MODE !== "read-only"
  ) {
    throw new TypeError("Ask Converge only accepts INITIAL_AGENT_MODE=read-only");
  }
  return Object.freeze(result);
}

function normalizeAdapter(candidate, sessionRoot) {
  if (typeof candidate !== "object" || candidate === null || Array.isArray(candidate)) {
    throw new TypeError("ACP adapter configuration must be an object");
  }
  if (!AGENT_ID.test(candidate.id)) {
    throw new TypeError("ACP adapter id must be a lowercase stable identifier");
  }
  const executable = assertText(candidate.executable, "ACP adapter executable", 4096);
  if (!path.isAbsolute(executable)) {
    throw new TypeError("ACP adapter executable must be an absolute path");
  }
  if (
    !Array.isArray(candidate.args) ||
    candidate.args.some((argument) =>
      typeof argument !== "string" || argument.length > 4096 || argument.includes("\0"))
  ) {
    throw new TypeError("ACP adapter args must be a bounded string array");
  }
  let requiredMode = null;
  if (candidate.requiredMode !== undefined) {
    if (!SAFE_AGENT_MODES.has(candidate.requiredMode)) {
      throw new TypeError(
        "ACP adapter requiredMode must be read-only or plan",
      );
    }
    requiredMode = candidate.requiredMode;
  }
  const contextIsolation = candidate.contextIsolation ?? "unsupported";
  if (!CONTEXT_ISOLATION.has(contextIsolation)) {
    throw new TypeError(
      "ACP adapter contextIsolation must be verified or unsupported",
    );
  }
  const blockedReason =
    contextIsolation === "unsupported"
      ? assertText(
          candidate.blockedReason ??
            "This ACP adapter cannot enforce context-only operation.",
          "ACP adapter blockedReason",
          512,
        )
      : null;
  return Object.freeze({
    id: candidate.id,
    label: assertText(candidate.label, "ACP adapter label", 80),
    executable: path.normalize(executable),
    args: Object.freeze([...candidate.args]),
    cwd: sessionRoot,
    environment: freezeEnvironment(candidate.environment),
    requiredMode,
    disableBuiltInTools: candidate.disableBuiltInTools === true,
    contextIsolation,
    blockedReason,
  });
}

export class AgentRegistry {
  constructor({ projectRoot, sessionRoot = projectRoot, adapters = [] }) {
    const resolvedRoot = path.resolve(assertText(projectRoot, "projectRoot", 4096));
    if (!path.isAbsolute(projectRoot)) {
      throw new TypeError("projectRoot must be an absolute path");
    }
    const resolvedSessionRoot = path.resolve(
      assertText(sessionRoot, "sessionRoot", 4096),
    );
    if (!path.isAbsolute(sessionRoot)) {
      throw new TypeError("sessionRoot must be an absolute path");
    }
    this.projectRoot = resolvedRoot;
    this.sessionRoot = resolvedSessionRoot;
    this.adapters = new Map();
    for (const candidate of adapters) {
      const adapter = normalizeAdapter(candidate, resolvedSessionRoot);
      if (this.adapters.has(adapter.id)) {
        throw new TypeError(`duplicate ACP adapter id: ${adapter.id}`);
      }
      this.adapters.set(adapter.id, adapter);
    }
  }

  get(agentId) {
    return this.adapters.get(agentId) ?? null;
  }

  async list() {
    return Promise.all(
      [...this.adapters.values()].map(async (adapter) => {
        if (adapter.contextIsolation !== "verified") {
          return Object.freeze({
            id: adapter.id,
            label: adapter.label,
            availability: "blocked",
            connection: "not_started",
            reason: adapter.blockedReason,
          });
        }
        let availability = "available";
        let reason = null;
        try {
          const canonical = await realpath(adapter.executable);
          await access(canonical, constants.X_OK);
        } catch {
          availability = "unavailable";
          reason = "ACP adapter executable is unavailable.";
        }
        return Object.freeze({
          id: adapter.id,
          label: adapter.label,
          availability,
          connection: "not_started",
          reason: availability === "available" ? null : reason,
        });
      }),
    );
  }
}

export function createAgentRegistry(options) {
  return new AgentRegistry(options);
}

export { SAFE_ENVIRONMENT_NAMES };
