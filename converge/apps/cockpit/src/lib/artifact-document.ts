import type { ArtifactDocument, ArtifactRef } from "../types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function matchesArtifactDocument(
  candidate: unknown,
  artifact: ArtifactRef,
  snapshotId: string,
): candidate is ArtifactDocument {
  if (
    !isRecord(candidate) ||
    candidate.path !== artifact.path ||
    candidate.label !== artifact.label ||
    candidate.kind !== artifact.kind ||
    candidate.snapshotId !== snapshotId ||
    candidate.sha256 !== artifact.sha256 ||
    typeof candidate.truncated !== "boolean" ||
    typeof candidate.redacted !== "boolean" ||
    !Number.isInteger(candidate.sourceBytes) ||
    Number(candidate.sourceBytes) < 0
  ) return false;

  if (candidate.format === "markdown" || candidate.format === "text") {
    return typeof candidate.content === "string";
  }
  if (
    candidate.format !== "pdf-text" ||
    !Array.isArray(candidate.pages) ||
    !Number.isInteger(candidate.pageCount) ||
    Number(candidate.pageCount) < 1
  ) return false;
  return candidate.pages.every(
    (page) =>
      isRecord(page) &&
      Number.isInteger(page.number) &&
      Number(page.number) >= 1 &&
      Number(page.number) <= Number(candidate.pageCount) &&
      typeof page.text === "string",
  );
}

export function artifactPreviewError(status: number) {
  if (status === 503) return "The live workspace snapshot is unavailable. Reconnect or refresh Cockpit before opening this artifact.";
  if (status === 409) return "This proof is stale. Refresh the workspace before opening it.";
  if (status === 413) return "This artifact is larger than the safe preview limit.";
  if (status === 422) return "This PDF could not be converted into a safe text preview.";
  if (status === 403) return "This artifact is not in the workspace evidence allowlist.";
  return `Artifact is unavailable (${status})`;
}
