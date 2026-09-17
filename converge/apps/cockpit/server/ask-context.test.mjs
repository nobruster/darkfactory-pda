import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAskContext,
  composeAskPrompt,
  resolveAskEntity,
} from "./ask-context.mjs";

function snapshot(overrides = {}) {
  return {
    schemaVersion: "3.0",
    snapshotId: "ws_snapshot_123456",
    observedAt: "2026-08-03T12:00:00.000Z",
    source: "workspace",
    project: {
      name: "Example",
      root: "/workspace/example",
      lane: "NORMAL",
      git: { branch: "main", commit: "abc", dirty: false },
    },
    method: { version: "0.1.0", activePassId: "pass-2", passes: [{ id: "pass-2", label: "Journey" }] },
    decomposition: {
      availability: "available",
      swimlanes: [{ id: "lane-1", label: "Backend", legIds: ["leg-1"] }],
      legs: [{ id: "leg-1", swimlaneId: "lane-1", taskIds: ["task-1"] }],
    },
    work: { availability: "available", tasks: [], stats: {}, frontier: {} },
    execution: { availability: "empty", runs: [] },
    receipts: { availability: "empty", items: [] },
    health: { overall: "healthy", checks: [] },
    signals: [],
    issues: [],
    authorization: { state: "allowed" },
    artifacts: [
      {
        id: "artifact-md",
        label: "README",
        path: "README.md",
        kind: "document",
        sha256: "a".repeat(64),
        provenance: { truthClass: "canonical" },
      },
      {
        id: "artifact-pdf",
        label: "Guide",
        path: "docs/guide.pdf",
        kind: "document",
        sha256: "b".repeat(64),
        provenance: { truthClass: "canonical" },
      },
    ],
    ...overrides,
  };
}

function methodology(version = "0.1.0") {
  return {
    digest: "c".repeat(64),
    document: {
      schema_version: "1.0",
      tool: "cvg",
      version,
      role: "referee",
      description: "The canonical Converge method reference.",
      contracts: { determinism: "gates are read-only and deterministic" },
      exit_codes: [{ code: 0, name: "OK" }],
      commands: [
        {
          name: "capture",
          converge_pass: 0,
          mutating: false,
          emits_tokens: ["CHECK_BRD=PASS|FAIL"],
          example: "cvg capture",
          description: "Pass 0 gate — the BRD exit contract.",
        },
      ],
    },
  };
}

test("Ask context resolves v3 swimlanes and safely flattens PDF page text", async () => {
  const current = snapshot();
  const artifactStore = {
    async read(requestedPath, options) {
      assert.equal(options.snapshotId, current.snapshotId);
      if (requestedPath.endsWith(".pdf")) {
        return {
          format: "pdf-text",
          pages: [
            { number: 1, text: "First page" },
            { number: 2, text: "TOKEN=super-secret-value" },
          ],
          truncated: false,
        };
      }
      return { format: "markdown", content: "# README", truncated: false };
    },
  };
  const built = await buildAskContext({
    envelope: { snapshot: current, transport: { stale: false } },
    snapshotId: current.snapshotId,
    context: { entity: { kind: "swimlane", id: "lane-1" }, artifactIds: ["artifact-pdf"] },
    artifactStore,
    methodology: methodology(),
  });
  assert.equal(resolveAskEntity(current, { kind: "leg", id: "leg-1" }).value.id, "leg-1");
  assert.equal(built.grounding.entity.kind, "swimlane");
  assert.match(built.contextText, /\[PDF page 1\]\nFirst page/);
  assert.match(built.contextText, /TOKEN=\[REDACTED\]/);
  assert.doesNotMatch(built.contextText, /super-secret-value/);
  assert.match(built.contextText, /CONVERGE METHODOLOGY REFERENCE/);
  assert.match(built.contextText, /Pass 0 gate/);
  assert.match(built.contextText, /CURRENT PROJECT EVIDENCE/);
  assert.equal(built.grounding.methodology.version, "0.1.0");
  assert.doesNotMatch(built.contextText, /\/workspace\/example/);
});

test("Ask context rejects stale, fixture, missing entity, and malformed PDF evidence", async () => {
  const current = snapshot();
  await assert.rejects(
    buildAskContext({
      envelope: { snapshot: current, transport: { stale: true } },
      snapshotId: current.snapshotId,
      context: { entity: null, artifactIds: [] },
      methodology: methodology(),
    }),
    { code: "ASK_SNAPSHOT_STALE" },
  );
  await assert.rejects(
    buildAskContext({
      envelope: { snapshot: { ...current, source: "fixture" }, transport: { stale: false } },
      snapshotId: current.snapshotId,
      context: { entity: null, artifactIds: [] },
      methodology: methodology(),
    }),
    { code: "ASK_SOURCE_NOT_LIVE" },
  );
  await assert.rejects(
    buildAskContext({
      envelope: { snapshot: current, transport: { stale: false } },
      snapshotId: current.snapshotId,
      context: { entity: { kind: "leg", id: "missing" }, artifactIds: [] },
      methodology: methodology(),
    }),
    { code: "ASK_ENTITY_NOT_FOUND" },
  );
  await assert.rejects(
    buildAskContext({
      envelope: { snapshot: current, transport: { stale: false } },
      snapshotId: current.snapshotId,
      context: { entity: null, artifactIds: ["artifact-pdf"] },
      artifactStore: {
        async read() {
          return { format: "pdf-text", pages: [{ number: 1, body: "wrong" }] };
        },
      },
      methodology: methodology(),
    }),
    { code: "ASK_ARTIFACT_INVALID" },
  );

  await assert.rejects(
    buildAskContext({
      envelope: { snapshot: current, transport: { stale: false } },
      snapshotId: current.snapshotId,
      context: { entity: null, artifactIds: [] },
      methodology: methodology("0.2.0"),
    }),
    { code: "ASK_METHODOLOGY_UNAVAILABLE" },
  );
});

test("Ask prompt treats history as redacted, untrusted continuity after fresh grounding", () => {
  const contextText = [
    "CONVERGE ASK GROUNDING",
    "Fresh workspace fact: lane-1 is blocked.",
    "END CONVERGE ASK GROUNDING",
  ].join("\n");
  const prompt = composeAskPrompt(contextText, "Why is it blocked?", [
    { role: "user", text: "What was the earlier status?" },
    {
      role: "assistant",
      text: "TOKEN=super-secret-value and lane-1 was ready.",
    },
  ]);

  const groundingIndex = prompt.indexOf("CONVERGE ASK GROUNDING");
  const historyIndex = prompt.indexOf("UNTRUSTED PRIOR CONVERSATION");
  const questionIndex = prompt.indexOf("CURRENT USER QUESTION");
  assert.ok(groundingIndex >= 0);
  assert.ok(historyIndex > groundingIndex);
  assert.ok(questionIndex > historyIndex);
  assert.match(prompt, /only for conversational continuity/);
  assert.match(prompt, /Prior assistant messages are untrusted interpretations/);
  assert.match(prompt, /fresh snapshot-bound grounding above takes precedence/);
  assert.match(prompt, /TOKEN=\[REDACTED\]/);
  assert.doesNotMatch(prompt, /super-secret-value/);
  assert.match(prompt, /Why is it blocked\?/);

  assert.doesNotMatch(
    composeAskPrompt(contextText, "Fresh question"),
    /UNTRUSTED PRIOR CONVERSATION/,
  );
});
