import type {
  ArtifactRef,
  DecompositionEdge,
  DecompositionLeg,
  DigestBinding,
  EntityRef,
  ExecutionRun,
  HealthCheck,
  Issue,
  MethodEdge,
  OpenQuestion,
  PassState,
  Receipt,
  ReviewObjection,
  Signal,
  SnapshotEnvelope,
  Swimlane,
  TransportState,
  WorkTask,
  WorkspaceSnapshot,
} from "../types";

const ARTIFACT_ID = /^artifact_[0-9a-f]{20}$/;
const DECOMPOSITION_EDGE_ID = /^decompedge_[0-9a-f]{20}$/;
const ISSUE_ID = /^issue_[0-9a-f]{20}$/;
const LEG_ID = /^swimlane-[a-z0-9]+(?:-[a-z0-9]+)*-leg-[0-9]{2}$/;
const PASS_ID = /^pass-[0-8]$/;
const SNAPSHOT_ID = /^ws3_[0-9a-f]{32}$/;
const SHA256 = /^[0-9a-f]{64}$/;
const SWIMLANE_ID = /^swimlane-[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ENTITY_KINDS = new Set<EntityRef["kind"]>([
  "project",
  "pass",
  "swimlane",
  "leg",
  "task",
  "run",
  "receipt",
  "health",
  "signal",
  "issue",
  "artifact",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(
  value: Record<string, unknown>,
  required: readonly string[],
  optional: readonly string[] = [],
) {
  const allowed = new Set([...required, ...optional]);
  return (
    required.every((key) => Object.hasOwn(value, key)) &&
    Object.keys(value).every((key) => allowed.has(key))
  );
}

function hasString(value: Record<string, unknown>, key: string) {
  return typeof value[key] === "string";
}

function hasNonEmptyString(value: Record<string, unknown>, key: string) {
  return hasString(value, key) && (value[key] as string).length > 0;
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNullableBoolean(value: unknown): value is boolean | null {
  return value === null || typeof value === "boolean";
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function isNonNegativeInteger(value: unknown): value is number {
  return isInteger(value) && value >= 0;
}

function isNullableInteger(value: unknown): value is number | null {
  return value === null || isInteger(value);
}

function isNullableNonNegativeInteger(value: unknown): value is number | null {
  return value === null || isNonNegativeInteger(value);
}

function isDate(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function isStringArray(value: unknown, nonEmpty = false): value is string[] {
  return (
    Array.isArray(value) &&
    value.every(
      (item) =>
        typeof item === "string" && (!nonEmpty || item.length > 0),
    ) &&
    new Set(value).size === value.length
  );
}

function isArtifactIds(value: unknown): value is string[] {
  return isStringArray(value) && value.every((id) => ARTIFACT_ID.test(id));
}

function isEntity(value: unknown): value is EntityRef {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["kind", "id"]) &&
    hasString(value, "kind") &&
    ENTITY_KINDS.has(value.kind as EntityRef["kind"]) &&
    hasNonEmptyString(value, "id")
  );
}

function hasOptionalEntity(value: Record<string, unknown>) {
  return value.entity === undefined || isEntity(value.entity);
}

function hasUniqueIds(records: Array<{ id: string }>) {
  return new Set(records.map(({ id }) => id)).size === records.length;
}

function hasKnownArtifactReferences(
  value: unknown,
  knownArtifactIds: Set<string>,
): boolean {
  if (Array.isArray(value)) {
    return value.every((item) =>
      hasKnownArtifactReferences(item, knownArtifactIds),
    );
  }
  if (!isRecord(value)) return true;
  return Object.entries(value).every(([name, child]) => {
    if (name === "artifactIds") {
      return (
        Array.isArray(child) &&
        child.every(
          (artifactId) =>
            typeof artifactId === "string" &&
            knownArtifactIds.has(artifactId),
        )
      );
    }
    return hasKnownArtifactReferences(child, knownArtifactIds);
  });
}

function hasAcyclicLegDependencies(legs: DecompositionLeg[]): boolean {
  const ids = new Set(legs.map(({ id }) => id));
  const indegree = new Map(legs.map(({ id }) => [id, 0]));
  const dependents = new Map(legs.map(({ id }) => [id, [] as string[]]));
  for (const leg of legs) {
    for (const dependency of leg.dependsOn) {
      if (!ids.has(dependency)) continue;
      if (dependency === leg.id) return false;
      indegree.set(leg.id, (indegree.get(leg.id) ?? 0) + 1);
      dependents.get(dependency)?.push(leg.id);
    }
  }
  const frontier = [...ids].filter((id) => indegree.get(id) === 0);
  let visited = 0;
  while (frontier.length > 0) {
    const current = frontier.shift();
    if (!current) continue;
    visited += 1;
    for (const dependent of dependents.get(current) ?? []) {
      const next = (indegree.get(dependent) ?? 0) - 1;
      indegree.set(dependent, next);
      if (next === 0) frontier.push(dependent);
    }
  }
  return visited === ids.size;
}

function hasReferentialIntegrity(snapshot: WorkspaceSnapshot) {
  const collections = {
    pass: snapshot.method.passes,
    swimlane: snapshot.decomposition.swimlanes,
    leg: snapshot.decomposition.legs,
    task: snapshot.work.tasks,
    run: snapshot.execution.runs,
    receipt: snapshot.receipts.items,
    health: snapshot.health.checks,
    signal: snapshot.signals,
    issue: snapshot.issues,
    artifact: snapshot.artifacts,
  } as const;

  if (
    !Object.values(collections).every((records) =>
      hasUniqueIds(records as Array<{ id: string }>),
    )
  ) {
    return false;
  }

  const knownEntities: Record<EntityRef["kind"], Set<string>> = {
    project: new Set([snapshot.project.name]),
    pass: new Set(snapshot.method.passes.map(({ id }) => id)),
    swimlane: new Set(snapshot.decomposition.swimlanes.map(({ id }) => id)),
    leg: new Set(snapshot.decomposition.legs.map(({ id }) => id)),
    task: new Set(snapshot.work.tasks.map(({ id }) => id)),
    run: new Set(snapshot.execution.runs.map(({ id }) => id)),
    receipt: new Set(snapshot.receipts.items.map(({ id }) => id)),
    health: new Set(snapshot.health.checks.map(({ id }) => id)),
    signal: new Set(snapshot.signals.map(({ id }) => id)),
    issue: new Set(snapshot.issues.map(({ id }) => id)),
    artifact: new Set(snapshot.artifacts.map(({ id }) => id)),
  };
  const references = [
    ...snapshot.signals.map(({ entity }) => entity),
    ...snapshot.issues.map(({ entity }) => entity),
    ...snapshot.artifacts.map(({ entity }) => entity),
  ].filter((entity): entity is EntityRef => entity !== undefined);

  const lanesById = new Map(
    snapshot.decomposition.swimlanes.map((lane) => [lane.id, lane] as const),
  );
  const legsById = new Map(
    snapshot.decomposition.legs.map((leg) => [leg.id, leg] as const),
  );
  const laneLegReferences = snapshot.decomposition.swimlanes.every((lane) =>
    lane.legIds.every(
      (id) => legsById.get(id)?.swimlaneId === lane.id,
    ),
  );
  const legReferences = snapshot.decomposition.legs.every(
    (leg) =>
      lanesById.get(leg.swimlaneId)?.legIds.includes(leg.id) === true &&
      leg.dependsOn.every((id) => knownEntities.leg.has(id)),
  );
  const edgeIds = snapshot.decomposition.edges.map(({ id }) => id);
  const expectedDependencyPairs = new Set(
    snapshot.decomposition.legs.flatMap((leg) =>
      leg.dependsOn.map((dependency) => `${dependency}\u0000${leg.id}`),
    ),
  );
  const observedDependencyPairs = snapshot.decomposition.edges.map(
    (edge) => `${edge.source}\u0000${edge.target}`,
  );
  const edgeReferences =
    new Set(edgeIds).size === edgeIds.length &&
    new Set(observedDependencyPairs).size === observedDependencyPairs.length &&
    expectedDependencyPairs.size === observedDependencyPairs.length &&
    observedDependencyPairs.every((pair) => expectedDependencyPairs.has(pair)) &&
    snapshot.decomposition.edges.every(
    (edge) =>
      knownEntities.leg.has(edge.source) &&
      knownEntities.leg.has(edge.target) &&
      legsById.get(edge.target)?.dependsOn.includes(edge.source) === true,
    );
  const emptyWhenUnavailable =
    snapshot.decomposition.availability === "available" ||
    (snapshot.decomposition.swimlanes.length === 0 &&
      snapshot.decomposition.legs.length === 0 &&
      snapshot.decomposition.edges.length === 0);
  return (
    laneLegReferences &&
    legReferences &&
    hasAcyclicLegDependencies(snapshot.decomposition.legs) &&
    edgeReferences &&
    emptyWhenUnavailable &&
    references.every(({ kind, id }) => knownEntities[kind].has(id)) &&
    hasKnownArtifactReferences(snapshot, knownEntities.artifact)
  );
}

function isGate(value: unknown) {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["command", "token", "verdict", "exitCode", "ok"]) &&
    isNullableString(value.command) &&
    isNullableString(value.token) &&
    isNullableString(value.verdict) &&
    isNullableInteger(value.exitCode) &&
    isNullableBoolean(value.ok)
  );
}

function isPass(value: unknown): value is PassState {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "id",
      "order",
      "label",
      "summary",
      "optional",
      "status",
      "gate",
      "artifactIds",
    ]) &&
    hasString(value, "id") &&
    PASS_ID.test(value.id as string) &&
    isNonNegativeInteger(value.order) &&
    value.order <= 8 &&
    hasNonEmptyString(value, "label") &&
    hasNonEmptyString(value, "summary") &&
    typeof value.optional === "boolean" &&
    ["complete", "active", "blocked", "waiting", "optional", "skipped"].includes(
      String(value.status),
    ) &&
    isGate(value.gate) &&
    isArtifactIds(value.artifactIds)
  );
}

function isEdge(value: unknown): value is MethodEdge {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["id", "source", "target", "kind"]) &&
    hasNonEmptyString(value, "id") &&
    hasString(value, "source") &&
    PASS_ID.test(value.source as string) &&
    hasString(value, "target") &&
    PASS_ID.test(value.target as string) &&
    ["required", "optional", "bypass"].includes(String(value.kind))
  );
}

function isObjection(value: unknown): value is ReviewObjection {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "id",
      "title",
      "severity",
      "resolved",
      "artifactIds",
    ]) &&
    hasNonEmptyString(value, "id") &&
    hasNonEmptyString(value, "title") &&
    (value.title as string).length <= 320 &&
    hasNonEmptyString(value, "severity") &&
    typeof value.resolved === "boolean" &&
    isArtifactIds(value.artifactIds)
  );
}

function isQuestion(value: unknown): value is OpenQuestion {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["id", "question", "owner", "blocksBuild"]) &&
    hasNonEmptyString(value, "id") &&
    hasNonEmptyString(value, "question") &&
    (value.question as string).length <= 500 &&
    hasNonEmptyString(value, "owner") &&
    (value.owner as string).length <= 120 &&
    typeof value.blocksBuild === "boolean"
  );
}

function isSwimlane(value: unknown): value is Swimlane {
  if (!isRecord(value) || !isRecord(value.seam)) return false;
  return (
    hasExactKeys(value, [
      "id",
      "label",
      "purpose",
      "thread",
      "risk",
      "owner",
      "seam",
      "legIds",
      "blockingQuestionCount",
      "artifactIds",
    ]) &&
    hasString(value, "id") &&
    SWIMLANE_ID.test(value.id as string) &&
    hasNonEmptyString(value, "label") &&
    isNullableString(value.purpose) &&
    typeof value.thread === "boolean" &&
    ["low", "med", "high"].includes(String(value.risk)) &&
    hasNonEmptyString(value, "owner") &&
    hasExactKeys(value.seam, [
      "rationale",
      "inputContract",
      "outputContract",
      "consumedInterface",
      "evolution",
    ]) &&
    isNullableString(value.seam.rationale) &&
    isNullableString(value.seam.inputContract) &&
    isNullableString(value.seam.outputContract) &&
    isNullableString(value.seam.consumedInterface) &&
    isNullableString(value.seam.evolution) &&
    isStringArray(value.legIds) &&
    value.legIds.every((id) => LEG_ID.test(id)) &&
    isNonNegativeInteger(value.blockingQuestionCount) &&
    isArtifactIds(value.artifactIds)
  );
}

function isDecompositionLeg(value: unknown): value is DecompositionLeg {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "id",
      "swimlaneId",
      "order",
      "title",
      "tech",
      "status",
      "specRefs",
      "dependsOn",
      "responsibility",
      "proves",
      "independence",
      "consumes",
      "produces",
      "appetite",
      "yields",
      "reverifyWhen",
      "artifactIds",
    ]) &&
    hasString(value, "id") &&
    LEG_ID.test(value.id as string) &&
    hasString(value, "swimlaneId") &&
    SWIMLANE_ID.test(value.swimlaneId as string) &&
    isNonNegativeInteger(value.order) &&
    value.order <= 99 &&
    hasNonEmptyString(value, "title") &&
    isNullableString(value.tech) &&
    ["proposed", "accepted", "in_progress", "done", "superseded"].includes(
      String(value.status),
    ) &&
    isStringArray(value.specRefs) &&
    isStringArray(value.dependsOn) &&
    value.dependsOn.every((id) => LEG_ID.test(id)) &&
    isNullableString(value.responsibility) &&
    isStringArray(value.proves) &&
    isNullableString(value.independence) &&
    isStringArray(value.consumes) &&
    isStringArray(value.produces) &&
    isNullableString(value.appetite) &&
    isStringArray(value.yields) &&
    isNullableString(value.reverifyWhen) &&
    isArtifactIds(value.artifactIds)
  );
}

function isDecompositionEdge(
  value: unknown,
): value is DecompositionEdge {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "id",
      "source",
      "target",
      "kind",
      "artifactIds",
    ]) &&
    hasString(value, "id") &&
    DECOMPOSITION_EDGE_ID.test(value.id as string) &&
    hasString(value, "source") &&
    LEG_ID.test(value.source as string) &&
    hasString(value, "target") &&
    LEG_ID.test(value.target as string) &&
    value.kind === "depends_on" &&
    isArtifactIds(value.artifactIds)
  );
}

function isTask(value: unknown): value is WorkTask {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "id",
      "title",
      "status",
      "effort",
      "priority",
      "agent",
      "budgetIterations",
      "dependsOn",
      "signedOff",
      "dispatchable",
      "blockingReasons",
      "artifactIds",
    ]) &&
    hasNonEmptyString(value, "id") &&
    hasNonEmptyString(value, "title") &&
    (value.title as string).length <= 240 &&
    hasNonEmptyString(value, "status") &&
    isNullableString(value.effort) &&
    isNullableString(value.priority) &&
    isNullableString(value.agent) &&
    isNullableNonNegativeInteger(value.budgetIterations) &&
    isStringArray(value.dependsOn, true) &&
    typeof value.signedOff === "boolean" &&
    typeof value.dispatchable === "boolean" &&
    isStringArray(value.blockingReasons, true) &&
    isArtifactIds(value.artifactIds)
  );
}

function isCheckpoint(value: unknown) {
  return (
    value === null ||
    (isRecord(value) &&
      hasExactKeys(value, [
        "attempt",
        "strikes",
        "tokensUsed",
        "startedAtEpoch",
        "elapsedSeconds",
        "artifactId",
      ]) &&
      isNullableNonNegativeInteger(value.attempt) &&
      isNullableNonNegativeInteger(value.strikes) &&
      isNullableNonNegativeInteger(value.tokensUsed) &&
      isNullableNonNegativeInteger(value.startedAtEpoch) &&
      isNullableNonNegativeInteger(value.elapsedSeconds) &&
      isNullableString(value.artifactId))
  );
}

function isTerminal(value: unknown) {
  return (
    value === null ||
    (isRecord(value) &&
      hasExactKeys(value, ["result", "recordedAt"]) &&
      hasNonEmptyString(value, "result") &&
      isNullableString(value.recordedAt))
  );
}

function isRun(value: unknown): value is ExecutionRun {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "id",
      "taskId",
      "state",
      "attempt",
      "budgetIterations",
      "runtime",
      "checkpoint",
      "terminal",
      "handoffArtifactId",
      "profileArtifactId",
      "artifactIds",
    ]) &&
    hasNonEmptyString(value, "id") &&
    hasNonEmptyString(value, "taskId") &&
    hasNonEmptyString(value, "state") &&
    isNullableNonNegativeInteger(value.attempt) &&
    isNullableNonNegativeInteger(value.budgetIterations) &&
    isRecord(value.runtime) &&
    hasExactKeys(value.runtime, ["primaryRuntime", "assurance"]) &&
    isNullableString(value.runtime.primaryRuntime) &&
    isNullableString(value.runtime.assurance) &&
    isCheckpoint(value.checkpoint) &&
    isTerminal(value.terminal) &&
    isNullableString(value.handoffArtifactId) &&
    hasString(value, "profileArtifactId") &&
    isArtifactIds(value.artifactIds)
  );
}

function isDigestBinding(value: unknown): value is DigestBinding {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "path",
      "expectedSha256",
      "currentSha256",
      "matches",
    ]) &&
    isNullableString(value.path) &&
    isNullableString(value.expectedSha256) &&
    isNullableString(value.currentSha256) &&
    isNullableBoolean(value.matches)
  );
}

function isReceipt(value: unknown): value is Receipt {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "id",
      "taskId",
      "result",
      "recordedAt",
      "integrity",
      "freshness",
      "bindings",
      "provenance",
      "artifactIds",
    ]) &&
    hasNonEmptyString(value, "id") &&
    hasNonEmptyString(value, "taskId") &&
    hasNonEmptyString(value, "result") &&
    (value.recordedAt === null || isDate(value.recordedAt)) &&
    ["verified", "mismatch", "unavailable"].includes(String(value.integrity)) &&
    ["current", "stale", "unavailable"].includes(String(value.freshness)) &&
    isRecord(value.bindings) &&
    hasExactKeys(value.bindings, [
      "task",
      "executionProfile",
      "evaluationOutputSha256",
      "pathPolicy",
    ]) &&
    isDigestBinding(value.bindings.task) &&
    isDigestBinding(value.bindings.executionProfile) &&
    isNullableString(value.bindings.evaluationOutputSha256) &&
    isNullableString(value.bindings.pathPolicy) &&
    isRecord(value.provenance) &&
    hasExactKeys(value.provenance, ["generatedBy", "postHoc"]) &&
    isNullableString(value.provenance.generatedBy) &&
    typeof value.provenance.postHoc === "boolean" &&
    isArtifactIds(value.artifactIds)
  );
}

function isHealthCheck(value: unknown): value is HealthCheck {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "id",
      "component",
      "status",
      "required",
      "summary",
      "artifactIds",
    ]) &&
    hasNonEmptyString(value, "id") &&
    hasNonEmptyString(value, "component") &&
    ["healthy", "degraded", "blocked", "unavailable", "empty"].includes(
      String(value.status),
    ) &&
    typeof value.required === "boolean" &&
    hasNonEmptyString(value, "summary") &&
    isArtifactIds(value.artifactIds)
  );
}

function isSignal(value: unknown): value is Signal {
  return (
    isRecord(value) &&
    hasExactKeys(
      value,
      ["id", "kind", "severity", "summary", "occurredAt", "artifactIds"],
      ["entity"],
    ) &&
    hasNonEmptyString(value, "id") &&
    ["gate", "task", "run", "receipt", "git"].includes(String(value.kind)) &&
    ["info", "success", "warning", "error"].includes(String(value.severity)) &&
    hasNonEmptyString(value, "summary") &&
    (value.occurredAt === null || isDate(value.occurredAt)) &&
    hasOptionalEntity(value) &&
    isArtifactIds(value.artifactIds)
  );
}

function isIssue(value: unknown): value is Issue {
  return (
    isRecord(value) &&
    hasExactKeys(
      value,
      ["id", "code", "severity", "domain", "message", "artifactIds"],
      ["entity", "remediation"],
    ) &&
    hasString(value, "id") &&
    ISSUE_ID.test(value.id as string) &&
    hasString(value, "code") &&
    /^[A-Z][A-Z0-9_]*$/.test(value.code as string) &&
    ["info", "warning", "error", "blocking"].includes(String(value.severity)) &&
    [
      "project",
      "method",
      "decomposition",
      "review",
      "work",
      "execution",
      "receipts",
      "health",
      "authorization",
    ].includes(String(value.domain)) &&
    hasNonEmptyString(value, "message") &&
    hasOptionalEntity(value) &&
    (value.remediation === undefined ||
      (typeof value.remediation === "string" && value.remediation.length > 0)) &&
    isArtifactIds(value.artifactIds)
  );
}

function isArtifact(value: unknown): value is ArtifactRef {
  if (!isRecord(value) || !isRecord(value.provenance)) return false;
  const path = value.path;
  return (
    hasExactKeys(
      value,
      ["id", "label", "path", "kind", "sha256", "provenance"],
      ["entity"],
    ) &&
    hasString(value, "id") &&
    ARTIFACT_ID.test(value.id as string) &&
    hasNonEmptyString(value, "label") &&
    typeof path === "string" &&
    path.length > 0 &&
    !path.startsWith("/") &&
    !path.split("/").includes("..") &&
    hasNonEmptyString(value, "kind") &&
    hasString(value, "sha256") &&
    SHA256.test(value.sha256 as string) &&
    hasOptionalEntity(value) &&
    hasExactKeys(value.provenance, [
      "sourceKind",
      "sourceRef",
      "observedAt",
      "truthClass",
    ]) &&
    ["file", "command"].includes(String(value.provenance.sourceKind)) &&
    hasNonEmptyString(value.provenance, "sourceRef") &&
    isDate(value.provenance.observedAt) &&
    ["canonical", "observed", "derived", "inferred"].includes(
      String(value.provenance.truthClass),
    )
  );
}

export function isWorkspaceSnapshot(
  value: unknown,
): value is WorkspaceSnapshot {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
      "schemaVersion",
      "snapshotId",
      "observedAt",
      "source",
      "project",
      "method",
      "review",
      "decomposition",
      "work",
      "execution",
      "receipts",
      "health",
      "signals",
      "issues",
      "authorization",
      "artifacts",
    ]) ||
    !isRecord(value.project) ||
    !isRecord(value.project.git) ||
    !isRecord(value.method) ||
    !isRecord(value.decomposition) ||
    !isRecord(value.work) ||
    !isRecord(value.work.frontier) ||
    !isRecord(value.work.stats) ||
    !isRecord(value.execution) ||
    !isRecord(value.receipts) ||
    !isRecord(value.health) ||
    !isRecord(value.authorization)
  ) {
    return false;
  }

  if (
    value.schemaVersion !== "3.0" ||
    !hasString(value, "snapshotId") ||
    !SNAPSHOT_ID.test(value.snapshotId as string) ||
    !isDate(value.observedAt) ||
    !["workspace", "fixture"].includes(String(value.source)) ||
    !hasExactKeys(value.project, [
      "name",
      "root",
      "lane",
      "git",
      "artifactIds",
    ]) ||
    !hasNonEmptyString(value.project, "name") ||
    !hasNonEmptyString(value.project, "root") ||
    !["FULL", "NORMAL", "FAST"].includes(String(value.project.lane)) ||
    !hasExactKeys(value.project.git, [
      "available",
      "root",
      "branch",
      "commit",
      "dirty",
    ]) ||
    typeof value.project.git.available !== "boolean" ||
    !isNullableString(value.project.git.root) ||
    !isNullableString(value.project.git.branch) ||
    !isNullableString(value.project.git.commit) ||
    !isNullableBoolean(value.project.git.dirty) ||
    !isArtifactIds(value.project.artifactIds) ||
    !hasExactKeys(value.method, [
      "name",
      "version",
      "activePassId",
      "passes",
      "edges",
    ]) ||
    value.method.name !== "Converge" ||
    !hasNonEmptyString(value.method, "version") ||
    !(
      value.method.activePassId === null ||
      (typeof value.method.activePassId === "string" &&
        PASS_ID.test(value.method.activePassId))
    ) ||
    !Array.isArray(value.method.passes) ||
    value.method.passes.length !== 9 ||
    !value.method.passes.every(isPass) ||
    !Array.isArray(value.method.edges) ||
    !value.method.edges.every(isEdge)
  ) {
    return false;
  }

  if (
    value.review !== null &&
    (!isRecord(value.review) ||
      !hasExactKeys(value.review, [
        "verdict",
        "round",
        "unresolvedCount",
        "objections",
        "openQuestions",
        "artifactIds",
      ]) ||
      !hasNonEmptyString(value.review, "verdict") ||
      !isNonNegativeInteger(value.review.round) ||
      !isNonNegativeInteger(value.review.unresolvedCount) ||
      !Array.isArray(value.review.objections) ||
      !value.review.objections.every(isObjection) ||
      !Array.isArray(value.review.openQuestions) ||
      !value.review.openQuestions.every(isQuestion) ||
      !isArtifactIds(value.review.artifactIds))
  ) {
    return false;
  }

  if (
    !hasExactKeys(value.decomposition, [
      "availability",
      "swimlanes",
      "legs",
      "edges",
    ]) ||
    !["available", "empty", "unavailable"].includes(
      String(value.decomposition.availability),
    ) ||
    !Array.isArray(value.decomposition.swimlanes) ||
    !value.decomposition.swimlanes.every(isSwimlane) ||
    !Array.isArray(value.decomposition.legs) ||
    !value.decomposition.legs.every(isDecompositionLeg) ||
    !Array.isArray(value.decomposition.edges) ||
    !value.decomposition.edges.every(isDecompositionEdge)
  ) {
    return false;
  }

  const availability = ["available", "empty", "unavailable"];
  const stats = value.work.stats;
  const structurallyValid =
    hasExactKeys(value.work, ["availability", "tasks", "frontier", "stats"]) &&
    availability.includes(String(value.work.availability)) &&
    Array.isArray(value.work.tasks) &&
    value.work.tasks.every(isTask) &&
    hasExactKeys(value.work.frontier, ["taskIds", "blockedTaskIds"]) &&
    isStringArray(value.work.frontier.taskIds, true) &&
    isStringArray(value.work.frontier.blockedTaskIds, true) &&
    hasExactKeys(stats, [
      "total",
      "ready",
      "inProgress",
      "blocked",
      "done",
      "parked",
    ]) &&
    ["total", "ready", "inProgress", "blocked", "done", "parked"].every(
      (key) => isNonNegativeInteger(stats[key]),
    ) &&
    hasExactKeys(value.execution, ["availability", "runs"]) &&
    availability.includes(String(value.execution.availability)) &&
    Array.isArray(value.execution.runs) &&
    value.execution.runs.every(isRun) &&
    hasExactKeys(value.receipts, ["availability", "items"]) &&
    availability.includes(String(value.receipts.availability)) &&
    Array.isArray(value.receipts.items) &&
    value.receipts.items.every(isReceipt) &&
    hasExactKeys(value.health, ["overall", "checks"]) &&
    ["healthy", "degraded", "blocked"].includes(String(value.health.overall)) &&
    Array.isArray(value.health.checks) &&
    value.health.checks.every(isHealthCheck) &&
    Array.isArray(value.signals) &&
    value.signals.every(isSignal) &&
    Array.isArray(value.issues) &&
    value.issues.every(isIssue) &&
    hasExactKeys(value.authorization, [
      "state",
      "nextPassId",
      "command",
      "mutation",
      "dryRunSupported",
      "enabled",
      "rationale",
      "blockingIssueIds",
    ]) &&
    ["allowed", "blocked", "complete", "unknown"].includes(
      String(value.authorization.state),
    ) &&
    (value.authorization.nextPassId === null ||
      (typeof value.authorization.nextPassId === "string" &&
        PASS_ID.test(value.authorization.nextPassId))) &&
    isNullableString(value.authorization.command) &&
    ["mutating", "non_mutating", "none"].includes(
      String(value.authorization.mutation),
    ) &&
    typeof value.authorization.dryRunSupported === "boolean" &&
    typeof value.authorization.enabled === "boolean" &&
    hasNonEmptyString(value.authorization, "rationale") &&
    isStringArray(value.authorization.blockingIssueIds) &&
    value.authorization.blockingIssueIds.every((id) => ISSUE_ID.test(id)) &&
    Array.isArray(value.artifacts) &&
    value.artifacts.every(isArtifact);

  return (
    structurallyValid &&
    hasReferentialIntegrity(value as unknown as WorkspaceSnapshot)
  );
}

function isTransport(value: unknown): value is TransportState {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["stale", "servedAt"], ["error"]) &&
    typeof value.stale === "boolean" &&
    isDate(value.servedAt) &&
    (value.error === undefined ||
      (isRecord(value.error) &&
        hasExactKeys(value.error, ["code", "message"]) &&
        hasNonEmptyString(value.error, "code") &&
        hasNonEmptyString(value.error, "message")))
  );
}

export function isSnapshotEnvelope(value: unknown): value is SnapshotEnvelope {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["snapshot", "transport"]) &&
    isWorkspaceSnapshot(value.snapshot) &&
    isTransport(value.transport)
  );
}

export function decodeSnapshotPayload(value: unknown): SnapshotEnvelope | null {
  return isSnapshotEnvelope(value) ? value : null;
}
