import type {
  SnapshotEnvelope,
  WorkspaceSnapshot,
} from "../types";

const observedAt = "2026-08-03T20:00:00.000Z";
const sha256 = "a".repeat(64);
const artifactIds = {
  review: "artifact_11111111111111111111",
  task: "artifact_22222222222222222222",
  profile: "artifact_33333333333333333333",
  receipt: "artifact_44444444444444444444",
  lane: "artifact_55555555555555555555",
  legApi: "artifact_66666666666666666666",
  legUi: "artifact_77777777777777777777",
} as const;
const issueIds = {
  review: "issue_11111111111111111111",
  unlinked: "issue_22222222222222222222",
} as const;

function pass(
  order: number,
  label: string,
  status: WorkspaceSnapshot["method"]["passes"][number]["status"],
  ok: boolean | null,
) {
  return {
    id: `pass-${order}`,
    order,
    label,
    summary: `${label} is represented by canonical Converge evidence.`,
    optional: order === 6,
    status,
    gate: {
      command:
        order === 4
          ? "cvg review --check"
          : order === 5
            ? "cvg tasks plan"
            : `cvg pass-${order}`,
      token:
        ok === null
          ? null
          : order === 4
            ? "CHECK_CONSENSUS=FAIL"
            : `CHECK_PASS_${order}=${ok ? "PASS" : "FAIL"}`,
      verdict: ok === null ? null : ok ? "PASS" : "FAIL",
      exitCode: ok === null ? null : ok ? 0 : 1,
      ok,
    },
    artifactIds:
      order === 4
        ? [artifactIds.review]
        : order === 3
          ? [artifactIds.lane]
          : [],
  };
}

/**
 * A deterministic, schema-valid WorkspaceSnapshot 3.0 scenario.
 *
 * The scenario intentionally combines every lifecycle state Cockpit must keep
 * visually distinct. Tests may mutate their own fresh copy without changing
 * product replay data or claiming that this is a live workspace.
 */
export function makeScenarioSnapshot(
  mutate?: (snapshot: WorkspaceSnapshot) => void,
): WorkspaceSnapshot {
  const snapshot: WorkspaceSnapshot = {
    schemaVersion: "3.0",
    snapshotId: "ws3_00000000000000000000000000000001",
    observedAt,
    source: "fixture",
    project: {
      name: "Cockpit verification replay",
      root: "/fixtures/cockpit-verification",
      lane: "FULL",
      git: {
        available: true,
        root: "/fixtures/cockpit-verification",
        branch: "feat/front-end-cockpit-v1",
        commit: "0123456789abcdef0123456789abcdef01234567",
        dirty: false,
      },
      artifactIds: [],
    },
    method: {
      name: "Converge",
      version: "0.1.0",
      activePassId: "pass-4",
      passes: [
        pass(0, "Capture", "complete", true),
        pass(1, "Intent", "complete", true),
        pass(2, "Structure", "complete", true),
        pass(3, "Decompose", "complete", true),
        pass(4, "Consensus", "blocked", false),
        pass(5, "Tasking", "waiting", null),
        pass(6, "Register", "optional", null),
        pass(7, "Bind", "waiting", null),
        pass(8, "Loop", "waiting", null),
      ],
      edges: [
        {
          id: "pass-3-pass-4",
          source: "pass-3",
          target: "pass-4",
          kind: "required",
        },
        {
          id: "pass-4-pass-5",
          source: "pass-4",
          target: "pass-5",
          kind: "required",
        },
      ],
    },
    review: {
      verdict: "FAIL",
      round: 2,
      unresolvedCount: 1,
      objections: [
        {
          id: "OBJ-001",
          title: "Owner decision is still required",
          severity: "critical",
          resolved: false,
          artifactIds: [artifactIds.review],
        },
      ],
      openQuestions: [
        {
          id: "Q-001",
          question: "Who accepts the residual risk?",
          owner: "Product owner",
          blocksBuild: true,
        },
      ],
      artifactIds: [artifactIds.review],
    },
    decomposition: {
      availability: "available",
      swimlanes: [
        {
          id: "swimlane-checkout",
          label: "Swimlane · checkout",
          purpose: "Prove a bounded checkout steel thread across explicit seams.",
          thread: true,
          risk: "high",
          owner: "Payments platform",
          seam: {
            rationale:
              "The HTTP boundary isolates shopper intent from payment-provider settlement.",
            inputContract: "checkout command v1",
            outputContract: "payment outcome v1",
            consumedInterface: "cart and identity context",
            evolution: "Additive fields remain backwards compatible.",
          },
          legIds: [
            "swimlane-checkout-leg-01",
            "swimlane-checkout-leg-02",
          ],
          blockingQuestionCount: 1,
          artifactIds: [artifactIds.lane],
        },
      ],
      legs: [
        {
          id: "swimlane-checkout-leg-01",
          swimlaneId: "swimlane-checkout",
          order: 1,
          title: "Accept checkout intent",
          tech: "fastapi",
          status: "accepted",
          specRefs: ["REQ-001", "ADR-002"],
          dependsOn: [],
          responsibility:
            "Validate a checkout command and publish a stable payment request.",
          proves: ["Invalid checkout commands fail closed"],
          independence: "Uses a provider port and deterministic request fixtures.",
          consumes: ["checkout command v1"],
          produces: ["payment request v1"],
          appetite: "1 day",
          yields: ["HTTP adapter", "contract tests"],
          reverifyWhen: "The checkout command schema changes.",
          artifactIds: [artifactIds.legApi],
        },
        {
          id: "swimlane-checkout-leg-02",
          swimlaneId: "swimlane-checkout",
          order: 2,
          title: "Settle payment outcome",
          tech: "stripe",
          status: "in_progress",
          specRefs: ["REQ-004"],
          dependsOn: ["swimlane-checkout-leg-01"],
          responsibility:
            "Translate the payment request into an idempotent provider interaction.",
          proves: ["Retries do not duplicate charges"],
          independence: "Runs against a deterministic provider fixture.",
          consumes: ["payment request v1"],
          produces: ["payment outcome v1"],
          appetite: "2 days",
          yields: ["provider adapter", "idempotency receipt"],
          reverifyWhen: "Provider idempotency or webhook semantics change.",
          artifactIds: [artifactIds.legUi],
        },
      ],
      edges: [
        {
          id: "decompedge_11111111111111111111",
          source: "swimlane-checkout-leg-01",
          target: "swimlane-checkout-leg-02",
          kind: "depends_on",
          artifactIds: [artifactIds.legUi],
        },
      ],
    },
    work: {
      availability: "available",
      tasks: [
        {
          id: "T-ready",
          title: "Dispatchable frontier task",
          status: "ready",
          effort: "S",
          priority: "P1",
          agent: "codex",
          budgetIterations: 4,
          dependsOn: [],
          signedOff: true,
          dispatchable: true,
          blockingReasons: [],
          artifactIds: [artifactIds.task],
        },
        {
          id: "T-blocked",
          title: "Dependency-blocked task",
          status: "blocked",
          effort: "M",
          priority: "P1",
          agent: null,
          budgetIterations: 4,
          dependsOn: ["T-ready"],
          signedOff: true,
          dispatchable: false,
          blockingReasons: ["Waiting for T-ready"],
          artifactIds: [],
        },
        {
          id: "T-progress",
          title: "Task in progress",
          status: "in_progress",
          effort: "S",
          priority: "P2",
          agent: "claude",
          budgetIterations: 4,
          dependsOn: [],
          signedOff: true,
          dispatchable: false,
          blockingReasons: [],
          artifactIds: [],
        },
        {
          id: "T-done",
          title: "Completed task",
          status: "done",
          effort: "XS",
          priority: "P2",
          agent: "kimi",
          budgetIterations: 2,
          dependsOn: [],
          signedOff: true,
          dispatchable: false,
          blockingReasons: [],
          artifactIds: [],
        },
        {
          id: "T-parked",
          title: "Parked task",
          status: "parked",
          effort: "L",
          priority: "P3",
          agent: null,
          budgetIterations: null,
          dependsOn: [],
          signedOff: false,
          dispatchable: false,
          blockingReasons: ["Explicitly parked"],
          artifactIds: [],
        },
      ],
      frontier: {
        taskIds: ["T-ready"],
        blockedTaskIds: ["T-blocked"],
      },
      stats: {
        total: 5,
        ready: 1,
        inProgress: 1,
        blocked: 1,
        done: 1,
        parked: 1,
      },
    },
    execution: {
      availability: "available",
      runs: [
        {
          id: "run-red",
          taskId: "T-ready",
          state: "red",
          attempt: 1,
          budgetIterations: 4,
          runtime: {
            primaryRuntime: "codex",
            assurance: "claude",
          },
          checkpoint: {
            attempt: 1,
            strikes: 1,
            tokensUsed: 900,
            startedAtEpoch: 1_754_252_400,
            elapsedSeconds: 40,
            artifactId: null,
          },
          terminal: null,
          handoffArtifactId: null,
          profileArtifactId: artifactIds.profile,
          artifactIds: [artifactIds.profile],
        },
        {
          id: "run-retry",
          taskId: "T-ready",
          state: "retry",
          attempt: 2,
          budgetIterations: 4,
          runtime: {
            primaryRuntime: "codex",
            assurance: "claude",
          },
          checkpoint: {
            attempt: 2,
            strikes: 1,
            tokensUsed: 1_800,
            startedAtEpoch: 1_754_252_400,
            elapsedSeconds: 90,
            artifactId: null,
          },
          terminal: null,
          handoffArtifactId: null,
          profileArtifactId: artifactIds.profile,
          artifactIds: [artifactIds.profile],
        },
        {
          id: "run-resumed",
          taskId: "T-ready",
          state: "resumed",
          attempt: 3,
          budgetIterations: 4,
          runtime: {
            primaryRuntime: "codex",
            assurance: "claude",
          },
          checkpoint: {
            attempt: 3,
            strikes: 1,
            tokensUsed: 2_600,
            startedAtEpoch: 1_754_252_400,
            elapsedSeconds: 140,
            artifactId: null,
          },
          terminal: null,
          handoffArtifactId: null,
          profileArtifactId: artifactIds.profile,
          artifactIds: [artifactIds.profile],
        },
        {
          id: "run-settled",
          taskId: "T-done",
          state: "settled",
          attempt: null,
          budgetIterations: 2,
          runtime: {
            primaryRuntime: "kimi",
            assurance: "codex",
          },
          checkpoint: null,
          terminal: {
            result: "pass",
            recordedAt: "2026-08-03T19:58:00.000Z",
          },
          handoffArtifactId: null,
          profileArtifactId: artifactIds.profile,
          artifactIds: [artifactIds.profile],
        },
      ],
    },
    receipts: {
      availability: "available",
      items: [
        {
          id: "receipt-verified",
          taskId: "T-done",
          result: "pass",
          recordedAt: "2026-08-03T19:58:00.000Z",
          integrity: "verified",
          freshness: "current",
          bindings: {
            task: {
              path: "cvg/tasks/T-done.md",
              expectedSha256: sha256,
              currentSha256: sha256,
              matches: true,
            },
            executionProfile: {
              path: "cvg/execution/T-done/execution-profile.yaml",
              expectedSha256: sha256,
              currentSha256: sha256,
              matches: true,
            },
            evaluationOutputSha256: sha256,
            pathPolicy: "strict",
          },
          provenance: {
            generatedBy: "cvg loop",
            postHoc: false,
          },
          artifactIds: [artifactIds.receipt],
        },
        {
          id: "receipt-mismatch",
          taskId: "T-progress",
          result: "pass",
          recordedAt: "2026-08-03T19:57:00.000Z",
          integrity: "mismatch",
          freshness: "stale",
          bindings: {
            task: {
              path: "cvg/tasks/T-progress.md",
              expectedSha256: sha256,
              currentSha256: "b".repeat(64),
              matches: false,
            },
            executionProfile: {
              path: "cvg/execution/T-progress/execution-profile.yaml",
              expectedSha256: sha256,
              currentSha256: sha256,
              matches: true,
            },
            evaluationOutputSha256: sha256,
            pathPolicy: "strict",
          },
          provenance: {
            generatedBy: "cvg loop",
            postHoc: false,
          },
          artifactIds: [],
        },
        {
          id: "receipt-unavailable",
          taskId: "T-parked",
          result: "blocked",
          recordedAt: null,
          integrity: "unavailable",
          freshness: "unavailable",
          bindings: {
            task: {
              path: null,
              expectedSha256: null,
              currentSha256: null,
              matches: null,
            },
            executionProfile: {
              path: null,
              expectedSha256: null,
              currentSha256: null,
              matches: null,
            },
            evaluationOutputSha256: null,
            pathPolicy: null,
          },
          provenance: {
            generatedBy: null,
            postHoc: true,
          },
          artifactIds: [],
        },
      ],
    },
    health: {
      overall: "degraded",
      checks: [
        {
          id: "workspace",
          component: "workspace",
          status: "healthy",
          required: true,
          summary: "Canonical control plane is present.",
          artifactIds: [],
        },
        {
          id: "tracker-config",
          component: "tracker-config",
          status: "unavailable",
          required: false,
          summary: "No optional tracker is configured.",
          artifactIds: [],
        },
      ],
    },
    signals: [
      {
        id: "signal-newer",
        kind: "run",
        severity: "warning",
        summary: "Retry was requested.",
        occurredAt: "2026-08-03T19:59:00.000Z",
        entity: { kind: "run", id: "run-retry" },
        artifactIds: [],
      },
      {
        id: "signal-older",
        kind: "run",
        severity: "error",
        summary: "RED evaluation.",
        occurredAt: "2026-08-03T19:55:00.000Z",
        entity: { kind: "run", id: "run-retry" },
        artifactIds: [],
      },
      {
        id: "signal-no-time",
        kind: "gate",
        severity: "warning",
        summary: "Consensus remains blocked.",
        occurredAt: null,
        entity: { kind: "pass", id: "pass-4" },
        artifactIds: [artifactIds.review],
      },
      {
        id: "signal-misleading-text",
        kind: "task",
        severity: "info",
        summary: "Text mentions run-retry but has no entity reference.",
        occurredAt: "2026-08-03T19:59:30.000Z",
        artifactIds: [],
      },
    ],
    issues: [
      {
        id: issueIds.review,
        code: "REVIEW_UNRESOLVED",
        severity: "blocking",
        domain: "review",
        message: "Pass 4 needs an owner decision.",
        entity: { kind: "pass", id: "pass-4" },
        remediation: "Record the owner decision.",
        artifactIds: [artifactIds.review],
      },
      {
        id: issueIds.unlinked,
        code: "TEXT_IS_NOT_A_LINK",
        severity: "warning",
        domain: "work",
        message: "This prose mentions pass-4 but deliberately has no entity.",
        artifactIds: [],
      },
    ],
    authorization: {
      state: "blocked",
      nextPassId: "pass-4",
      command: "cvg review --check",
      mutation: "non_mutating",
      dryRunSupported: false,
      enabled: false,
      rationale: "The owner-decision barrier remains open.",
      blockingIssueIds: [issueIds.review],
    },
    artifacts: [
      {
        id: artifactIds.review,
        label: "Consensus review",
        path: "cvg/swimlanes/.consensus/objection-log.json",
        kind: "review",
        sha256,
        entity: { kind: "pass", id: "pass-4" },
        provenance: {
          sourceKind: "file",
          sourceRef: "cvg/swimlanes/.consensus/objection-log.json",
          observedAt,
          truthClass: "canonical",
        },
      },
      {
        id: artifactIds.task,
        label: "Task specification",
        path: "cvg/tasks/T-ready.md",
        kind: "task",
        sha256,
        entity: { kind: "task", id: "T-ready" },
        provenance: {
          sourceKind: "file",
          sourceRef: "cvg/tasks/T-ready.md",
          observedAt,
          truthClass: "canonical",
        },
      },
      {
        id: artifactIds.profile,
        label: "Execution profile",
        path: "cvg/execution/T-ready/execution-profile.yaml",
        kind: "contract",
        sha256,
        entity: { kind: "run", id: "run-retry" },
        provenance: {
          sourceKind: "file",
          sourceRef: "cvg bind",
          observedAt,
          truthClass: "canonical",
        },
      },
      {
        id: artifactIds.receipt,
        label: "Settlement receipt",
        path: "cvg/receipts/T-done.json",
        kind: "receipt",
        sha256,
        entity: { kind: "receipt", id: "receipt-verified" },
        provenance: {
          sourceKind: "file",
          sourceRef: "cvg/receipts/T-done.json",
          observedAt,
          truthClass: "canonical",
        },
      },
      {
        id: artifactIds.lane,
        label: "Checkout swimlane",
        path: "cvg/swimlanes/checkout/_lane.md",
        kind: "plan",
        sha256,
        entity: { kind: "swimlane", id: "swimlane-checkout" },
        provenance: {
          sourceKind: "file",
          sourceRef: "cvg/swimlanes/checkout/_lane.md",
          observedAt,
          truthClass: "canonical",
        },
      },
      {
        id: artifactIds.legApi,
        label: "Accept checkout intent",
        path: "cvg/swimlanes/checkout/leg-01-fastapi.md",
        kind: "plan",
        sha256,
        entity: { kind: "leg", id: "swimlane-checkout-leg-01" },
        provenance: {
          sourceKind: "file",
          sourceRef: "cvg/swimlanes/checkout/leg-01-fastapi.md",
          observedAt,
          truthClass: "canonical",
        },
      },
      {
        id: artifactIds.legUi,
        label: "Settle payment outcome",
        path: "cvg/swimlanes/checkout/leg-02-stripe.md",
        kind: "plan",
        sha256,
        entity: { kind: "leg", id: "swimlane-checkout-leg-02" },
        provenance: {
          sourceKind: "file",
          sourceRef: "cvg/swimlanes/checkout/leg-02-stripe.md",
          observedAt,
          truthClass: "canonical",
        },
      },
    ],
  };

  mutate?.(snapshot);
  return snapshot;
}

export function makeEmptySnapshot(): WorkspaceSnapshot {
  return makeScenarioSnapshot((snapshot) => {
    snapshot.snapshotId = "ws3_00000000000000000000000000000002";
    snapshot.decomposition = {
      availability: "empty",
      swimlanes: [],
      legs: [],
      edges: [],
    };
    const pass = snapshot.method.passes.find((item) => item.id === "pass-3");
    if (pass) pass.artifactIds = [];
    snapshot.work = {
      availability: "empty",
      tasks: [],
      frontier: { taskIds: [], blockedTaskIds: [] },
      stats: {
        total: 0,
        ready: 0,
        inProgress: 0,
        blocked: 0,
        done: 0,
        parked: 0,
      },
    };
    snapshot.execution = { availability: "empty", runs: [] };
    snapshot.receipts = { availability: "empty", items: [] };
    snapshot.signals = snapshot.signals.filter(
      (signal) =>
        signal.entity?.kind !== "task" &&
        signal.entity?.kind !== "run" &&
        signal.entity?.kind !== "receipt",
    );
    snapshot.artifacts = snapshot.artifacts
      .filter(
        (artifact) =>
          artifact.entity?.kind !== "swimlane" &&
          artifact.entity?.kind !== "leg",
      )
      .map((artifact) => {
      if (
        artifact.entity?.kind !== "task" &&
        artifact.entity?.kind !== "run" &&
        artifact.entity?.kind !== "receipt"
      ) {
        return artifact;
      }
      const { entity: _entity, ...unlinkedArtifact } = artifact;
      return unlinkedArtifact;
      });
  });
}

export function makeScenarioEnvelope(
  snapshot = makeScenarioSnapshot(),
  mutate?: (envelope: SnapshotEnvelope) => void,
): SnapshotEnvelope {
  const envelope: SnapshotEnvelope = {
    snapshot,
    transport: {
      stale: false,
      servedAt: "2026-08-03T20:00:01.000Z",
    },
  };
  mutate?.(envelope);
  return envelope;
}

export function makeStaleEnvelope(): SnapshotEnvelope {
  return makeScenarioEnvelope(makeScenarioSnapshot(), (envelope) => {
    envelope.transport = {
      stale: true,
      servedAt: "2026-08-03T20:01:00.000Z",
      error: {
        code: "SNAPSHOT_REFRESH_FAILED",
        message: "The CLI snapshot could not be refreshed.",
      },
    };
  });
}
