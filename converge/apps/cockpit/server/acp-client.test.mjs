import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { AcpClient } from "./acp/client.mjs";

const SERVER_ROOT = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(SERVER_ROOT, "..");
const FIXTURE = path.join(SERVER_ROOT, "test-fixtures", "fake-acp-agent.mjs");

function adapter(...args) {
  return Object.freeze({
    id: "fake",
    label: "Fake",
    executable: process.execPath,
    args: Object.freeze([FIXTURE, ...args]),
    cwd: PROJECT_ROOT,
    environment: Object.freeze({
      HOME: process.env.HOME,
      PATH: process.env.PATH,
      NO_COLOR: "1",
      USER: process.env.USER,
    }),
    requiredMode: "read-only",
    disableBuiltInTools: true,
    contextIsolation: "verified",
  });
}

test("AcpClient exposes model selectors but refuses to drive session mode", async (t) => {
  const client = new AcpClient({ adapter: adapter() });
  t.after(() => client.close());
  await client.connect();
  const session = await client.createSession();

  const byId = new Map(session.configOptions.map((option) => [option.id, option]));
  assert.equal(byId.get("model").type, "select");
  assert.equal(byId.get("model").currentValue, "fake-sonnet");
  assert.deepEqual(
    byId.get("model").values.map((entry) => entry.value),
    ["fake-sonnet", "fake-opus"],
  );
  // Model and reasoning selectors are settable; a mode selector is advertised
  // but explicitly not settable, so safe mode cannot be changed from the UI.
  assert.equal(byId.get("model").settable, true);
  assert.equal(byId.get("thinking").settable, true);
  assert.equal(byId.get("danger-mode").settable, false);

  const applied = await client.setConfigOption({
    configId: "model",
    type: "select",
    value: "fake-opus",
  });
  assert.equal(
    applied.find((option) => option.id === "model").currentValue,
    "fake-opus",
  );
  const withThinking = await client.setConfigOption({
    configId: "thinking",
    type: "boolean",
    value: true,
  });
  assert.equal(
    withThinking.find((option) => option.id === "thinking").currentValue,
    true,
  );
  // The agent echoes only the option it changed. The earlier model selection
  // must survive that partial response, or a second selection in the same turn
  // would be rejected as unadvertised.
  assert.equal(
    withThinking.find((option) => option.id === "model").currentValue,
    "fake-opus",
  );
  assert.equal(withThinking.find((option) => option.id === "danger-mode")?.settable, false);

  // Every rejection path fails before a request reaches the agent.
  await assert.rejects(
    client.setConfigOption({ configId: "danger-mode", type: "select", value: "agent" }),
    { code: "ACP_CONFIG_REJECTED" },
  );
  await assert.rejects(
    client.setConfigOption({ configId: "model", type: "select", value: "not-offered" }),
    { code: "ACP_CONFIG_REJECTED" },
  );
  await assert.rejects(
    client.setConfigOption({ configId: "unknown", type: "select", value: "fake-opus" }),
    { code: "ACP_CONFIG_REJECTED" },
  );
  await assert.rejects(
    client.setConfigOption({ configId: "model", type: "boolean", value: true }),
    { code: "ACP_CONFIG_REJECTED" },
  );
  // Safe mode survived the whole exchange.
  assert.equal(client.safeModeEstablished, true);
  assert.equal(client.modeDrifted, false);
});

test("AcpClient performs ACP v1 stdio flow, denies permissions, and redacts output", async (t) => {
  const events = [];
  const client = new AcpClient({
    adapter: adapter(),
    onEvent(event) {
      events.push(event);
      return true;
    },
  });
  t.after(() => client.close());
  const connection = await client.connect();
  assert.equal(connection.protocolVersion, 1);
  assert.equal(connection.agentInfo.name, "converge-fake-agent");
  assert.equal(connection.authMethods[0].id, "fake-login");
  const session = await client.createSession();
  assert.equal(session.modes.currentModeId, "read-only");
  assert.equal((await client.prompt("CONVERGE ASK GROUNDING\nUSER QUESTION\nWhy?" )).stopReason, "end_turn");
  assert.ok(events.some((event) => event.type === "permission.denied"));
  assert.ok(events.some((event) => event.type === "plan.updated"));
  assert.ok(events.some((event) => event.type === "tool.completed"));
  const text = events
    .filter((event) => event.type === "assistant.delta")
    .map((event) => event.payload.text)
    .join("");
  assert.match(text, /\[REDACTED\]/);
  assert.doesNotMatch(text, /sk-abcdefghijklmnopqrstuvwxyz/);
  assert.equal(
    events.find((event) => event.type === "tool.started").payload.locations[0].path,
    "docs/proof.md",
  );
  await client.close();
  assert.equal(client.remoteSessionDeleted, true);
});

test("AcpClient fails closed on protocol mismatch and unsafe tool kinds", async (t) => {
  const mismatch = new AcpClient({ adapter: adapter("--protocol-mismatch") });
  t.after(() => mismatch.close());
  await assert.rejects(mismatch.connect(), { code: "ACP_PROTOCOL_MISMATCH" });

  const unsafe = new AcpClient({ adapter: adapter("--unsafe") });
  t.after(() => unsafe.close());
  await unsafe.connect();
  await unsafe.createSession();
  await assert.rejects(
    unsafe.prompt("CONVERGE ASK GROUNDING\nUSER QUESTION\nWhy?"),
    { code: "ACP_UNSAFE_TOOL" },
  );

  const unsafeMode = new AcpClient({
    adapter: adapter("--no-safe-mode"),
  });
  t.after(() => unsafeMode.close());
  await unsafeMode.connect();
  await assert.rejects(unsafeMode.createSession(), {
    code: "ACP_SAFE_MODE_UNAVAILABLE",
  });
});

test("AcpClient normalizes ACP authentication-required failures", async (t) => {
  const client = new AcpClient({ adapter: adapter("--auth-required") });
  t.after(() => client.close());
  await client.connect();
  await client.createSession();
  await assert.rejects(
    client.prompt("CONVERGE ASK GROUNDING\nCURRENT USER QUESTION\nWhy?"),
    { code: "ACP_AUTH_REQUIRED" },
  );
});
