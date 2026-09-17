function snapshotError(code, message, options = {}) {
  const error = new Error(message, options);
  error.code = code;
  return error;
}

function extractSnapshotEnvelope(result) {
  if (result?.timedOut) {
    throw snapshotError(
      "CLI_SNAPSHOT_TIMEOUT",
      "cvg snapshot exceeded the read-only bridge timeout",
    );
  }
  if (!result?.parsed || !result.document) {
    throw snapshotError(
      "CLI_SNAPSHOT_INVALID",
      "cvg snapshot did not emit a JSON document",
    );
  }
  if (
    result.exitCode !== 0 ||
    result.document.ok !== true ||
    !result.document.data ||
    typeof result.document.data !== "object" ||
    !result.document.data.snapshot ||
    typeof result.document.data.snapshot !== "object" ||
    Array.isArray(result.document.data.snapshot)
  ) {
    throw snapshotError(
      "CLI_SNAPSHOT_REJECTED",
      "cvg snapshot did not emit a successful snapshot envelope",
    );
  }
  return result.document.data.snapshot;
}

export async function buildWorkspaceSnapshot({
  runner,
  artifactStore,
  validateSnapshot,
}) {
  if (!runner || typeof runner.run !== "function") {
    throw new TypeError("buildWorkspaceSnapshot requires a cvg runner");
  }
  if (!artifactStore || typeof artifactStore.setAllowedArtifacts !== "function") {
    throw new TypeError("buildWorkspaceSnapshot requires an artifact store");
  }
  if (typeof validateSnapshot !== "function") {
    throw new TypeError("buildWorkspaceSnapshot requires a snapshot validator");
  }

  const result = await runner.run("snapshot");
  const snapshot = extractSnapshotEnvelope(result);
  validateSnapshot(snapshot);

  // The CLI owns every semantic field and the stable digest. The bridge only
  // derives its read capability from the top-level, schema-validated references.
  artifactStore.setAllowedArtifacts(snapshot.artifacts, snapshot.snapshotId);
  return snapshot;
}

export { extractSnapshotEnvelope, snapshotError };
