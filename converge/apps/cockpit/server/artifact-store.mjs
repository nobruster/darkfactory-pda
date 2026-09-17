import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { lstat, realpath, stat } from "node:fs/promises";
import path from "node:path";

import { extractPdfText } from "./pdf-text.mjs";
import { redactSensitiveTextWithReport } from "./security.mjs";

const DEFAULT_MAX_BYTES = 256 * 1024;
const DEFAULT_MAX_PDF_BYTES = 16 * 1024 * 1024;
const DEFAULT_MAX_PDF_PAGES = 100;
const DISALLOWED_TEXT_CONTROLS = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/;

function artifactFormat(relativePath) {
  const extension = path.posix.extname(relativePath).toLowerCase();
  if (extension === ".md" || extension === ".markdown") return "markdown";
  if (extension === ".pdf") return "pdf-text";
  return "text";
}

function normalizeRequestedPath(requestedPath) {
  if (
    typeof requestedPath !== "string" ||
    requestedPath.length === 0 ||
    requestedPath.includes("\0") ||
    requestedPath.includes("\\") ||
    path.posix.isAbsolute(requestedPath)
  ) {
    return null;
  }

  const normalized = path.posix.normalize(requestedPath);
  if (
    normalized !== requestedPath ||
    normalized === "." ||
    normalized === ".." ||
    normalized.startsWith("../")
  ) {
    return null;
  }
  return normalized;
}

function decodeTextPreview(buffer, { truncated = false } = {}) {
  const attempts = truncated ? [0, 1, 2, 3] : [0];
  for (const trim of attempts) {
    try {
      const candidate = trim === 0 ? buffer : buffer.subarray(0, -trim);
      const text = new TextDecoder("utf-8", { fatal: true }).decode(candidate);
      if (!DISALLOWED_TEXT_CONTROLS.test(text)) return text;
      break;
    } catch {
      // A bounded preview can end inside one UTF-8 code point; try its shorter
      // prefix only when the source itself was truncated.
    }
  }
  const error = new Error("binary-looking artifacts are not exposed by the bridge");
  error.code = "ARTIFACT_NOT_ALLOWED";
  throw error;
}

export class ArtifactStore {
  constructor({
    projectRoot,
    maxBytes = DEFAULT_MAX_BYTES,
    maxPdfBytes = DEFAULT_MAX_PDF_BYTES,
    maxPdfPages = DEFAULT_MAX_PDF_PAGES,
    maxPdfTextBytes = maxBytes,
  }) {
    this.projectRoot = projectRoot;
    this.maxBytes = maxBytes;
    this.maxPdfBytes = maxPdfBytes;
    this.maxPdfPages = maxPdfPages;
    this.maxPdfTextBytes = maxPdfTextBytes;
    this.allowed = new Map();
    this.snapshotId = null;
    this.projectRealPath = null;
  }

  setAllowedArtifacts(records, snapshotId) {
    if (!Array.isArray(records) || typeof snapshotId !== "string") {
      const error = new Error("snapshot artifact references are malformed");
      error.code = "SNAPSHOT_SCHEMA_INVALID";
      throw error;
    }
    const nextAllowed = new Map();
    for (const record of records) {
      const relativePath = normalizeRequestedPath(record?.path);
      if (
        !relativePath ||
        typeof record?.id !== "string" ||
        typeof record?.label !== "string" ||
        typeof record?.kind !== "string" ||
        typeof record?.sha256 !== "string" ||
        !/^[a-f0-9]{64}$/i.test(record.sha256) ||
        typeof record?.provenance !== "object" ||
        record.provenance === null ||
        nextAllowed.has(relativePath)
      ) {
        const error = new Error(
          "snapshot contains an unsafe or duplicate artifact reference",
        );
        error.code = "SNAPSHOT_SCHEMA_INVALID";
        throw error;
      }
      nextAllowed.set(relativePath, {
        id: record.id,
        label: record.label,
        kind: record.kind,
        sha256: record.sha256.toLowerCase(),
        ...(record.entity ? { entity: record.entity } : {}),
        provenance: record.provenance,
      });
    }
    this.allowed = nextAllowed;
    this.snapshotId = snapshotId;
  }

  async read(requestedPath, { snapshotId, expectedSha256 } = {}) {
    const relativePath = normalizeRequestedPath(requestedPath);
    const metadata = relativePath ? this.allowed.get(relativePath) : null;
    if (!relativePath || !metadata) {
      const error = new Error("artifact is not in the workspace evidence allowlist");
      error.code = "ARTIFACT_NOT_ALLOWED";
      throw error;
    }
    if (!snapshotId || snapshotId !== this.snapshotId) {
      const error = new Error(
        "artifact request is not bound to the current workspace snapshot",
      );
      error.code = "SNAPSHOT_STALE";
      throw error;
    }
    if (typeof expectedSha256 !== "string") {
      const error = new Error(
        "artifact request is missing the captured evidence hash",
      );
      error.code = "EVIDENCE_HASH_REQUIRED";
      throw error;
    }
    if (expectedSha256.toLowerCase() !== metadata.sha256) {
      const error = new Error(
        "artifact request hash does not match the captured evidence reference",
      );
      error.code = "EVIDENCE_STALE";
      throw error;
    }

    const projectRealPath =
      this.projectRealPath ?? (this.projectRealPath = await realpath(this.projectRoot));
    const absolutePath = path.resolve(projectRealPath, relativePath);
    const unresolvedInfo = await lstat(absolutePath);
    if (unresolvedInfo.isSymbolicLink()) {
      const error = new Error("symbolic-link artifacts are not exposed");
      error.code = "ARTIFACT_NOT_ALLOWED";
      throw error;
    }
    const resolvedPath = await realpath(absolutePath);
    if (
      resolvedPath !== projectRealPath &&
      !resolvedPath.startsWith(`${projectRealPath}${path.sep}`)
    ) {
      const error = new Error("artifact resolves outside the observed workspace");
      error.code = "ARTIFACT_NOT_ALLOWED";
      throw error;
    }

    const info = await stat(resolvedPath);
    if (!info.isFile()) {
      const error = new Error("artifact is not a regular file");
      error.code = "ARTIFACT_NOT_ALLOWED";
      throw error;
    }

    const format = artifactFormat(relativePath);
    if (format === "pdf-text" && info.size > this.maxPdfBytes) {
      const error = new Error("PDF artifact exceeds the safe preview limit");
      error.code = "ARTIFACT_TOO_LARGE";
      throw error;
    }

    const digest = createHash("sha256");
    const previewChunks = [];
    const sourceChunks = [];
    let previewBytes = 0;
    for await (const chunk of createReadStream(resolvedPath)) {
      digest.update(chunk);
      if (format === "pdf-text") {
        sourceChunks.push(chunk);
      } else if (previewBytes < this.maxBytes) {
        const remaining = this.maxBytes - previewBytes;
        const previewChunk = chunk.subarray(0, remaining);
        previewChunks.push(previewChunk);
        previewBytes += previewChunk.byteLength;
      }
    }
    const actualSha256 = digest.digest("hex");
    if (actualSha256 !== metadata.sha256) {
      const error = new Error(
        "artifact bytes changed after the workspace snapshot was captured",
      );
      error.code = "EVIDENCE_STALE";
      throw error;
    }

    const common = {
      id: metadata.id,
      path: relativePath,
      label: metadata.label,
      kind: metadata.kind,
      format,
      sourceBytes: info.size,
      sha256: actualSha256,
      snapshotId,
      ...(metadata.entity ? { entity: metadata.entity } : {}),
      provenance: metadata.provenance,
    };

    if (format === "pdf-text") {
      const preview = await extractPdfText(
        Buffer.concat(sourceChunks, info.size),
        {
          maxPages: this.maxPdfPages,
          maxTextBytes: this.maxPdfTextBytes,
        },
      );
      return {
        ...common,
        ...preview,
      };
    }

    const previewBuffer = Buffer.concat(previewChunks);
    const truncated = info.size > this.maxBytes;
    const preview = redactSensitiveTextWithReport(
      decodeTextPreview(previewBuffer, { truncated }),
    );

    return {
      ...common,
      content: preview.content,
      truncated,
      redacted: preview.redacted,
    };
  }
}

export { artifactFormat, decodeTextPreview, normalizeRequestedPath };
