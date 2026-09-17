import {
  useEffect,
  useRef,
  type KeyboardEvent,
} from "react";
import { createPortal } from "react-dom";
import { Code, WarningCircle, X } from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { ArtifactRef, WorkspaceSnapshot } from "../types";
import { useArtifactDocument } from "../hooks/useArtifactDocument";
import { DocumentRenderer } from "./DocumentRenderer";

interface ArtifactViewerProps {
  snapshot: WorkspaceSnapshot;
  artifact: ArtifactRef | null;
  onClose: () => void;
}

export function ArtifactViewer({
  snapshot,
  artifact,
  onClose,
}: ArtifactViewerProps) {
  const reduceMotion = useReducedMotion();
  const state = useArtifactDocument(snapshot, artifact);
  const viewerRef = useRef<HTMLDivElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const replayFixture = snapshot.source === "fixture";

  useEffect(() => {
    if (!artifact) return;
    const previousOverflow = document.body.style.overflow;
    const previousFocus = document.activeElement;
    document.body.style.overflow = "hidden";
    window.requestAnimationFrame(() => closeRef.current?.focus());
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
      if (previousFocus instanceof HTMLElement) previousFocus.focus();
    };
  }, [artifact, onClose]);

  function trapFocus(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "Tab" || !viewerRef.current) return;
    const focusable = [
      ...viewerRef.current.querySelectorAll<HTMLElement>(
        'button, [href], [tabindex]:not([tabindex="-1"])',
      ),
    ].filter((element) => !element.hasAttribute("disabled"));
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return createPortal(
    <AnimatePresence>
      {artifact ? (
        <motion.div
          className="artifact-backdrop"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={reduceMotion ? undefined : { opacity: 0 }}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) onClose();
          }}
        >
          <motion.div
            ref={viewerRef}
            className="artifact-viewer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="artifact-viewer-title"
            aria-describedby="artifact-proof-summary"
            aria-busy={state.status === "loading"}
            onKeyDown={trapFocus}
            initial={reduceMotion ? false : { opacity: 0, y: 12, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: 8, scale: 0.995 }}
            transition={{ duration: 0.18 }}
          >
            <header>
              <div>
                <Code aria-hidden="true" />
                <span>
                  <strong id="artifact-viewer-title">{artifact.label}</strong>
                  <small>{artifact.path}</small>
                </span>
              </div>
              <button
                ref={closeRef}
                type="button"
                onClick={onClose}
                aria-label="Close artifact viewer"
              >
                <X aria-hidden="true" />
              </button>
            </header>

            <div className="artifact-proof" id="artifact-proof-summary">
              {replayFixture ? (
                <>
                  <span>replay fixture</span>
                  <span>example digest {artifact.sha256.slice(0, 12)}</span>
                  <span>not live evidence</span>
                </>
              ) : (
                <>
                  <span>snapshot {snapshot.snapshotId.slice(0, 12)}</span>
                  <span>verified source sha256 {artifact.sha256.slice(0, 12)}</span>
                  <span>{artifact.provenance.truthClass}</span>
                </>
              )}
            </div>

            {state.status === "loading" ? (
              <div className="artifact-loading" role="status">
                <p className="visually-hidden">Loading verified artifact preview</p>
                <div aria-hidden="true">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            ) : null}

            {state.status === "error" ? (
              <div className="artifact-error" role="alert">
                <WarningCircle size={22} weight="fill" aria-hidden="true" />
                <div>
                  <strong>
                    {replayFixture ? "Live workspace required" : "Preview unavailable"}
                  </strong>
                  <p>{state.error}</p>
                </div>
              </div>
            ) : null}

            {state.status === "ready" ? (
              <div className="artifact-document-shell">
                <div className="artifact-preview-flags" aria-label="Preview safeguards">
                  <span>{state.document.format.replace("-", " ")}</span>
                  {state.document.redacted ? (
                    <span className="artifact-preview-flags__safety">credentials redacted</span>
                  ) : null}
                  {state.document.truncated ? (
                    <span className="artifact-preview-flags__safety">preview truncated</span>
                  ) : null}
                  <span>{state.document.sourceBytes.toLocaleString()} source bytes</span>
                </div>
                <DocumentRenderer document={state.document} />
                {state.document.truncated ? (
                  <p className="document-truncation-note" role="note">
                    This safety preview is partial. The source SHA-256 above still
                    identifies the complete artifact captured by the snapshot.
                  </p>
                ) : null}
              </div>
            ) : null}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
