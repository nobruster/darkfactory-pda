import type { EntityRef } from "../types";

export type AskAgentAvailability =
  | "available"
  | "ready"
  | "not_configured"
  | "authentication_required"
  | "unavailable"
  | "blocked";

export interface AskAgent {
  id: "codex" | "claude";
  label: string;
  adapter: string;
  availability: AskAgentAvailability;
  reason: string | null;
  authenticationMethods?: Array<{ id: string; label: string }>;
}

export interface AskCapabilities {
  agents: AskAgent[];
  requestToken: string;
  policy: {
    transport: "ACP";
    workspaceAccess: "enforced-safe-mode";
    persistence: "cockpit-ephemeral";
    evidenceBoundary: string;
  };
}

/** ACP `SessionConfigOptionCategory`. `mode` is advertised but never settable. */
export type AskConfigCategory =
  | "model"
  | "model_config"
  | "thought_level"
  | "mode"
  | null;

export interface AskConfigValue {
  value: string;
  name: string;
  description: string | null;
  group: string | null;
}

/** One selector the agent advertises, as sanitized by the ACP client. */
export interface AskConfigOption {
  id: string;
  name: string;
  description: string | null;
  category: AskConfigCategory;
  type: "select" | "boolean";
  currentValue: string | boolean | null;
  values: AskConfigValue[];
  settable: boolean;
}

export interface AskConfigProbe {
  agentId: string;
  agentInfo: { name: string; title: string | null; version: string } | null;
  configOptions: AskConfigOption[];
}

/** A selection the composer sends with a turn. */
export interface AskConfigSelection {
  configId: string;
  type: "select" | "boolean";
  value: string | boolean;
}

/** What actually answered, read back from the session rather than the request. */
export interface AskEngineSelection {
  id: string;
  name: string;
  category: AskConfigCategory;
  value: string | null;
  label: string | null;
}

export interface AskFailure {
  code: string;
  message: string;
  retryable: boolean;
}

export interface AskConversationTurn {
  id: string;
  agentId: AskAgent["id"];
  question: string;
  scope: EntityRef | null;
  state: "pending" | "complete" | "error" | "cancelled";
  response: AskTurnResponse | null;
  error: AskFailure | null;
}

/**
 * Conversations are owned by App so that navigating to another surface does not
 * unmount the transcript. They are held in memory only: nothing is written to
 * disk, which keeps the documented `cockpit-ephemeral` persistence boundary.
 */
export interface AskConversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  turns: AskConversationTurn[];
}

export interface AskActivity {
  id: string;
  kind: "plan" | "read" | "search" | "think" | "permission" | "status";
  label: string;
  status: "pending" | "active" | "complete" | "denied";
  detail?: string;
}

export interface AskTurnResponse {
  turnId: string;
  agentId: AskAgent["id"];
  snapshotId: string;
  grounding: {
    snapshotId: string;
    observedAt: string;
    methodology: {
      tool: "cvg";
      version: string;
      digest: string;
    };
    entity: EntityRef | null;
    artifacts: Array<{
      id: string;
      label: string;
      path: string;
      sha256: string;
      truncated: boolean;
    }>;
  };
  answer: string;
  steps: string[];
  activity: AskActivity[];
  stopReason: string;
  elapsedMs: number;
  engine?: AskEngineSelection[];
  timings?: AskTurnTimings;
  context?: AskContextStats;
}

/** Where a turn's wall-clock went. */
export interface AskTurnTimings {
  /** cvg snapshot, methodology, artifact reads, adapter spawn, session setup. */
  prepareMs: number | null;
  /** Provider thinking and writing. */
  answerMs: number | null;
  totalMs: number;
}

/** What was packed into the prompt for this turn. */
export interface AskContextStats {
  contextBytes: number;
  maxContextBytes: number;
  methodCommands: number;
  passes: number;
  swimlanes: number;
  legs: number;
  tasks: number;
  runs: number;
  receipts: number;
  artifactsCatalogued: number;
  artifactsIncluded: number;
  issues: number;
  signals: number;
  healthChecks: number;
}
