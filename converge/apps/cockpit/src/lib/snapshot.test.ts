import { describe, expect, it } from "vitest";
import {
  decodeSnapshotPayload,
  isSnapshotEnvelope,
  isWorkspaceSnapshot,
} from "./snapshot";
import {
  makeScenarioEnvelope,
  makeScenarioSnapshot,
  makeStaleEnvelope,
} from "../test/scenarios";

describe("WorkspaceSnapshot 3.0 client boundary", () => {
  it("accepts a complete semantic snapshot with nullable event and attempt fields", () => {
    const snapshot = makeScenarioSnapshot();

    expect(snapshot.signals.some((signal) => signal.occurredAt === null)).toBe(
      true,
    );
    expect(snapshot.execution.runs.some((run) => run.attempt === null)).toBe(
      true,
    );
    expect(isWorkspaceSnapshot(snapshot)).toBe(true);
  });

  it("accepts and decodes the bridge transport envelope", () => {
    const envelope = makeScenarioEnvelope();

    expect(isSnapshotEnvelope(envelope)).toBe(true);
    expect(decodeSnapshotPayload(envelope)).toEqual(envelope);
  });

  it("rejects a raw snapshot because transport truth must come from the bridge", () => {
    const snapshot = makeScenarioSnapshot();

    expect(isWorkspaceSnapshot(snapshot)).toBe(true);
    expect(decodeSnapshotPayload(snapshot)).toBeNull();
  });

  it("preserves explicit stale transport state outside the semantic snapshot", () => {
    const envelope = makeStaleEnvelope();

    expect(decodeSnapshotPayload(envelope)).toEqual(envelope);
    expect(envelope.transport.stale).toBe(true);
    expect(envelope.snapshot).not.toHaveProperty("transport");
  });

  it.each([
    ["schema version", (value: Record<string, unknown>) => (value.schemaVersion = "1.0")],
    ["source label", (value: Record<string, unknown>) => (value.source = "live")],
    ["snapshot id", (value: Record<string, unknown>) => delete value.snapshotId],
    [
      "artifact digest",
      (value: Record<string, unknown>) => {
        const artifacts = value.artifacts as Array<Record<string, unknown>>;
        artifacts[0].sha256 = "not-a-digest";
      },
    ],
    [
      "typed issue severity",
      (value: Record<string, unknown>) => {
        const issues = value.issues as Array<Record<string, unknown>>;
        issues[0].severity = "urgent";
      },
    ],
    [
      "entity kind",
      (value: Record<string, unknown>) => {
        const issues = value.issues as Array<Record<string, unknown>>;
        issues[0].entity = { kind: "invented", id: "pass-4" };
      },
    ],
    [
      "dangling entity reference",
      (value: Record<string, unknown>) => {
        const issues = value.issues as Array<Record<string, unknown>>;
        issues[0].entity = { kind: "task", id: "missing-task" };
      },
    ],
    [
      "missing decomposition edge",
      (value: Record<string, unknown>) => {
        const decomposition = value.decomposition as Record<string, unknown>;
        decomposition.edges = [];
      },
    ],
    [
      "inconsistent swimlane membership",
      (value: Record<string, unknown>) => {
        const decomposition = value.decomposition as {
          swimlanes: Array<Record<string, unknown>>;
        };
        decomposition.swimlanes[0].legIds = [];
      },
    ],
    [
      "cyclic decomposition dependency",
      (value: Record<string, unknown>) => {
        const decomposition = value.decomposition as {
          legs: Array<{
            id: string;
            dependsOn: string[];
            artifactIds: string[];
          }>;
          edges: Array<Record<string, unknown>>;
        };
        const leg = decomposition.legs[0];
        leg.dependsOn.push(leg.id);
        decomposition.edges.push({
          id: "decompedge_ffffffffffffffffffff",
          source: leg.id,
          target: leg.id,
          kind: "depends_on",
          artifactIds: leg.artifactIds,
        });
      },
    ],
    [
      "dangling artifact reference",
      (value: Record<string, unknown>) => {
        const method = value.method as {
          passes: Array<Record<string, unknown>>;
        };
        method.passes[0].artifactIds = ["artifact_ffffffffffffffffffff"];
      },
    ],
  ])("rejects a snapshot with invalid %s", (_label, mutate) => {
    const candidate = makeScenarioSnapshot() as unknown as Record<
      string,
      unknown
    >;
    mutate(candidate);

    expect(isWorkspaceSnapshot(candidate)).toBe(false);
    expect(decodeSnapshotPayload(candidate)).toBeNull();
  });

  it("rejects malformed transport metadata even when the snapshot is valid", () => {
    const envelope = makeScenarioEnvelope() as unknown as {
      snapshot: unknown;
      transport: Record<string, unknown>;
    };
    envelope.transport.servedAt = "not-a-date";

    expect(isSnapshotEnvelope(envelope)).toBe(false);
    expect(decodeSnapshotPayload(envelope)).toBeNull();
  });
});
