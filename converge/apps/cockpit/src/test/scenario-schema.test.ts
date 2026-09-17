import { describe, expect, it } from "vitest";
import snapshotSchema from "../../../../contracts/ui/v3/workspace-snapshot.schema.json";
// The bridge validator is intentionally framework-free JavaScript.
// @ts-expect-error no declaration file is shipped for the local bridge module
import { validateJsonSchema } from "../../server/schema.mjs";
import { isWorkspaceSnapshot } from "../lib/snapshot";
import {
  makeEmptySnapshot,
  makeScenarioSnapshot,
  makeStaleEnvelope,
} from "./scenarios";

describe("shared Cockpit verification scenarios", () => {
  it.each([
    ["lifecycle", makeScenarioSnapshot],
    ["empty", makeEmptySnapshot],
  ])("keeps the %s scenario valid in both contract validators", (
    _label,
    makeSnapshot,
  ) => {
    const snapshot = makeSnapshot();

    expect(validateJsonSchema(snapshot, snapshotSchema)).toEqual([]);
    expect(isWorkspaceSnapshot(snapshot)).toBe(true);
  });

  it("keeps stale transport metadata outside the semantic snapshot digest input", () => {
    const envelope = makeStaleEnvelope();

    expect(envelope.transport.stale).toBe(true);
    expect(Object.hasOwn(envelope.snapshot, "transport")).toBe(false);
    expect(envelope.snapshot.source).toBe("fixture");
  });
});
