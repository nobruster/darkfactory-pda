import { describe, expect, it } from "vitest";
import {
  artifactsByIds,
  entityExists,
  entityKey,
  relatedSignals,
  resolveEntity,
  sameEntity,
} from "./entities";
import { makeScenarioSnapshot } from "../test/scenarios";
import type { EntityRef } from "../types";

describe("typed Cockpit entity navigation", () => {
  it("compares and keys references by both kind and id", () => {
    expect(
      sameEntity(
        { kind: "task", id: "shared" },
        { kind: "task", id: "shared" },
      ),
    ).toBe(true);
    expect(
      sameEntity(
        { kind: "task", id: "shared" },
        { kind: "run", id: "shared" },
      ),
    ).toBe(false);
    expect(entityKey({ kind: "receipt", id: "receipt-verified" })).toBe(
      "receipt:receipt-verified",
    );
  });

  it("associates signals only through explicit entity references, never prose", () => {
    const snapshot = makeScenarioSnapshot();
    const signals = relatedSignals(snapshot, {
      kind: "run",
      id: "run-retry",
    });

    expect(signals.map((signal) => signal.id)).toEqual([
      "signal-newer",
      "signal-older",
    ]);
    expect(signals.map((signal) => signal.id)).not.toContain(
      "signal-misleading-text",
    );
  });

  it("orders explicitly related signals newest first and keeps untimed signals usable", () => {
    const snapshot = makeScenarioSnapshot();

    expect(
      relatedSignals(snapshot, { kind: "run", id: "run-retry" }).map(
        (signal) => signal.id,
      ),
    ).toEqual(["signal-newer", "signal-older"]);
    expect(
      relatedSignals(snapshot, { kind: "pass", id: "pass-4" }).map(
        (signal) => signal.id,
      ),
    ).toEqual(["signal-no-time"]);
  });

  it("resolves each supported semantic entity without inventing one", () => {
    const snapshot = makeScenarioSnapshot();
    const cases: Array<EntityRef & { title: string }> = [
      { kind: "pass", id: "pass-4", title: "Consensus" },
      { kind: "task", id: "T-ready", title: "Dispatchable frontier task" },
      { kind: "run", id: "run-retry", title: "run-retry" },
      {
        kind: "receipt",
        id: "receipt-verified",
        title: "receipt-verified",
      },
      { kind: "health", id: "workspace", title: "workspace" },
      {
        kind: "signal",
        id: "signal-newer",
        title: "Retry was requested.",
      },
      {
        kind: "issue",
        id: "issue_11111111111111111111",
        title: "review",
      },
      {
        kind: "artifact",
        id: "artifact_22222222222222222222",
        title: "Task specification",
      },
    ];

    for (const candidate of cases) {
      expect(resolveEntity(snapshot, candidate)).toMatchObject({
        ref: { kind: candidate.kind, id: candidate.id },
        title: candidate.title,
      });
      expect(entityExists(snapshot, candidate)).toBe(true);
    }

    expect(resolveEntity(snapshot, { kind: "task", id: "missing" })).toBeNull();
    expect(entityExists(snapshot, { kind: "task", id: "missing" })).toBe(false);
  });

  it("looks up proof only through artifact ids", () => {
    const snapshot = makeScenarioSnapshot();

    expect(
      artifactsByIds(snapshot, [
        "artifact_22222222222222222222",
        "artifact_11111111111111111111",
      ]).map((artifact) => artifact.id),
    ).toEqual([
      "artifact_11111111111111111111",
      "artifact_22222222222222222222",
    ]);
    expect(artifactsByIds(snapshot, ["cvg/tasks/T-ready.md"])).toEqual([]);
  });

  it("keeps receipt integrity variants semantically distinct", () => {
    const snapshot = makeScenarioSnapshot();

    expect(
      snapshot.receipts.items.map((receipt) => [
        receipt.id,
        resolveEntity(snapshot, { kind: "receipt", id: receipt.id })?.status,
      ]),
    ).toEqual([
      ["receipt-verified", "verified"],
      ["receipt-mismatch", "mismatch"],
      ["receipt-unavailable", "unavailable"],
    ]);
  });
});
