import { redactSensitiveText } from "./security.mjs";

export const ASK_LIMITS = Object.freeze({
  maxAgentIdLength: 48,
  maxArtifactCount: 3,
  // The Converge methodology manifest alone serializes past 21 KiB, so a 96 KiB
  // ceiling silently forced every section through the compaction profiles in
  // ask-context.mjs. The bound is raised so full-fidelity method and project
  // evidence both fit; see METHOD_CONTEXT_BYTES for the per-section split.
  maxContextBytes: 128 * 1024,
  maxConfigSelections: 8,
  maxEventBytes: 256 * 1024,
  maxEvents: 256,
  maxHistoryBytes: 12 * 1024,
  maxHistoryMessageBytes: 4 * 1024,
  maxHistoryMessages: 6,
  maxPromptBytes: 16 * 1024,
  maxSessionIdLength: 96,
});

const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._:-]*$/;
const ENTITY_KINDS = new Set([
  "pass",
  "task",
  "run",
  "receipt",
  "health",
  "signal",
  "issue",
  "artifact",
  "swimlane",
  "leg",
]);
const HISTORY_ROLES = new Set(["user", "assistant"]);
const HISTORY_KEYS = new Set(["role", "text"]);

const PUBLIC_ERRORS = Object.freeze({
  ASK_AGENT_FAILED: [502, "The selected agent could not complete this request.", true],
  ASK_AGENT_NOT_FOUND: [404, "The selected ACP agent is not configured.", false],
  ASK_AGENT_UNAVAILABLE: [503, "The selected ACP agent is unavailable.", true],
  ASK_ARTIFACT_INVALID: [400, "One or more selected artifacts are invalid.", false],
  ASK_AUTH_REQUIRED: [401, "The selected agent is not authenticated on this machine. Sign in with its local CLI, then try again.", true],
  ASK_AUTH_UNSUPPORTED: [400, "This authentication method is not supported by Ask Converge.", false],
  ASK_BUSY: [409, "This Ask session already has an active turn.", true],
  ASK_CANCELLED: [409, "The Ask turn was cancelled.", true],
  ASK_CONFIG_REJECTED: [400, "The selected model or reasoning option is not offered by this agent.", false],
  ASK_CONFIG_UNSUPPORTED: [409, "This agent does not expose selectable model options.", false],
  ASK_CONTEXT_LIMIT: [413, "The selected evidence is too large for an Ask turn.", false],
  ASK_ENTITY_NOT_FOUND: [404, "The selected workspace entity is unavailable.", false],
  ASK_INVALID_REQUEST: [400, "The Ask request does not match the expected contract.", false],
  ASK_METHODOLOGY_UNAVAILABLE: [503, "The Converge methodology reference is unavailable. Restart the Cockpit after verifying the local Converge CLI.", true],
  ASK_OUTPUT_LIMIT: [413, "The agent response exceeded the Ask output limit.", false],
  ASK_PROTOCOL_MISMATCH: [502, "The selected agent does not support ACP v1.", false],
  ASK_SESSION_EXPIRED: [410, "This Ask session has expired.", false],
  ASK_SESSION_LIMIT: [429, "The local Ask session limit has been reached.", true],
  ASK_SESSION_NOT_FOUND: [404, "The Ask session is unavailable.", false],
  ASK_SNAPSHOT_STALE: [409, "The workspace changed. Refresh before asking again.", true],
  ASK_SOURCE_NOT_LIVE: [409, "Ask Converge requires a live workspace snapshot.", true],
  ASK_TIMEOUT: [504, "The selected agent did not respond in time.", true],
  ASK_TURN_ALREADY_USED: [409, "This ephemeral Ask session has already been used.", false],
});

export class AskError extends Error {
  constructor(code, { cause } = {}) {
    const definition = PUBLIC_ERRORS[code] ?? PUBLIC_ERRORS.ASK_AGENT_FAILED;
    super(definition[1], { cause });
    this.name = "AskError";
    this.code = PUBLIC_ERRORS[code] ? code : "ASK_AGENT_FAILED";
    this.statusCode = definition[0];
    this.retryable = definition[2];
  }
}

function isPlainObject(value) {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function hasOnlyKeys(value, allowed) {
  return Object.keys(value).every((key) => allowed.has(key));
}

function validIdentifier(value, maxLength) {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= maxLength &&
    IDENTIFIER.test(value)
  );
}

function utf8Length(value) {
  return Buffer.byteLength(value, "utf8");
}

function parseEntity(value) {
  if (
    !isPlainObject(value) ||
    !hasOnlyKeys(value, new Set(["kind", "id"])) ||
    !ENTITY_KINDS.has(value.kind) ||
    !validIdentifier(value.id, 160)
  ) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  return Object.freeze({ kind: value.kind, id: value.id });
}

function parseContext(value) {
  if (value === undefined) {
    return Object.freeze({ entity: null, artifactIds: Object.freeze([]) });
  }
  if (
    !isPlainObject(value) ||
    !hasOnlyKeys(value, new Set(["entity", "artifactIds"]))
  ) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  const entity = value.entity === undefined || value.entity === null
    ? null
    : parseEntity(value.entity);
  const artifactIds = value.artifactIds ?? [];
  if (
    !Array.isArray(artifactIds) ||
    artifactIds.length > ASK_LIMITS.maxArtifactCount ||
    artifactIds.some((id) => !validIdentifier(id, 160)) ||
    new Set(artifactIds).size !== artifactIds.length
  ) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  return Object.freeze({ entity, artifactIds: Object.freeze([...artifactIds]) });
}

export function parseAskHistory(value) {
  if (value === undefined) return Object.freeze([]);
  if (!Array.isArray(value) || value.length > ASK_LIMITS.maxHistoryMessages) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  let totalBytes = 0;
  const messages = value.map((candidate) => {
    if (
      !isPlainObject(candidate) ||
      !hasOnlyKeys(candidate, HISTORY_KEYS) ||
      !HISTORY_ROLES.has(candidate.role) ||
      typeof candidate.text !== "string"
    ) {
      throw new AskError("ASK_INVALID_REQUEST");
    }
    const text = candidate.text.trim();
    const messageBytes = utf8Length(text);
    totalBytes += messageBytes;
    if (
      text.length === 0 ||
      messageBytes > ASK_LIMITS.maxHistoryMessageBytes ||
      totalBytes > ASK_LIMITS.maxHistoryBytes
    ) {
      throw new AskError("ASK_INVALID_REQUEST");
    }
    return Object.freeze({
      role: candidate.role,
      text: redactSensitiveText(text),
    });
  });
  return Object.freeze(messages);
}

/**
 * Session configuration selections (model, reasoning level) requested for a
 * turn. Only the option identity and value cross this boundary; which
 * categories may be applied is decided by the ACP client, so a selection can
 * never reach a `mode` selector and weaken safe mode.
 */
export function parseAskConfigSelections(value) {
  if (value === undefined || value === null) return Object.freeze([]);
  if (!Array.isArray(value) || value.length > ASK_LIMITS.maxConfigSelections) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  const selections = value.map((candidate) => {
    if (
      !isPlainObject(candidate) ||
      !hasOnlyKeys(candidate, new Set(["configId", "type", "value"])) ||
      !validIdentifier(candidate.configId, 160)
    ) {
      throw new AskError("ASK_INVALID_REQUEST");
    }
    if (candidate.type === "boolean") {
      if (typeof candidate.value !== "boolean") {
        throw new AskError("ASK_INVALID_REQUEST");
      }
      return Object.freeze({
        configId: candidate.configId,
        type: "boolean",
        value: candidate.value,
      });
    }
    if (candidate.type !== "select" || !validIdentifier(candidate.value, 160)) {
      throw new AskError("ASK_INVALID_REQUEST");
    }
    return Object.freeze({
      configId: candidate.configId,
      type: "select",
      value: candidate.value,
    });
  });
  if (new Set(selections.map((entry) => entry.configId)).size !== selections.length) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  return Object.freeze(selections);
}

export function parseCreateAskSessionRequest(value) {
  if (
    !isPlainObject(value) ||
    !hasOnlyKeys(value, new Set(["agentId", "snapshotId", "context", "config"])) ||
    !validIdentifier(value.agentId, ASK_LIMITS.maxAgentIdLength) ||
    !validIdentifier(value.snapshotId, 160)
  ) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  return Object.freeze({
    agentId: value.agentId,
    snapshotId: value.snapshotId,
    context: parseContext(value.context),
    config: parseAskConfigSelections(value.config),
  });
}

export function parseAskAgentIdRequest(value) {
  if (
    !isPlainObject(value) ||
    !hasOnlyKeys(value, new Set(["agentId"])) ||
    !validIdentifier(value.agentId, ASK_LIMITS.maxAgentIdLength)
  ) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  return Object.freeze({ agentId: value.agentId });
}

export function parseAskTurnRequest(value) {
  if (
    !isPlainObject(value) ||
    !hasOnlyKeys(value, new Set(["text", "snapshotId", "history"])) ||
    typeof value.text !== "string" ||
    value.text.trim().length === 0 ||
    utf8Length(value.text) > ASK_LIMITS.maxPromptBytes ||
    !validIdentifier(value.snapshotId, 160)
  ) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  return Object.freeze({
    text: value.text.trim(),
    snapshotId: value.snapshotId,
    history: parseAskHistory(value.history),
  });
}

export function parseAskAuthenticationRequest(value) {
  if (
    !isPlainObject(value) ||
    !hasOnlyKeys(value, new Set(["methodId"])) ||
    !validIdentifier(value.methodId, 160)
  ) {
    throw new AskError("ASK_INVALID_REQUEST");
  }
  return Object.freeze({ methodId: value.methodId });
}

export function parseAskSessionId(value) {
  if (!validIdentifier(value, ASK_LIMITS.maxSessionIdLength)) {
    throw new AskError("ASK_SESSION_NOT_FOUND");
  }
  return value;
}

export function publicAskError(error) {
  const typed = error instanceof AskError
    ? error
    : new AskError("ASK_AGENT_FAILED", { cause: error });
  return Object.freeze({
    statusCode: typed.statusCode,
    document: Object.freeze({
      ok: false,
      error: Object.freeze({
        code: typed.code,
        message: redactSensitiveText(typed.message),
        retryable: typed.retryable,
      }),
    }),
  });
}

export function truncateUtf8(value, maxBytes) {
  const text = String(value);
  if (utf8Length(text) <= maxBytes) return text;
  const suffix = "\n[truncated]";
  const suffixBytes = utf8Length(suffix);
  const buffer = Buffer.from(text, "utf8");
  let end = Math.max(0, maxBytes - suffixBytes);
  while (end > 0 && (buffer[end] & 0xc0) === 0x80) end -= 1;
  return `${buffer.subarray(0, end).toString("utf8")}${suffix}`;
}

export { ENTITY_KINDS, isPlainObject, utf8Length };
