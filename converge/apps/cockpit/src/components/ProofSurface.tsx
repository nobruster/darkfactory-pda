import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowSquareOut,
  FileCode,
  FileMd,
  FilePdf,
  Fingerprint,
  MagnifyingGlass,
  SealCheck,
  WarningCircle,
} from "@phosphor-icons/react";
import { useArtifactDocument } from "../hooks/useArtifactDocument";
import type { ArtifactRef, EntityRef, WorkspaceSnapshot } from "../types";
import { DocumentRenderer } from "./DocumentRenderer";

interface ProofSurfaceProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
  onOpenArtifact: (artifact: ArtifactRef) => void;
}

const DOCUMENT_EXTENSION = /\.(?:md|markdown|pdf|txt|json|ya?ml|toml|csv|log)$/i;

function ArtifactIcon({ path }: { path: string }) {
  const extension = path.split(".").at(-1)?.toLowerCase();
  if (extension === "pdf") return <FilePdf aria-hidden="true" />;
  if (extension === "md" || extension === "markdown") return <FileMd aria-hidden="true" />;
  return <FileCode aria-hidden="true" />;
}

export function ProofSurface({
  snapshot,
  selected,
  onSelect,
  onOpenArtifact,
}: ProofSurfaceProps) {
  const [query, setQuery] = useState("");
  const [documentsOnly, setDocumentsOnly] = useState(true);
  const normalizedQuery = query.trim().toLowerCase();
  const documentCount = snapshot.artifacts.filter((artifact) => DOCUMENT_EXTENSION.test(artifact.path)).length;
  const visibleArtifacts = useMemo(
    () =>
      snapshot.artifacts.filter((artifact) => {
        if (documentsOnly && !DOCUMENT_EXTENSION.test(artifact.path)) return false;
        if (!normalizedQuery) return true;
        return `${artifact.label} ${artifact.path} ${artifact.kind}`.toLowerCase().includes(normalizedQuery);
      }),
    [documentsOnly, normalizedQuery, snapshot.artifacts],
  );
  const selectedArtifact =
    selected?.kind === "artifact"
      ? snapshot.artifacts.find((artifact) => artifact.id === selected.id) ?? null
      : null;
  const activeArtifact =
    selectedArtifact && visibleArtifacts.some((artifact) => artifact.id === selectedArtifact.id)
      ? selectedArtifact
      : visibleArtifacts[0] ?? null;
  const activeIndex = activeArtifact
    ? visibleArtifacts.findIndex((artifact) => artifact.id === activeArtifact.id)
    : -1;
  const preview = useArtifactDocument(snapshot, activeArtifact);
  const fixture = snapshot.source === "fixture";

  useEffect(() => {
    if (
      activeArtifact &&
      (selected?.kind !== "artifact" || selected.id !== activeArtifact.id)
    ) {
      onSelect({ kind: "artifact", id: activeArtifact.id });
    }
  }, [activeArtifact, onSelect, selected]);

  function selectAt(index: number) {
    const artifact = visibleArtifacts[index];
    if (artifact) onSelect({ kind: "artifact", id: artifact.id });
  }

  return (
    <section className="surface surface--proof proof-library" aria-labelledby="proof-title">
      <header className="surface-header">
        <div>
          <span>Browse every observed output</span>
          <h1 id="proof-title">Documents & proof</h1>
        </div>
        <div className="surface-header__stat">
          <Fingerprint aria-hidden="true" />
          <span><strong>{snapshot.artifacts.length}</strong>hash-bound files</span>
        </div>
      </header>

      <div className="document-browser">
        <aside className="document-browser__library" aria-labelledby="artifact-list-title">
          <header>
            <div>
              <h2 id="artifact-list-title">Generated files</h2>
              <span>{visibleArtifacts.length} shown</span>
            </div>
            <label className="document-search">
              <MagnifyingGlass aria-hidden="true" />
              <span className="visually-hidden">Search generated files</span>
              <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a file…" />
            </label>
            <div className="document-filter" role="group" aria-label="Evidence type">
              <button type="button" className={documentsOnly ? "is-active" : ""} onClick={() => setDocumentsOnly(true)} aria-pressed={documentsOnly}>
                Documents <span>{documentCount}</span>
              </button>
              <button type="button" className={!documentsOnly ? "is-active" : ""} onClick={() => setDocumentsOnly(false)} aria-pressed={!documentsOnly}>
                All evidence <span>{snapshot.artifacts.length}</span>
              </button>
            </div>
          </header>

          {visibleArtifacts.length > 0 ? (
            <div className="document-list">
              {visibleArtifacts.map((artifact) => {
                const active = activeArtifact?.id === artifact.id;
                return (
                  <button
                    type="button"
                    key={artifact.id}
                    className={active ? "is-active" : ""}
                    onClick={() => onSelect({ kind: "artifact", id: artifact.id })}
                    aria-current={active ? "true" : undefined}
                  >
                    <span className="document-list__icon"><ArtifactIcon path={artifact.path} /></span>
                    <span><strong>{artifact.label}</strong><small>{artifact.path}</small></span>
                    <code>{artifact.sha256.slice(0, 8)}</code>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="inline-state"><MagnifyingGlass aria-hidden="true" />No file matches this filter.</div>
          )}

          <details className="document-receipts">
            <summary><SealCheck aria-hidden="true" />Receipts <span>{snapshot.receipts.items.length}</span></summary>
            {snapshot.receipts.availability === "unavailable" ? (
              <p>Receipt inventory is unavailable.</p>
            ) : snapshot.receipts.items.length === 0 ? (
              <p>No settlements have emitted receipts.</p>
            ) : (
              snapshot.receipts.items.map((receipt) => (
                <button type="button" key={receipt.id} onClick={() => onSelect({ kind: "receipt", id: receipt.id })}>
                  <span className={`status-beacon status-beacon--${receipt.integrity}`} />
                  <span>
                    <strong>{receipt.taskId ?? receipt.id}</strong>
                    <small><span>{receipt.result}</span> · <span>{receipt.integrity}</span></small>
                  </span>
                  <time dateTime={receipt.recordedAt ?? undefined}>{receipt.recordedAt ? new Date(receipt.recordedAt).toLocaleDateString() : "No date"}</time>
                </button>
              ))
            )}
          </details>
        </aside>

        <article className="document-browser__reader" aria-live="polite">
          {activeArtifact ? (
            <>
              <header>
                <div>
                  <span className="document-reader-title__icon"><ArtifactIcon path={activeArtifact.path} /></span>
                  <span><strong>{activeArtifact.label}</strong><small>{activeArtifact.path}</small></span>
                </div>
                <div className="document-reader-actions">
                  <button type="button" onClick={() => selectAt(activeIndex - 1)} disabled={activeIndex <= 0} aria-label="Previous document"><ArrowLeft aria-hidden="true" /></button>
                  <span>{activeIndex + 1} / {visibleArtifacts.length}</span>
                  <button type="button" onClick={() => selectAt(activeIndex + 1)} disabled={activeIndex < 0 || activeIndex >= visibleArtifacts.length - 1} aria-label="Next document"><ArrowRight aria-hidden="true" /></button>
                  <button type="button" onClick={() => onOpenArtifact(activeArtifact)} disabled={fixture} title={fixture ? "Connect a live workspace to read verified bytes" : "Open full-screen reader"}>
                    <ArrowSquareOut aria-hidden="true" /> Full screen
                  </button>
                </div>
              </header>
              <div className="document-browser__proof">
                <span>{fixture ? "replay metadata" : activeArtifact.provenance.truthClass}</span>
                <code>sha256 {activeArtifact.sha256.slice(0, 16)}</code>
                <time dateTime={activeArtifact.provenance.observedAt}>{new Date(activeArtifact.provenance.observedAt).toLocaleString()}</time>
              </div>

              {preview.status === "loading" ? (
                <div className="document-browser__state" role="status"><CircleLoader /><strong>Loading verified document…</strong></div>
              ) : null}
              {preview.status === "error" ? (
                <div className="document-browser__state is-error" role={fixture ? "status" : "alert"}>
                  {fixture ? <SealCheck weight="fill" aria-hidden="true" /> : <WarningCircle weight="fill" aria-hidden="true" />}
                  <strong>{fixture ? "Connect a live workspace to read this file" : "Preview unavailable"}</strong>
                  <p>{preview.error}</p>
                </div>
              ) : null}
              {preview.status === "ready" ? (
                <div className="document-browser__document">
                  <div className="artifact-preview-flags">
                    <span>{preview.document.format.replace("-", " ")}</span>
                    {preview.document.redacted ? <span className="artifact-preview-flags__safety">credentials redacted</span> : null}
                    {preview.document.truncated ? <span className="artifact-preview-flags__safety">preview truncated</span> : null}
                    <span>{preview.document.sourceBytes.toLocaleString()} source bytes</span>
                  </div>
                  <DocumentRenderer document={preview.document} />
                </div>
              ) : null}
            </>
          ) : (
            <div className="document-browser__state"><FileCode aria-hidden="true" /><strong>Select a generated file</strong><p>Its readable verified preview will appear here.</p></div>
          )}
        </article>
      </div>
    </section>
  );
}

function CircleLoader() {
  return <span className="document-loader" aria-hidden="true" />;
}
