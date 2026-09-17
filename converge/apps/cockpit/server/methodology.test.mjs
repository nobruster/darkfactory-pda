import assert from "node:assert/strict";
import test from "node:test";

import {
  createMethodologyProvider,
  extractMethodologyManifest,
} from "./methodology.mjs";

function result(document, overrides = {}) {
  return {
    parsed: true,
    exitCode: 0,
    timedOut: false,
    document,
    ...overrides,
  };
}

function manifest() {
  return {
    schema_version: "1.0",
    tool: "cvg",
    version: "0.1.0",
    role: "referee",
    description: "Canonical Converge method.",
    contracts: { determinism: "read-only gates" },
    commands: [{ name: "capture", description: "Pass 0 gate." }],
  };
}

test("methodology provider validates, digests, and caches cvg agent-context", async () => {
  let calls = 0;
  const provider = createMethodologyProvider({
    runner: {
      async run(name) {
        calls += 1;
        assert.equal(name, "agentContext");
        return result(manifest());
      },
    },
  });
  const first = await provider();
  const second = await provider();
  assert.equal(first, second);
  assert.equal(first.document.tool, "cvg");
  assert.match(first.digest, /^[a-f0-9]{64}$/);
  assert.equal(calls, 1);
});

test("methodology extraction fails closed on timeout and malformed manifests", () => {
  assert.throws(
    () => extractMethodologyManifest(result(manifest(), { timedOut: true })),
    { code: "CLI_METHODOLOGY_TIMEOUT" },
  );
  assert.throws(
    () => extractMethodologyManifest(result({ ...manifest(), commands: [] })),
    { code: "CLI_METHODOLOGY_INVALID" },
  );
  assert.throws(
    () => extractMethodologyManifest(result({ ...manifest(), tool: "other" })),
    { code: "CLI_METHODOLOGY_INVALID" },
  );
});
