export type Availability = "available" | "empty" | "unavailable";
export type TruthClass = "canonical" | "observed" | "derived" | "inferred";
export type EntityKind =
  | "project"
  | "pass"
  | "swimlane"
  | "leg"
  | "task"
  | "run"
  | "receipt"
  | "health"
  | "signal"
  | "issue"
  | "artifact";

export interface EntityRef {
  kind: EntityKind;
  id: string;
}

export type PassStatus =
  | "complete"
  | "active"
  | "blocked"
  | "waiting"
  | "optional"
  | "skipped";

export interface GateState {
  command: string | null;
  token: string | null;
  verdict: string | null;
  exitCode: number | null;
  ok: boolean | null;
}

export interface PassState {
  id: string;
  order: number;
  label: string;
  summary: string;
  optional: boolean;
  status: PassStatus;
  gate: GateState;
  artifactIds: string[];
}

export interface MethodEdge {
  id: string;
  source: string;
  target: string;
  kind: "required" | "optional" | "bypass";
}

export interface ReviewObjection {
  id: string;
  title: string;
  severity: string;
  resolved: boolean;
  artifactIds: string[];
}

export interface OpenQuestion {
  id: string;
  question: string;
  owner: string;
  blocksBuild: boolean;
}

export interface ReviewState {
  verdict: string;
  round: number;
  unresolvedCount: number;
  objections: ReviewObjection[];
  openQuestions: OpenQuestion[];
  artifactIds: string[];
}

export interface Swimlane {
  id: string;
  label: string;
  purpose: string | null;
  thread: boolean;
  risk: "low" | "med" | "high";
  owner: string;
  seam: {
    rationale: string | null;
    inputContract: string | null;
    outputContract: string | null;
    consumedInterface: string | null;
    evolution: string | null;
  };
  legIds: string[];
  blockingQuestionCount: number;
  artifactIds: string[];
}

export interface DecompositionLeg {
  id: string;
  swimlaneId: string;
  order: number;
  title: string;
  tech: string | null;
  status:
    | "proposed"
    | "accepted"
    | "in_progress"
    | "done"
    | "superseded";
  specRefs: string[];
  dependsOn: string[];
  responsibility: string | null;
  proves: string[];
  independence: string | null;
  consumes: string[];
  produces: string[];
  appetite: string | null;
  yields: string[];
  reverifyWhen: string | null;
  artifactIds: string[];
}

export interface DecompositionEdge {
  id: string;
  source: string;
  target: string;
  kind: "depends_on";
  artifactIds: string[];
}

export interface DecompositionState {
  availability: Availability;
  swimlanes: Swimlane[];
  legs: DecompositionLeg[];
  edges: DecompositionEdge[];
}

export type TaskStatus =
  | "ready"
  | "in_progress"
  | "blocked"
  | "done"
  | "parked"
  | string;

export interface WorkTask {
  id: string;
  title: string;
  status: TaskStatus;
  effort: string | null;
  priority: string | null;
  agent: string | null;
  budgetIterations: number | null;
  dependsOn: string[];
  signedOff: boolean;
  dispatchable: boolean;
  blockingReasons: string[];
  artifactIds: string[];
}

export interface WorkState {
  availability: Availability;
  tasks: WorkTask[];
  frontier: {
    taskIds: string[];
    blockedTaskIds: string[];
  };
  stats: {
    total: number;
    ready: number;
    inProgress: number;
    blocked: number;
    done: number;
    parked: number;
  };
}

export interface ExecutionRun {
  id: string;
  taskId: string;
  state: string;
  attempt: number | null;
  budgetIterations: number | null;
  runtime: {
    primaryRuntime: string | null;
    assurance: string | null;
  };
  checkpoint: {
    attempt: number | null;
    strikes: number | null;
    tokensUsed: number | null;
    startedAtEpoch: number | null;
    elapsedSeconds: number | null;
    artifactId: string | null;
  } | null;
  terminal: {
    result: string;
    recordedAt: string | null;
  } | null;
  handoffArtifactId: string | null;
  profileArtifactId: string;
  artifactIds: string[];
}

export interface ExecutionState {
  availability: Availability;
  runs: ExecutionRun[];
}

export interface Receipt {
  id: string;
  taskId: string;
  result: string;
  recordedAt: string | null;
  integrity: "verified" | "mismatch" | "unavailable";
  freshness: "current" | "stale" | "unavailable";
  bindings: {
    task: DigestBinding;
    executionProfile: DigestBinding;
    evaluationOutputSha256: string | null;
    pathPolicy: string | null;
  };
  provenance: {
    generatedBy: string | null;
    postHoc: boolean;
  };
  artifactIds: string[];
}

export interface DigestBinding {
  path: string | null;
  expectedSha256: string | null;
  currentSha256: string | null;
  matches: boolean | null;
}

export interface ReceiptState {
  availability: Availability;
  items: Receipt[];
}

export interface HealthCheck {
  id: string;
  component: string;
  status: "healthy" | "degraded" | "blocked" | "unavailable" | "empty";
  required: boolean;
  summary: string;
  artifactIds: string[];
}

export interface HealthState {
  overall: "healthy" | "degraded" | "blocked";
  checks: HealthCheck[];
}

export interface Signal {
  id: string;
  kind: "gate" | "task" | "run" | "receipt" | "git";
  severity: "info" | "success" | "warning" | "error";
  summary: string;
  occurredAt: string | null;
  entity?: EntityRef;
  artifactIds: string[];
}

export interface Issue {
  id: string;
  code: string;
  severity: "info" | "warning" | "error" | "blocking";
  domain:
    | "project"
    | "method"
    | "decomposition"
    | "review"
    | "work"
    | "execution"
    | "receipts"
    | "health"
    | "authorization";
  message: string;
  entity?: EntityRef;
  remediation?: string;
  artifactIds: string[];
}

export interface AuthorizationState {
  state: "allowed" | "blocked" | "complete" | "unknown";
  nextPassId: string | null;
  command: string | null;
  mutation: "mutating" | "non_mutating" | "none";
  dryRunSupported: boolean;
  enabled: boolean;
  rationale: string;
  blockingIssueIds: string[];
}

export interface ArtifactRef {
  id: string;
  label: string;
  path: string;
  kind: string;
  sha256: string;
  entity?: EntityRef;
  provenance: {
    sourceKind: "file" | "command";
    sourceRef: string;
    observedAt: string;
    truthClass: TruthClass;
  };
}

export interface WorkspaceSnapshot {
  schemaVersion: "3.0";
  snapshotId: string;
  observedAt: string;
  source: "workspace" | "fixture";
  project: {
    name: string;
    root: string;
    lane: "FULL" | "NORMAL" | "FAST";
    git: {
      available: boolean;
      root: string | null;
      branch: string | null;
      commit: string | null;
      dirty: boolean | null;
    };
    artifactIds: string[];
  };
  method: {
    name: "Converge";
    version: string;
    activePassId: string | null;
    passes: PassState[];
    edges: MethodEdge[];
  };
  review: ReviewState | null;
  decomposition: DecompositionState;
  work: WorkState;
  execution: ExecutionState;
  receipts: ReceiptState;
  health: HealthState;
  signals: Signal[];
  issues: Issue[];
  authorization: AuthorizationState;
  artifacts: ArtifactRef[];
}

export interface TransportState {
  stale: boolean;
  servedAt: string;
  error?: {
    code: string;
    message: string;
  };
}

export interface SnapshotEnvelope {
  snapshot: WorkspaceSnapshot;
  transport: TransportState;
}

interface ArtifactDocumentBase {
  path: string;
  label: string;
  kind: string;
  truncated: boolean;
  redacted: boolean;
  sourceBytes: number;
  sha256: string;
  snapshotId: string;
}

export interface TextArtifactDocument extends ArtifactDocumentBase {
  format: "markdown" | "text";
  content: string;
}

export interface PdfTextArtifactDocument extends ArtifactDocumentBase {
  format: "pdf-text";
  pages: Array<{
    number: number;
    text: string;
  }>;
  pageCount: number;
}

export type ArtifactDocument =
  | TextArtifactDocument
  | PdfTextArtifactDocument;

export type CockpitSurface =
  | "ask"
  | "overview"
  | "journey"
  | "decompose"
  | "artifacts"
  | "work"
  | "runs"
  | "proof"
  | "activity"
  | "health";
export type InspectorTab = "overview" | "evidence" | "activity";
