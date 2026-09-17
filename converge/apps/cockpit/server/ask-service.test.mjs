import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { createAgentRegistry } from "./acp/agent-registry.mjs";
import { AcpClient } from "./acp/client.mjs";
import { createAskService } from "./ask-service.mjs";

const SERVER_ROOT = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(SERVER_ROOT, "..");
const FIXTURE = path.join(SERVER_ROOT, "test-fixtures", "fake-acp-agent.mjs");

function workspaceSnapshot(snapshotId = "ws_snapshot_123456") {
  return {
    schemaVersion: "3.0",
    snapshotId,
    observedAt: "2026-08-03T12:00:00.000Z",
    source: "workspace",
    project: {
      name: "Example",
      root: PROJECT_ROOT,
      lane: "NORMAL",
      git: { branch: "main", commit: "abc", dirty: false },
    },
    method: { version: "0.1.0", activePassId: "pass-2", passes: [{ id: "pass-2", label: "Journey" }] },
    decomposition: {
      availability: "available",
      swimlanes: [{ id: "lane-1", label: "Backend" }],
      legs: [{ id: "leg-1", swimlaneId: "lane-1" }],
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
        id: "artifact-readme",
        label: "README",
        path: "README.md",
        kind: "document",
        sha256: "a".repeat(64),
        provenance: { truthClass: "canonical" },
      },
    ],
  };
}

function makeService({ fixtureArgs = [], maxEvents, snapshotRef } = {}) {
  let nextId = 0;
  const current = snapshotRef ?? { value: workspaceSnapshot() };
  const registry = createAgentRegistry({
    projectRoot: PROJECT_ROOT,
    adapters: [
      {
        id: "fake",
        label: "Fake agent",
        executable: process.execPath,
        args: [FIXTURE, ...fixtureArgs],
        environment: {
          HOME: process.env.HOME,
          PATH: process.env.PATH,
          NO_COLOR: "1",
        },
        requiredMode: "read-only",
        disableBuiltInTools: true,
        contextIsolation: "verified",
      },
    ],
  });
  return createAskService({
    registry,
    snapshotService: {
      async getSnapshot() {
        return { snapshot: current.value, transport: { stale: false } };
      },
    },
    artifactStore: {
      async read(_path, { snapshotId, expectedSha256 }) {
        assert.equal(snapshotId, current.value.snapshotId);
        assert.equal(expectedSha256, "a".repeat(64));
        return { format: "markdown", content: "# Grounded README", truncated: false };
      },
    },
    methodologyProvider: async () => ({
      digest: "c".repeat(64),
      document: {
        schema_version: "1.0",
        tool: "cvg",
        version: "0.1.0",
        role: "referee",
        description: "Canonical Converge method.",
        contracts: { determinism: "read-only gates" },
        exit_codes: [{ code: 0, name: "OK" }],
        commands: [{
          name: "capture",
          converge_pass: 0,
          mutating: false,
          emits_tokens: ["CHECK_BRD=PASS"],
          example: "cvg capture",
          description: "Pass 0 gate.",
        }],
      },
    }),
    clientFactory: (options) => new AcpClient({ ...options, turnTimeoutMs: 2_000 }),
    idFactory: () => `id-${++nextId}`,
    ...(maxEvents ? { maxEvents } : {}),
  });
}

test("AskService runs one snapshot-bound ephemeral turn with normalized events", async (t) => {
  const service = makeService({ fixtureArgs: ["--require-history"] });
  t.after(() => service.close());
  assert.equal((await service.listAgents()).agents[0].availability, "available");
  const created = await service.createSession({
    agentId: "fake",
    snapshotId: "ws_snapshot_123456",
    context: {
      entity: { kind: "swimlane", id: "lane-1" },
      artifactIds: ["artifact-readme"],
    },
  });
  assert.equal(created.session.state, "ready");
  assert.equal(created.session.protocolVersion, 1);
  assert.equal(created.session.grounding.entity.kind, "swimlane");

  const turn = await service.startTurn(created.session.id, {
    text: "Explain this lane.",
    snapshotId: "ws_snapshot_123456",
    history: [
      { role: "user", text: "Earlier question" },
      { role: "assistant", text: "TOKEN=super-secret-value" },
    ],
  });
  await service.waitForTurn(created.session.id);
  const events = service.getEvents(created.session.id).events;
  assert.equal(events[0].type, "turn.started");
  assert.ok(events.some((event) => event.type === "permission.denied"));
  assert.equal(events.at(-1).type, "turn.completed");
  assert.equal(service.getSession(created.session.id).session.state, "completed");
  assert.ok(events.every((event, index) => event.sequence === index + 1));
  assert.ok(service.getEvents(created.session.id, { after: 2 }).events.every(
    (event) => event.sequence > 2,
  ));
  await assert.rejects(
    service.startTurn(created.session.id, {
      text: "Ask twice",
      snapshotId: "ws_snapshot_123456",
    }),
    { code: "ASK_TURN_ALREADY_USED" },
  );
  assert.equal(turn.state, "running");
});

test("AskService rejects stale turns and converts output overflow to a typed failure", async (t) => {
  const snapshotRef = { value: workspaceSnapshot() };
  const stale = makeService({ snapshotRef });
  t.after(() => stale.close());
  const created = await stale.createSession({
    agentId: "fake",
    snapshotId: snapshotRef.value.snapshotId,
    context: { artifactIds: [] },
  });
  snapshotRef.value = workspaceSnapshot("ws_snapshot_changed_456");
  await assert.rejects(
    stale.startTurn(created.session.id, {
      text: "Use stale context",
      snapshotId: created.session.grounding.snapshotId,
    }),
    { code: "ASK_SNAPSHOT_STALE" },
  );

  const changedDuringTurnRef = { value: workspaceSnapshot() };
  const changedDuringTurn = makeService({ snapshotRef: changedDuringTurnRef });
  t.after(() => changedDuringTurn.close());
  const active = await changedDuringTurn.createSession({
    agentId: "fake",
    snapshotId: changedDuringTurnRef.value.snapshotId,
    context: { artifactIds: [] },
  });
  await changedDuringTurn.startTurn(active.session.id, {
    text: "Explain only if this remains current.",
    snapshotId: active.session.grounding.snapshotId,
  });
  changedDuringTurnRef.value = workspaceSnapshot("ws_snapshot_changed_during_turn");
  await assert.rejects(changedDuringTurn.waitForTurn(active.session.id), {
    code: "ASK_SNAPSHOT_STALE",
  });
  assert.equal(
    changedDuringTurn.getEvents(active.session.id).events.at(-1).payload.code,
    "ASK_SNAPSHOT_STALE",
  );

  const bounded = makeService({ maxEvents: 4 });
  t.after(() => bounded.close());
  const boundedSession = await bounded.createSession({
    agentId: "fake",
    snapshotId: "ws_snapshot_123456",
    context: { artifactIds: [] },
  });
  await bounded.startTurn(boundedSession.session.id, {
    text: "Produce bounded output",
    snapshotId: "ws_snapshot_123456",
  });
  await bounded.waitForTurn(boundedSession.session.id);
  const boundedEvents = bounded.getEvents(boundedSession.session.id).events;
  assert.equal(bounded.getSession(boundedSession.session.id).session.state, "failed");
  assert.equal(boundedEvents.at(-1).payload.code, "ASK_OUTPUT_LIMIT");
  assert.ok(boundedEvents.length <= 4);
});

test("AskService cancellation reaches the ACP session and closes the child", async (t) => {
  const service = makeService({ fixtureArgs: ["--hang"] });
  t.after(() => service.close());
  const created = await service.createSession({
    agentId: "fake",
    snapshotId: "ws_snapshot_123456",
    context: { artifactIds: [] },
  });
  const turn = await service.startTurn(created.session.id, {
    text: "Wait until cancelled",
    snapshotId: "ws_snapshot_123456",
  });
  await service.cancelTurn(created.session.id, turn.turnId);
  await service.waitForTurn(created.session.id);
  assert.equal(service.getSession(created.session.id).session.state, "cancelled");
  assert.equal(
    service.getEvents(created.session.id).events.at(-1).payload.stopReason,
    "cancelled",
  );
});

test("AskService exposes authentication recovery instead of a generic provider failure", async (t) => {
  const service = makeService({ fixtureArgs: ["--auth-required"] });
  t.after(() => service.close());
  const created = await service.createSession({
    agentId: "fake",
    snapshotId: "ws_snapshot_123456",
    context: { artifactIds: [] },
  });
  await service.startTurn(created.session.id, {
    text: "Explain this project.",
    snapshotId: "ws_snapshot_123456",
  });
  await service.waitForTurn(created.session.id);
  const failure = service.getEvents(created.session.id).events.at(-1);
  assert.equal(failure.type, "turn.failed");
  assert.equal(failure.payload.code, "ASK_AUTH_REQUIRED");
  assert.equal(failure.payload.retryable, true);
});

test("AskService rejects a context-isolation-blocked adapter before spawn", async () => {
  const registry = createAgentRegistry({
    projectRoot: PROJECT_ROOT,
    adapters: [
      {
        id: "codex",
        label: "Codex",
        executable: process.execPath,
        args: [],
        environment: {
          HOME: process.env.HOME,
          PATH: process.env.PATH,
          INITIAL_AGENT_MODE: "read-only",
        },
        requiredMode: "read-only",
        contextIsolation: "unsupported",
        blockedReason: "Local reads cannot be suppressed.",
      },
    ],
  });
  let spawned = false;
  const service = createAskService({
    registry,
    snapshotService: {
      async getSnapshot() {
        return { snapshot: workspaceSnapshot(), transport: { stale: false } };
      },
    },
    artifactStore: {},
    methodologyProvider: async () => {
      throw new Error("blocked adapters must fail before methodology loading");
    },
    clientFactory() {
      spawned = true;
      throw new Error("must not spawn");
    },
  });

  await assert.rejects(
    service.createSession({
      agentId: "codex",
      snapshotId: "ws_snapshot_123456",
      context: { artifactIds: [] },
    }),
    { code: "ASK_AGENT_UNAVAILABLE" },
  );
  assert.equal(spawned, false);
});
