import { useEffect, useState } from "react";
import { artifactPreviewError, matchesArtifactDocument } from "../lib/artifact-document";
import type { ArtifactDocument, ArtifactRef, WorkspaceSnapshot } from "../types";

export type ArtifactDocumentState =
  | { status: "idle"; document: null; error: null }
  | { status: "loading"; document: null; error: null }
  | { status: "ready"; document: ArtifactDocument; error: null }
  | { status: "error"; document: null; error: string };

export function useArtifactDocument(snapshot: WorkspaceSnapshot, artifact: ArtifactRef | null) {
  const [state, setState] = useState<ArtifactDocumentState>({ status: "idle", document: null, error: null });

  useEffect(() => {
    if (!artifact) {
      setState({ status: "idle", document: null, error: null });
      return;
    }
    if (snapshot.source !== "workspace") {
      setState({
        status: "error",
        document: null,
        error: "Replay fixture entries cannot be opened as verified artifacts. Connect Cockpit to a live Converge workspace and refresh.",
      });
      return;
    }
    const target = artifact;

    const controller = new AbortController();
    async function load() {
      setState({ status: "loading", document: null, error: null });
      try {
        const query = new URLSearchParams({ path: target.path, snapshotId: snapshot.snapshotId, sha256: target.sha256 });
        const response = await fetch(`/api/artifact?${query.toString()}`, {
          method: "GET",
          signal: controller.signal,
          headers: { Accept: "application/json" },
        });
        if (!response.ok) throw new Error(artifactPreviewError(response.status));
        const candidate: unknown = await response.json();
        if (!matchesArtifactDocument(candidate, target, snapshot.snapshotId)) {
          throw new Error("Artifact no longer matches the selected proof.");
        }
        setState({ status: "ready", document: candidate, error: null });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState({ status: "error", document: null, error: error instanceof Error ? error.message : "Artifact is unavailable." });
      }
    }
    void load();
    return () => controller.abort();
  }, [artifact, snapshot.snapshotId, snapshot.source]);

  return state;
}
