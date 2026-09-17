import { useEffect, useState } from "react";
import {
  Article,
  FlowArrow,
  Graph,
  LockKey,
} from "@phosphor-icons/react";
import type { EntityRef, WorkspaceSnapshot } from "../types";
import { DecompositionGraph } from "./DecompositionGraph";
import { DecompositionList } from "./DecompositionList";
import { DecompositionFocus } from "./DecompositionFocus";

interface DecomposeSurfaceProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

type DecomposeView = "focus" | "graph" | "list";
const MAX_GRAPH_LEGS = 160;
const MAX_GRAPH_EDGES = 320;
const MAX_GRAPH_LANES = 40;

function isMobileViewport() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(max-width: 767px)").matches
  );
}

export function DecomposeSurface({
  snapshot,
  selected,
  onSelect,
}: DecomposeSurfaceProps) {
  const decomposition = snapshot.decomposition;
  const graphTooDense =
    decomposition.swimlanes.length > MAX_GRAPH_LANES ||
    decomposition.legs.length > MAX_GRAPH_LEGS ||
    decomposition.edges.length > MAX_GRAPH_EDGES;
  const [mobile, setMobile] = useState(isMobileViewport);
  const [view, setView] = useState<DecomposeView>("focus");

  useEffect(() => {
    const media = window.matchMedia("(max-width: 767px)");
    const sync = () => {
      setMobile(media.matches);
      if (media.matches && view === "graph") setView("focus");
    };
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, [view]);

  useEffect(() => {
    if (graphTooDense && view === "graph") setView("focus");
  }, [graphTooDense, view]);

  const highRisk = decomposition.swimlanes.filter(
    (lane) => lane.risk === "high",
  ).length;
  const threads = decomposition.swimlanes.filter((lane) => lane.thread).length;

  return (
    <section
      className="surface surface--decompose"
      aria-labelledby="decompose-title"
    >
      <header className="surface-header">
        <div>
          <span>Seams into bounded delivery</span>
          <h1 id="decompose-title">Decompose</h1>
        </div>
        <div className="segmented-control" aria-label="Decomposition presentation">
          <button
            type="button"
            className={view === "focus" ? "is-active" : ""}
            onClick={() => setView("focus")}
            aria-pressed={view === "focus"}
          >
            <FlowArrow aria-hidden="true" />
            Focus
          </button>
          <button
            type="button"
            className={view === "graph" ? "is-active" : ""}
            onClick={() => setView("graph")}
            aria-pressed={view === "graph"}
            disabled={mobile || graphTooDense}
            title={
              mobile
                ? "Graph is available on wider screens"
                : graphTooDense
                  ? "Read view protects responsiveness for large decompositions"
                  : undefined
            }
          >
            <Graph aria-hidden="true" />
            Map
          </button>
          <button
            type="button"
            className={view === "list" ? "is-active" : ""}
            onClick={() => setView("list")}
            aria-pressed={view === "list"}
          >
            <Article aria-hidden="true" />
            Read
          </button>
        </div>
      </header>

      {decomposition.availability === "unavailable" ? (
        <div className="surface-state">
          <LockKey size={28} weight="fill" aria-hidden="true" />
          <strong>Decomposition unavailable</strong>
          <p>The snapshot could not project a trustworthy lane graph.</p>
        </div>
      ) : decomposition.availability === "empty" ||
        decomposition.swimlanes.length === 0 ? (
        <div className="surface-state">
          <FlowArrow size={28} weight="fill" aria-hidden="true" />
          <strong>No canonical swimlane plans were observed</strong>
          <p>Pass 3 will populate seams, lanes, and legs when plans exist.</p>
        </div>
      ) : (
        <>
          <div className="decompose-summary" aria-label="Decomposition summary">
            <span>
              <strong>{decomposition.swimlanes.length}</strong>
              swimlanes
            </span>
            <span>
              <strong>{decomposition.legs.length}</strong>
              delivery legs
            </span>
            <span className="tone-active">
              <strong>{threads}</strong>
              steel-thread lanes
            </span>
            <span className={highRisk ? "tone-danger" : "tone-proven"}>
              <strong>{highRisk}</strong>
              high risk
            </span>
          </div>
          {graphTooDense ? (
            <div className="decompose-density-notice" role="status">
              Focus view protects readability for this large decomposition (
              {decomposition.legs.length} legs and {decomposition.edges.length} edges).
            </div>
          ) : null}
          {view === "focus" ? (
            <DecompositionFocus
              snapshot={snapshot}
              selected={selected}
              onSelect={onSelect}
            />
          ) : view === "graph" && !mobile && !graphTooDense ? (
            <DecompositionGraph
              snapshot={snapshot}
              selected={selected}
              onSelect={onSelect}
            />
          ) : (
            <DecompositionList
              snapshot={snapshot}
              selected={selected}
              onSelect={onSelect}
            />
          )}
        </>
      )}
    </section>
  );
}
