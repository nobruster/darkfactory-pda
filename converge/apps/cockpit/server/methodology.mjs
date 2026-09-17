import { createHash } from "node:crypto";

const MAX_MANIFEST_BYTES = 128 * 1024;

function methodologyError(code, message, options = {}) {
  const error = new Error(message, options);
  error.code = code;
  return error;
}

function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function extractMethodologyManifest(result) {
  if (result?.timedOut) {
    throw methodologyError(
      "CLI_METHODOLOGY_TIMEOUT",
      "cvg agent-context exceeded the read-only bridge timeout",
    );
  }
  const document = result?.document;
  if (
    result?.exitCode !== 0 ||
    result?.parsed !== true ||
    !isRecord(document) ||
    document.schema_version !== "1.0" ||
    document.tool !== "cvg" ||
    typeof document.version !== "string" ||
    document.version.length === 0 ||
    typeof document.role !== "string" ||
    !isRecord(document.contracts) ||
    !Array.isArray(document.commands) ||
    document.commands.length === 0 ||
    document.commands.length > 256 ||
    document.commands.some((command) =>
      !isRecord(command) ||
      typeof command.name !== "string" ||
      typeof command.description !== "string")
  ) {
    throw methodologyError(
      "CLI_METHODOLOGY_INVALID",
      "cvg agent-context did not emit the expected methodology manifest",
    );
  }
  const serialized = JSON.stringify(document);
  if (Buffer.byteLength(serialized, "utf8") > MAX_MANIFEST_BYTES) {
    throw methodologyError(
      "CLI_METHODOLOGY_TOO_LARGE",
      "cvg agent-context exceeded the bounded methodology manifest size",
    );
  }
  return Object.freeze({
    document,
    digest: createHash("sha256").update(serialized).digest("hex"),
  });
}

export function createMethodologyProvider({ runner }) {
  if (!runner || typeof runner.run !== "function") {
    throw new TypeError("createMethodologyProvider requires a cvg runner");
  }
  let cached = null;
  let inFlight = null;
  return async function getMethodology() {
    if (cached) return cached;
    if (!inFlight) {
      inFlight = runner
        .run("agentContext")
        .then(extractMethodologyManifest)
        .then((manifest) => {
          cached = manifest;
          return manifest;
        })
        .finally(() => {
          inFlight = null;
        });
    }
    return inFlight;
  };
}

export { MAX_MANIFEST_BYTES };
