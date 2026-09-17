import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  chmod,
  cp,
  mkdir,
  mkdtemp,
  readFile,
  realpath,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import { createServer, request as httpRequest } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { createRequestHandler } from "./app.mjs";
import { createAgentRegistry } from "./acp/agent-registry.mjs";
import { ArtifactStore } from "./artifact-store.mjs";
import {
  resolveServerConfig,
  UNVERIFIED_CLAUDE_ACP_OVERRIDE,
} from "./config.mjs";
import { createCvgRunner } from "./cvg.mjs";
import {
  createWorkspaceSnapshotValidator,
  validateJsonSchema,
} from "./schema.mjs";
import { SnapshotService } from "./service.mjs";
import {
  buildWorkspaceSnapshot,
  extractSnapshotEnvelope,
} from "./snapshot.mjs";

const APP_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPOSITORY_ROOT = path.resolve(APP_ROOT, "../..");

async function withTempDirectory(t) {
  const directory = await mkdtemp(path.join(tmpdir(), "cvg-cockpit-test-"));
  t.after(() => rm(directory, { force: true, recursive: true }));
  return directory;
}

function sha256(contents) {
  return createHash("sha256").update(contents).digest("hex");
}

function minimalPdf(text) {
  const escaped = text.replaceAll("\\", "\\\\").replaceAll("(", "\\(").replaceAll(")", "\\)");
  const stream = `BT\n/F1 12 Tf\n72 100 Td\n(${escaped}) Tj\nET\n`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 360 144] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
    `<< /Length ${Buffer.byteLength(stream, "latin1")} >>\nstream\n${stream}endstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let document = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets[index + 1] = Buffer.byteLength(document, "latin1");
    document += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xrefOffset = Buffer.byteLength(document, "latin1");
  document += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  document += offsets
    .slice(1)
    .map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`)
    .join("");
  document += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  return Buffer.from(document, "latin1");
}

function artifactRef({
  id = "artifact-proof",
  artifactPath = "docs/proof.md",
  digest = sha256("proof"),
} = {}) {
  return {
    id,
    label: "Proof",
    path: artifactPath,
    kind: "artifact",
    sha256: digest,
    entity: { kind: "pass", id: "pass-0" },
    provenance: {
      sourceKind: "file",
      sourceRef: artifactPath,
      observedAt: "2026-08-03T12:00:00.000Z",
      truthClass: "canonical",
    },
  };
}

function workspaceSnapshot({
  snapshotId = "ws_1234567890abcdef",
  artifacts = [artifactRef()],
} = {}) {
  return {
    schemaVersion: "3.0",
    snapshotId,
    observedAt: "2026-08-03T12:00:00.000Z",
    source: "workspace",
    project: {},
    method: {},
    review: null,
    decomposition: { availability: "empty", swimlanes: [], legs: [], edges: [] },
    work: {},
    execution: {},
    receipts: [],
    health: [],
    signals: [],
    issues: [],
    authorization: {},
    artifacts,
  };
}

function cliEnvelope(snapshot, overrides = {}) {
  return {
    ok: true,
    command: "snapshot",
    token: null,
    verdict: null,
    exit_code: 0,
    changed: false,
    dry_run: false,
    data: { snapshot },
    error: null,
    warnings: [],
    meta: {
      schema_version: "1.0",
      tool: "cvg",
      cvg_version: "0.1.0",
    },
    ...overrides,
  };
}

function transportEnvelope(snapshot, {
  stale = false,
  servedAt = "2026-08-03T12:00:01.000Z",
  error,
} = {}) {
  return {
    snapshot,
    transport: {
      stale,
      servedAt,
      ...(error ? { error } : {}),
    },
  };
}

async function listen(t, handler) {
  const server = createServer(handler);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(
    () =>
      new Promise((resolve) => {
        server.closeAllConnections();
        server.close(resolve);
      }),
  );
  const address = server.address();
  return `http://127.0.0.1:${address.port}`;
}

async function getWithHost(origin, requestPath, host) {
  const target = new URL(origin);
  return new Promise((resolve, reject) => {
    const request = httpRequest(
      {
        hostname: target.hostname,
        port: target.port,
        path: requestPath,
        method: "GET",
        headers: { Host: host },
      },
      (response) => {
        const chunks = [];
        response.on("data", (chunk) => chunks.push(chunk));
        response.on("end", () => {
          resolve({
            status: response.statusCode,
            document: JSON.parse(Buffer.concat(chunks).toString("utf8")),
          });
        });
      },
    );
    request.on("error", reject);
    request.end();
  });
}

test("server config requires explicit roots and only binds Cockpit to loopback", async (t) => {
  await assert.rejects(
    resolveServerConfig({ env: {}, argv: [] }),
    /CVG_HOME and CVG_PROJECT_ROOT are required/,
  );

  const root = await withTempDirectory(t);
  const cvgHome = path.join(root, "converge");
  const projectRoot = path.join(root, "project");
  await mkdir(path.join(cvgHome, "bin"), { recursive: true });
  await mkdir(projectRoot);
  await writeFile(path.join(cvgHome, "bin", "cvg"), "#!/bin/sh\n");
  await chmod(path.join(cvgHome, "bin", "cvg"), 0o755);

  const config = await resolveServerConfig({
    env: { CVG_HOME: cvgHome, CVG_PROJECT_ROOT: projectRoot },
    argv: ["--port", "4321"],
  });
  assert.equal(config.cvgHome, await realpath(cvgHome));
  assert.equal(config.projectRoot, await realpath(projectRoot));
  assert.equal(config.host, "127.0.0.1");
  assert.equal(config.port, 4321);
  assert.equal(config.claudeAcpContextIsolation, "verified");
  assert.equal(config.claudeAcpOverrideSource, null);
  assert.equal(config.claudeAcpBlockedReason, null);

  await assert.rejects(
    resolveServerConfig({
      env: { CVG_HOME: cvgHome, CVG_PROJECT_ROOT: projectRoot },
      argv: ["--host", "0.0.0.0"],
    }),
    /Converge Cockpit bridge is local-only/,
  );
});

test("server config blocks CLI and environment Claude ACP overrides", async (t) => {
  const root = await withTempDirectory(t);
  const cvgHome = path.join(root, "converge");
  const projectRoot = path.join(root, "project");
  await mkdir(path.join(cvgHome, "bin"), { recursive: true });
  await mkdir(projectRoot);
  await writeFile(path.join(cvgHome, "bin", "cvg"), "#!/bin/sh\n");
  await chmod(path.join(cvgHome, "bin", "cvg"), 0o755);

  const environmentOverride = path.join(root, "environment-claude-acp");
  const cliOverride = path.join(root, "cli-claude-acp");
  await writeFile(environmentOverride, "#!/bin/sh\n");
  await writeFile(cliOverride, "#!/bin/sh\n");
  await chmod(environmentOverride, 0o755);
  await chmod(cliOverride, 0o755);
  const roots = { CVG_HOME: cvgHome, CVG_PROJECT_ROOT: projectRoot };

  const fromEnvironment = await resolveServerConfig({
    env: { ...roots, CVG_ACP_CLAUDE_BIN: environmentOverride },
    argv: [],
  });
  assert.equal(fromEnvironment.claudeAcpBin, environmentOverride);
  assert.equal(fromEnvironment.claudeAcpOverrideSource, "environment");
  assert.equal(fromEnvironment.claudeAcpContextIsolation, "unsupported");
  assert.equal(
    fromEnvironment.claudeAcpBlockedReason,
    UNVERIFIED_CLAUDE_ACP_OVERRIDE,
  );

  const fromCli = await resolveServerConfig({
    env: { ...roots, CVG_ACP_CLAUDE_BIN: environmentOverride },
    argv: ["--claude-acp-bin", cliOverride],
  });
  assert.equal(fromCli.claudeAcpBin, cliOverride);
  assert.equal(fromCli.claudeAcpOverrideSource, "cli");
  assert.equal(fromCli.claudeAcpContextIsolation, "unsupported");
  assert.equal(fromCli.claudeAcpBlockedReason, UNVERIFIED_CLAUDE_ACP_OVERRIDE);

  for (const config of [fromEnvironment, fromCli]) {
    const registry = createAgentRegistry({
      projectRoot: config.projectRoot,
      adapters: [
        {
          id: "claude",
          label: "Claude Agent",
          executable: config.claudeAcpBin,
          args: [],
          environment: {},
          requiredMode: "plan",
          disableBuiltInTools: true,
          contextIsolation: config.claudeAcpContextIsolation,
          blockedReason: config.claudeAcpBlockedReason,
        },
      ],
    });
    const [agent] = await registry.list();
    assert.equal(agent.availability, "blocked");
    assert.equal(agent.connection, "not_started");
    assert.equal(agent.reason, UNVERIFIED_CLAUDE_ACP_OVERRIDE);
  }
});

test("runner invokes only declared read-only cvg commands with no shell or credential forwarding", async () => {
  const invocations = [];
  const snapshot = workspaceSnapshot();
  const execFileImpl = (file, args, options, callback) => {
    invocations.push({ file, args, options });
    callback(
      null,
      JSON.stringify(
        args[0] === "agent-context"
          ? {
              schema_version: "1.0",
              tool: "cvg",
              version: "0.1.0",
              role: "referee",
              contracts: {},
              commands: [{ name: "capture", description: "Pass 0 gate" }],
            }
          : cliEnvelope(snapshot),
      ),
      "",
    );
  };
  const config = {
    cvgBin: "/tool/bin/cvg",
    cvgHome: "/tool",
    projectRoot: "/workspace",
  };
  const runner = createCvgRunner({
    config,
    execFileImpl,
    baseEnvironment: {
      PATH: "/usr/bin",
      HOME: "/home/person",
      GITHUB_TOKEN: "do-not-forward",
      OPENAI_API_KEY: "do-not-forward",
    },
  });

  const result = await runner.run("snapshot");
  const methodology = await runner.run("agentContext");
  assert.deepEqual(invocations.map((invocation) => invocation.args), [
    ["snapshot", "--json"],
    ["agent-context"],
  ]);
  const invocation = invocations[0];
  assert.equal(invocation.file, "/tool/bin/cvg");
  assert.equal(invocation.options.cwd, "/workspace");
  assert.equal(invocation.options.shell, undefined);
  assert.equal(invocation.options.env.CVG_HOME, "/tool");
  assert.equal(invocation.options.env.CVG_PROJECT_ROOT, "/workspace");
  assert.equal(invocation.options.env.GITHUB_TOKEN, undefined);
  assert.equal(invocation.options.env.OPENAI_API_KEY, undefined);
  assert.deepEqual(result.document.data.snapshot, snapshot);
  assert.equal(methodology.document.tool, "cvg");

  await assert.rejects(runner.run("next"), /undeclared read-only/);
  await assert.rejects(runner.run("snapshot --json; rm -rf project"), /undeclared read-only/);
});

test("snapshot transport accepts only a successful cvg envelope and preserves CLI semantics", async () => {
  const snapshot = workspaceSnapshot();
  const allowed = [];
  const artifactStore = {
    setAllowedArtifacts(records, snapshotId) {
      allowed.push({ records, snapshotId });
    },
  };
  const runner = {
    async run(name) {
      assert.equal(name, "snapshot");
      return {
        parsed: true,
        exitCode: 0,
        timedOut: false,
        document: cliEnvelope(snapshot),
      };
    },
  };

  const received = await buildWorkspaceSnapshot({
    runner,
    artifactStore,
    validateSnapshot(candidate) {
      assert.equal(candidate, snapshot);
    },
  });
  assert.equal(received, snapshot);
  assert.deepEqual(allowed, [
    { records: snapshot.artifacts, snapshotId: snapshot.snapshotId },
  ]);
  assert.equal(Object.hasOwn(received, "transport"), false);

  assert.throws(
    () => extractSnapshotEnvelope({
      parsed: true,
      exitCode: 0,
      document: snapshot,
    }),
    { code: "CLI_SNAPSHOT_REJECTED" },
  );
  assert.throws(
    () => extractSnapshotEnvelope({
      parsed: true,
      exitCode: 1,
      document: cliEnvelope(snapshot, { ok: false, exit_code: 1 }),
    }),
    { code: "CLI_SNAPSHOT_REJECTED" },
  );
  assert.throws(
    () => extractSnapshotEnvelope({
      parsed: false,
      exitCode: 0,
      document: null,
    }),
    { code: "CLI_SNAPSHOT_INVALID" },
  );
  assert.throws(
    () => extractSnapshotEnvelope({
      parsed: false,
      exitCode: 2,
      document: null,
      timedOut: true,
    }),
    { code: "CLI_SNAPSHOT_TIMEOUT" },
  );
});

test("WorkspaceSnapshot validator rejects documents outside schema version 3.0", async (t) => {
  const root = await withTempDirectory(t);
  const schemaPath = path.join(root, "workspace-snapshot.schema.json");
  await writeFile(
    schemaPath,
    JSON.stringify({
      type: "object",
      required: ["schemaVersion", "snapshotId", "observedAt", "artifacts"],
      properties: {
        schemaVersion: { const: "3.0" },
        snapshotId: { type: "string", minLength: 12 },
        observedAt: { type: "string", format: "date-time" },
        artifacts: {
          type: "array",
          items: { $ref: "#/$defs/artifact" },
        },
      },
      additionalProperties: true,
      $defs: {
        artifact: {
          type: "object",
          required: ["id", "path", "sha256"],
          properties: {
            id: { type: "string" },
            path: { type: "string" },
            sha256: { type: "string", pattern: "^[a-f0-9]{64}$" },
          },
          additionalProperties: true,
        },
      },
    }),
  );
  const validate = await createWorkspaceSnapshotValidator({
    config: { cvgHome: root },
    schemaPath,
  });

  assert.equal(validate(workspaceSnapshot()).schemaVersion, "3.0");
  assert.throws(
    () => validate({ ...workspaceSnapshot(), schemaVersion: "1.0" }),
    { code: "SNAPSHOT_SCHEMA_INVALID" },
  );
  assert.throws(
    () => validate({ ...workspaceSnapshot(), artifacts: undefined }),
    { code: "SNAPSHOT_SCHEMA_INVALID" },
  );

  assert.deepEqual(
    validateJsonSchema(
      { state: "ok", extra: true },
      {
        type: "object",
        required: ["state"],
        properties: { state: { enum: ["ok"] } },
        additionalProperties: false,
      },
    ),
    ["$.extra is not allowed"],
  );
});

test("real CLI snapshot satisfies the complete WorkspaceSnapshot 3.0 bridge contract", async () => {
  const config = {
    cvgBin: path.join(REPOSITORY_ROOT, "bin", "cvg"),
    cvgHome: REPOSITORY_ROOT,
    projectRoot: path.join(APP_ROOT, "e2e", "fixtures", "workspace"),
  };
  const runner = createCvgRunner({ config });
  const validateSnapshot = await createWorkspaceSnapshotValidator({ config });
  const allowed = [];

  const snapshot = await buildWorkspaceSnapshot({
    runner,
    validateSnapshot,
    artifactStore: {
      setAllowedArtifacts(records, snapshotId) {
        allowed.push({ records, snapshotId });
      },
    },
  });

  assert.equal(snapshot.schemaVersion, "3.0");
  assert.equal(snapshot.source, "workspace");
  assert.match(snapshot.snapshotId, /^ws3_[0-9a-f]{32}$/);
  assert.equal(snapshot.method.activePassId, "pass-0");
  assert.equal(snapshot.work.availability, "empty");
  assert.equal(snapshot.execution.availability, "empty");
  assert.equal(snapshot.receipts.availability, "empty");
  assert.deepEqual(allowed, [
    {
      records: snapshot.artifacts,
      snapshotId: snapshot.snapshotId,
    },
  ]);
  assert.equal(JSON.stringify(snapshot).includes('"position"'), false);

  const invalidKind = structuredClone(snapshot);
  invalidKind.issues.push({
    id: "issue_11111111111111111111",
    code: "INVALID_ENTITY_KIND",
    severity: "warning",
    domain: "work",
    message: "test",
    entity: { kind: "invented", id: "pass-0" },
    artifactIds: [],
  });
  assert.throws(() => validateSnapshot(invalidKind), {
    code: "SNAPSHOT_SCHEMA_INVALID",
  });

  const danglingReference = structuredClone(snapshot);
  danglingReference.issues.push({
    id: "issue_22222222222222222222",
    code: "DANGLING_ENTITY_REFERENCE",
    severity: "warning",
    domain: "work",
    message: "test",
    entity: { kind: "task", id: "missing-task" },
    artifactIds: [],
  });
  assert.throws(() => validateSnapshot(danglingReference), {
    code: "SNAPSHOT_SCHEMA_INVALID",
  });

  const missingDependencyEdge = structuredClone(snapshot);
  missingDependencyEdge.decomposition.edges = [];
  assert.throws(() => validateSnapshot(missingDependencyEdge), {
    code: "SNAPSHOT_SCHEMA_INVALID",
  });

  const duplicateDependencyEdge = structuredClone(snapshot);
  duplicateDependencyEdge.decomposition.edges.push({
    ...duplicateDependencyEdge.decomposition.edges[0],
    id: "decompedge_11111111111111111111",
  });
  assert.throws(() => validateSnapshot(duplicateDependencyEdge), {
    code: "SNAPSHOT_SCHEMA_INVALID",
  });

  const cyclicDependency = structuredClone(snapshot);
  const cyclicLeg = cyclicDependency.decomposition.legs[0];
  cyclicLeg.dependsOn.push(cyclicLeg.id);
  cyclicDependency.decomposition.edges.push({
    id: "decompedge_ffffffffffffffffffff",
    source: cyclicLeg.id,
    target: cyclicLeg.id,
    kind: "depends_on",
    artifactIds: cyclicLeg.artifactIds,
  });
  assert.throws(() => validateSnapshot(cyclicDependency), {
    code: "SNAPSHOT_SCHEMA_INVALID",
  });

  const danglingArtifact = structuredClone(snapshot);
  danglingArtifact.decomposition.swimlanes[0].artifactIds = [
    "artifact_11111111111111111111",
  ];
  assert.throws(() => validateSnapshot(danglingArtifact), {
    code: "SNAPSHOT_SCHEMA_INVALID",
  });
});

test("invalid decomposition stays bridge-valid without dangling typed entities", async (t) => {
  const tempRoot = await withTempDirectory(t);
  const projectRoot = path.join(tempRoot, "workspace");
  await cp(
    path.join(APP_ROOT, "e2e", "fixtures", "workspace"),
    projectRoot,
    { recursive: true },
  );
  const legPath = path.join(
    projectRoot,
    "cvg",
    "swimlanes",
    "checkout",
    "leg-02-stripe.md",
  );
  const leg = await readFile(legPath, "utf8");
  await writeFile(
    legPath,
    leg.replace(
      "depends_on: [swimlane-checkout-leg-01]",
      "depends_on: [swimlane-missing-leg-09]",
    ),
  );
  const config = {
    cvgBin: path.join(REPOSITORY_ROOT, "bin", "cvg"),
    cvgHome: REPOSITORY_ROOT,
    projectRoot,
  };
  const snapshot = await buildWorkspaceSnapshot({
    runner: createCvgRunner({ config }),
    validateSnapshot: await createWorkspaceSnapshotValidator({ config }),
    artifactStore: { setAllowedArtifacts() {} },
  });

  assert.deepEqual(snapshot.decomposition, {
    availability: "unavailable",
    swimlanes: [],
    legs: [],
    edges: [],
  });
  assert.ok(
    snapshot.issues.some(
      (issue) => issue.code === "DECOMPOSITION_DEPENDENCY_DANGLING",
    ),
  );
  assert.equal(
    [...snapshot.issues, ...snapshot.artifacts].some((record) =>
      ["swimlane", "leg"].includes(record.entity?.kind),
    ),
    false,
  );
});

test("SnapshotService serves immutable last-good data with stale transport metadata", async () => {
  const first = workspaceSnapshot({ snapshotId: "ws_first_snapshot_123" });
  const second = workspaceSnapshot({ snapshotId: "ws_second_snapshot_45" });
  let clock = Date.parse("2026-08-03T12:00:00.000Z");
  let call = 0;
  const service = new SnapshotService({
    cacheMs: 1_000,
    now: () => clock,
    async build() {
      call += 1;
      if (call === 1) return first;
      if (call === 2) {
        const error = new Error("contains private diagnostic details");
        error.code = "SNAPSHOT_SCHEMA_INVALID";
        throw error;
      }
      return second;
    },
  });

  const live = await service.getSnapshot();
  assert.equal(live.snapshot, first);
  assert.deepEqual(live.transport, {
    stale: false,
    servedAt: "2026-08-03T12:00:00.000Z",
  });

  clock += 2_000;
  const stale = await service.getSnapshot({ fresh: true });
  assert.equal(stale.snapshot, first);
  assert.equal(stale.snapshot.snapshotId, live.snapshot.snapshotId);
  assert.equal(Object.hasOwn(stale.snapshot, "transport"), false);
  assert.deepEqual(stale.transport, {
    stale: true,
    servedAt: "2026-08-03T12:00:02.000Z",
    error: {
      code: "SNAPSHOT_SCHEMA_INVALID",
      message: "The CLI snapshot does not match WorkspaceSnapshot 3.0.",
    },
  });
  assert.equal(JSON.stringify(stale).includes("private diagnostic"), false);

  clock += 2_000;
  const recovered = await service.getSnapshot({ fresh: true });
  assert.equal(recovered.snapshot, second);
  assert.equal(recovered.transport.stale, false);

  const unavailable = new SnapshotService({
    async build() {
      throw new Error("no snapshot");
    },
  });
  await assert.rejects(unavailable.getSnapshot(), /no snapshot/);
});

test("artifact allowlist is snapshot+sha bound and blocks traversal, symlinks, binary data, and credentials", async (t) => {
  const projectRoot = await withTempDirectory(t);
  const outsideRoot = await withTempDirectory(t);
  await mkdir(path.join(projectRoot, "docs"), { recursive: true });
  const safeContents = [
    "# Evidence",
    "API_KEY=super-secret-value",
    "Authorization: Bearer bearer-secret-value",
    "github_pat_abcdefghijklmnopqrstuvwxyz0123456789",
  ].join("\n");
  const largeContents = "x".repeat(64);
  const pdfContents = minimalPdf("PDF proof API_KEY=super-secret-value");
  await writeFile(path.join(projectRoot, "docs", "safe.md"), safeContents);
  await writeFile(path.join(projectRoot, "docs", "large.md"), largeContents);
  await writeFile(path.join(projectRoot, "docs", "safe.pdf"), pdfContents);
  await writeFile(path.join(projectRoot, "docs", "invalid.pdf"), "%PDF-not-valid");
  await writeFile(path.join(projectRoot, "docs", "binary.log"), Buffer.from([0, 1, 2]));
  await writeFile(
    path.join(projectRoot, "docs", "invalid-utf8.log"),
    Buffer.from([0xff, 0xfe, 0xfd]),
  );
  await writeFile(path.join(outsideRoot, "outside.md"), "not allowed");
  await symlink(
    path.join(outsideRoot, "outside.md"),
    path.join(projectRoot, "docs", "escape.md"),
  );

  const store = new ArtifactStore({ projectRoot, maxBytes: 32 });
  const records = [
    artifactRef({
      id: "safe",
      artifactPath: "docs/safe.md",
      digest: sha256(safeContents),
    }),
    artifactRef({
      id: "large",
      artifactPath: "docs/large.md",
      digest: sha256(largeContents),
    }),
    artifactRef({
      id: "pdf",
      artifactPath: "docs/safe.pdf",
      digest: sha256(pdfContents),
    }),
    artifactRef({
      id: "invalid-pdf",
      artifactPath: "docs/invalid.pdf",
      digest: sha256("%PDF-not-valid"),
    }),
    artifactRef({
      id: "binary",
      artifactPath: "docs/binary.log",
      digest: sha256(Buffer.from([0, 1, 2])),
    }),
    artifactRef({
      id: "invalid-utf8",
      artifactPath: "docs/invalid-utf8.log",
      digest: sha256(Buffer.from([0xff, 0xfe, 0xfd])),
    }),
    artifactRef({
      id: "escape",
      artifactPath: "docs/escape.md",
      digest: sha256("not allowed"),
    }),
  ];
  store.setAllowedArtifacts(records, "ws_snapshot_one");

  const safe = await store.read("docs/safe.md", {
    snapshotId: "ws_snapshot_one",
    expectedSha256: sha256(safeContents),
  });
  assert.equal(safe.id, "safe");
  assert.equal(safe.content.includes("super-secret-value"), false);
  assert.equal(safe.content.includes("[REDACTED]"), true);
  assert.equal(safe.format, "markdown");
  assert.equal(safe.redacted, true);
  assert.equal(safe.sourceBytes, Buffer.byteLength(safeContents));
  assert.equal(safe.sha256, sha256(safeContents));
  assert.equal(safe.snapshotId, "ws_snapshot_one");
  assert.deepEqual(safe.entity, { kind: "pass", id: "pass-0" });
  assert.equal(safe.provenance.truthClass, "canonical");

  const large = await store.read("docs/large.md", {
    snapshotId: "ws_snapshot_one",
    expectedSha256: sha256(largeContents),
  });
  assert.equal(large.truncated, true);
  assert.equal(Buffer.byteLength(large.content) <= 32, true);

  const pdf = await store.read("docs/safe.pdf", {
    snapshotId: "ws_snapshot_one",
    expectedSha256: sha256(pdfContents),
  });
  assert.equal(pdf.format, "pdf-text");
  assert.equal(pdf.pageCount, 1);
  assert.equal(pdf.pages.length, 1);
  assert.equal(pdf.pages[0].text.includes("super-secret-value"), false);
  assert.equal(pdf.pages[0].text.includes("[REDACTED]"), true);
  assert.equal(pdf.redacted, true);
  assert.equal(pdf.sha256, sha256(pdfContents));
  assert.equal(Object.hasOwn(pdf, "content"), false);

  const sizeLimitedStore = new ArtifactStore({
    projectRoot,
    maxPdfBytes: pdfContents.byteLength - 1,
  });
  sizeLimitedStore.setAllowedArtifacts(
    [
      artifactRef({
        id: "pdf-size-limited",
        artifactPath: "docs/safe.pdf",
        digest: sha256(pdfContents),
      }),
    ],
    "ws_pdf_size_limit",
  );
  await assert.rejects(
    sizeLimitedStore.read("docs/safe.pdf", {
      snapshotId: "ws_pdf_size_limit",
      expectedSha256: sha256(pdfContents),
    }),
    { code: "ARTIFACT_TOO_LARGE" },
  );

  await assert.rejects(
    store.read("docs/invalid.pdf", {
      snapshotId: "ws_snapshot_one",
      expectedSha256: sha256("%PDF-not-valid"),
    }),
    { code: "PDF_PREVIEW_INVALID" },
  );

  await assert.rejects(
    store.read("../outside.md", {
      snapshotId: "ws_snapshot_one",
      expectedSha256: sha256("not allowed"),
    }),
    { code: "ARTIFACT_NOT_ALLOWED" },
  );
  await assert.rejects(
    store.read("docs/escape.md", {
      snapshotId: "ws_snapshot_one",
      expectedSha256: sha256("not allowed"),
    }),
    { code: "ARTIFACT_NOT_ALLOWED" },
  );
  await assert.rejects(
    store.read("docs/not-allowlisted.md", {
      snapshotId: "ws_snapshot_one",
      expectedSha256: sha256("missing"),
    }),
    { code: "ARTIFACT_NOT_ALLOWED" },
  );
  await assert.rejects(
    store.read("docs/safe.md", {
      snapshotId: "ws_old_snapshot",
      expectedSha256: sha256(safeContents),
    }),
    { code: "SNAPSHOT_STALE" },
  );
  await assert.rejects(
    store.read("docs/safe.md", { snapshotId: "ws_snapshot_one" }),
    { code: "EVIDENCE_HASH_REQUIRED" },
  );
  await assert.rejects(
    store.read("docs/safe.md", {
      snapshotId: "ws_snapshot_one",
      expectedSha256: sha256("different"),
    }),
    { code: "EVIDENCE_STALE" },
  );
  await assert.rejects(
    store.read("docs/binary.log", {
      snapshotId: "ws_snapshot_one",
      expectedSha256: sha256(Buffer.from([0, 1, 2])),
    }),
    { code: "ARTIFACT_NOT_ALLOWED" },
  );
  await assert.rejects(
    store.read("docs/invalid-utf8.log", {
      snapshotId: "ws_snapshot_one",
      expectedSha256: sha256(Buffer.from([0xff, 0xfe, 0xfd])),
    }),
    { code: "ARTIFACT_NOT_ALLOWED" },
  );

  await writeFile(path.join(projectRoot, "docs", "safe.md"), "changed after capture");
  await assert.rejects(
    store.read("docs/safe.md", {
      snapshotId: "ws_snapshot_one",
      expectedSha256: sha256(safeContents),
    }),
    { code: "EVIDENCE_STALE" },
  );

  assert.throws(
    () =>
      store.setAllowedArtifacts(
        [
          artifactRef({ artifactPath: "docs/same.md" }),
          artifactRef({ id: "duplicate", artifactPath: "docs/same.md" }),
        ],
        "ws_invalid",
      ),
    { code: "SNAPSHOT_SCHEMA_INVALID" },
  );
});

test("artifact endpoint rejects missing hashes and stale snapshots before reading", async (t) => {
  const snapshot = workspaceSnapshot();
  const service = {
    async getSnapshot() {
      return transportEnvelope(snapshot);
    },
  };
  let artifactReads = 0;
  let artifactFailure = null;
  const artifactStore = {
    async read() {
      artifactReads += 1;
      if (artifactFailure) {
        const error = new Error("private parser detail");
        error.code = artifactFailure;
        throw error;
      }
      return {};
    },
  };
  const origin = await listen(
    t,
    createRequestHandler({
      config: {
        projectRoot: "/workspace/use-case",
        serveDist: false,
        distRoot: "/unused",
      },
      service,
      artifactStore,
    }),
  );

  const missingHash = await fetch(
    `${origin}/api/artifact?path=docs%2Fproof.md&snapshotId=${snapshot.snapshotId}`,
  );
  assert.equal(missingHash.status, 400);
  assert.equal(
    (await missingHash.json()).error.code,
    "ARTIFACT_SHA256_REQUIRED",
  );

  const stale = await fetch(
    `${origin}/api/artifact?path=docs%2Fproof.md&snapshotId=ws_old&sha256=${snapshot.artifacts[0].sha256}`,
  );
  assert.equal(stale.status, 409);
  assert.equal((await stale.json()).error.code, "SNAPSHOT_STALE");
  assert.equal(artifactReads, 0);

  const artifactUrl =
    `${origin}/api/artifact?path=docs%2Fproof.md` +
    `&snapshotId=${snapshot.snapshotId}&sha256=${snapshot.artifacts[0].sha256}`;
  artifactFailure = "ARTIFACT_TOO_LARGE";
  const tooLarge = await fetch(artifactUrl);
  assert.equal(tooLarge.status, 413);
  assert.equal((await tooLarge.json()).error.code, "ARTIFACT_TOO_LARGE");

  artifactFailure = "PDF_PREVIEW_INVALID";
  const invalidPdf = await fetch(artifactUrl);
  assert.equal(invalidPdf.status, 422);
  const invalidPdfDocument = await invalidPdf.json();
  assert.equal(invalidPdfDocument.error.code, "PDF_PREVIEW_INVALID");
  assert.equal(JSON.stringify(invalidPdfDocument).includes("private parser"), false);
});

test("artifact endpoint reports an unavailable live snapshot before reading", async (t) => {
  const snapshot = workspaceSnapshot();
  let artifactReads = 0;
  let snapshotState = "unavailable";
  const origin = await listen(
    t,
    createRequestHandler({
      config: {
        projectRoot: "/workspace/use-case",
        serveDist: false,
        distRoot: "/unused",
      },
      service: {
        async getSnapshot() {
          if (snapshotState === "unavailable") {
            throw new Error("private snapshot failure");
          }
          return transportEnvelope({ ...snapshot, source: "fixture" });
        },
      },
      artifactStore: {
        async read() {
          artifactReads += 1;
          return {};
        },
      },
    }),
  );

  const response = await fetch(
    `${origin}/api/artifact?path=docs%2Fproof.md` +
      `&snapshotId=${snapshot.snapshotId}&sha256=${snapshot.artifacts[0].sha256}`,
  );
  assert.equal(response.status, 503);
  const document = await response.json();
  assert.equal(document.error.code, "SNAPSHOT_UNAVAILABLE");
  assert.equal(JSON.stringify(document).includes("private snapshot"), false);

  snapshotState = "fixture";
  const fixtureResponse = await fetch(
    `${origin}/api/artifact?path=docs%2Fproof.md` +
      `&snapshotId=${snapshot.snapshotId}&sha256=${snapshot.artifacts[0].sha256}`,
  );
  assert.equal(fixtureResponse.status, 503);
  assert.equal(
    (await fixtureResponse.json()).error.code,
    "SNAPSHOT_UNAVAILABLE",
  );
  assert.equal(artifactReads, 0);
});

test("serve-dist mode serves the Cockpit client and SPA routes", async (t) => {
  const distRoot = await withTempDirectory(t);
  await mkdir(path.join(distRoot, "assets"));
  await writeFile(
    path.join(distRoot, "index.html"),
    "<!doctype html><title>Converge Cockpit</title>",
  );
  await writeFile(path.join(distRoot, "assets", "app.js"), "export {};\n");

  const origin = await listen(
    t,
    createRequestHandler({
      config: {
        projectRoot: "/workspace/use-case",
        serveDist: true,
        distRoot,
      },
      service: { async getSnapshot() {} },
      artifactStore: { async read() {} },
    }),
  );

  const rootResponse = await fetch(`${origin}/`);
  assert.equal(rootResponse.status, 200);
  assert.match(await rootResponse.text(), /Converge Cockpit/);

  const routeResponse = await fetch(`${origin}/passes/4`);
  assert.equal(routeResponse.status, 200);
  assert.match(await routeResponse.text(), /Converge Cockpit/);

  const assetResponse = await fetch(`${origin}/assets/app.js`);
  assert.equal(assetResponse.status, 200);
  assert.equal(
    assetResponse.headers.get("content-type"),
    "text/javascript; charset=utf-8",
  );
});

test("HTTP API exposes GET-only health, snapshot, events, and snapshot-bound artifacts", async (t) => {
  const snapshot = workspaceSnapshot();
  const envelope = transportEnvelope(snapshot);
  const service = {
    async getSnapshot() {
      return envelope;
    },
  };
  const artifactStore = {
    async read(requestedPath, { snapshotId, expectedSha256 }) {
      assert.equal(requestedPath, "docs/proof.md");
      assert.equal(snapshotId, snapshot.snapshotId);
      assert.equal(expectedSha256, snapshot.artifacts[0].sha256);
      return {
        ...snapshot.artifacts[0],
        content: "proof",
        truncated: false,
        snapshotId,
      };
    },
  };
  const origin = await listen(
    t,
    createRequestHandler({
      config: {
        projectRoot: "/workspace/use-case",
        serveDist: false,
        distRoot: "/does/not/matter",
      },
      service,
      artifactStore,
      pollMs: 20,
    }),
  );

  const health = await fetch(`${origin}/api/health`);
  assert.equal(health.status, 200);
  const healthDocument = await health.json();
  assert.equal(healthDocument.service, "converge-cockpit");
  assert.equal(healthDocument.mode, "read-only");

  const rebound = await getWithHost(
    origin,
    "/api/snapshot",
    "cockpit.attacker.example",
  );
  assert.equal(rebound.status, 403);
  assert.equal(rebound.document.error.code, "HOST_NOT_ALLOWED");

  for (const method of ["POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const mutation = await fetch(`${origin}/api/snapshot`, { method });
    assert.equal(mutation.status, 405);
    if (method !== "HEAD") {
      assert.equal((await mutation.json()).error.code, "METHOD_NOT_ALLOWED");
    }
    assert.equal(mutation.headers.get("allow"), "GET");
  }

  const snapshotResponse = await fetch(`${origin}/api/snapshot`);
  assert.deepEqual(await snapshotResponse.json(), envelope);

  const artifact = await fetch(
    `${origin}/api/artifact?path=${encodeURIComponent("docs/proof.md")}` +
      `&snapshotId=${snapshot.snapshotId}&sha256=${snapshot.artifacts[0].sha256}`,
  );
  assert.equal(artifact.status, 200);
  const artifactDocument = await artifact.json();
  assert.equal(artifactDocument.content, "proof");
  assert.equal(artifactDocument.snapshotId, snapshot.snapshotId);

  const unknown = await fetch(`${origin}/api/command`);
  assert.equal(unknown.status, 404);
});

test("SSE emits semantic changes and stale transport transitions", async (t) => {
  const first = workspaceSnapshot({ snapshotId: "ws_first_snapshot_123" });
  const second = workspaceSnapshot({ snapshotId: "ws_second_snapshot_45" });
  let freshCalls = 0;
  const service = {
    async getSnapshot({ fresh = false } = {}) {
      if (!fresh) {
        return transportEnvelope(first);
      }
      freshCalls += 1;
      if (freshCalls < 3) {
        return transportEnvelope(first, {
          stale: freshCalls === 2,
          error:
            freshCalls === 2
              ? { code: "SNAPSHOT_REFRESH_FAILED", message: "stale" }
              : undefined,
        });
      }
      return transportEnvelope(second);
    },
  };
  const origin = await listen(
    t,
    createRequestHandler({
      config: {
        projectRoot: "/workspace/use-case",
        serveDist: false,
        distRoot: "/unused",
      },
      service,
      artifactStore: { async read() {} },
      pollMs: 10,
    }),
  );

  const controller = new AbortController();
  const events = await fetch(`${origin}/api/events`, {
    signal: controller.signal,
  });
  assert.equal(
    events.headers.get("content-type"),
    "text/event-stream; charset=utf-8",
  );
  const reader = events.body.getReader();
  const decoder = new TextDecoder();
  let eventText = "";
  while (!eventText.includes(`id: ${second.snapshotId}`)) {
    const { value, done } = await reader.read();
    if (done) break;
    eventText += decoder.decode(value, { stream: true });
  }
  controller.abort();

  assert.equal(
    eventText.match(/^event: snapshot$/gm)?.length,
    3,
    eventText,
  );
  assert.equal(
    eventText.match(new RegExp(`^id: ${first.snapshotId}$`, "gm"))?.length,
    2,
    eventText,
  );
  assert.match(eventText, new RegExp(`id: ${second.snapshotId}`));
  assert.match(eventText, /"stale":true/);
});
