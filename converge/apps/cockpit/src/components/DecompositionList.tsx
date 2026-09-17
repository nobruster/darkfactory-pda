import {
  CaretDown,
  CheckCircle,
  Circle,
  GitBranch,
} from "@phosphor-icons/react";
import type {
  DecompositionLeg,
  EntityRef,
  WorkspaceSnapshot,
} from "../types";

interface DecompositionListProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

function readable(value: string) {
  return value.replaceAll("—", "-").replaceAll("–", "-").replaceAll(" · ", " / ");
}

function laneName(label: string) {
  return readable(label.replace(/^Swimlane\s*[·:]\s*/i, ""));
}

function values(items: string[], fallback = "Not recorded") {
  return items.length > 0 ? items.map(readable).join(", ") : fallback;
}

function LegStatus({ leg }: { leg: DecompositionLeg }) {
  const complete = leg.status === "done" || leg.status === "accepted";
  return (
    <span className={`decomposition-list__status is-${leg.status}`}>
      {complete ? <CheckCircle weight="fill" aria-hidden="true" /> : <Circle weight={leg.status === "in_progress" ? "fill" : "regular"} aria-hidden="true" />}
      {leg.status.replaceAll("_", " ")}
    </span>
  );
}

export function DecompositionList({
  snapshot,
  selected,
  onSelect,
}: DecompositionListProps) {
  const legsById = new Map(snapshot.decomposition.legs.map((leg) => [leg.id, leg] as const));

  return (
    <div className="decomposition-list decomposition-list--reader">
      <header className="decomposition-reader-intro">
        <div>
          <span>Readable decomposition</span>
          <h2>Seams and delivery contracts</h2>
          <p>Open only the swimlane and leg you need. The full canonical text remains available without forcing every contract onto the screen at once.</p>
        </div>
        <strong>{snapshot.decomposition.swimlanes.length} swimlanes</strong>
      </header>

      {snapshot.decomposition.swimlanes.map((lane, laneIndex) => {
        const laneLegs = lane.legIds
          .map((id) => legsById.get(id))
          .filter((leg): leg is DecompositionLeg => Boolean(leg))
          .sort((left, right) => left.order - right.order);
        const laneSelected = selected?.kind === "swimlane" && selected.id === lane.id;
        const containsSelectedLeg = selected?.kind === "leg" && laneLegs.some((leg) => leg.id === selected.id);
        return (
          <details
            className={`decomposition-reader-lane ${laneSelected || containsSelectedLeg ? "is-selected" : ""}`}
            key={lane.id}
            open={laneIndex === 0 || laneSelected || containsSelectedLeg}
          >
            <summary
              role="button"
              aria-expanded={laneIndex === 0 || laneSelected || containsSelectedLeg}
              onClick={() => onSelect({ kind: "swimlane", id: lane.id })}
            >
              <span className="decomposition-reader-lane__number">{String(laneIndex + 1).padStart(2, "0")}</span>
              <span className="decomposition-reader-lane__copy">
                <small>Swimlane</small>
                <strong>{laneName(lane.label)}</strong>
              </span>
              <span className="decomposition-reader-lane__meta">
                {lane.thread ? <em>Steel thread</em> : null}
                <span className={`risk-chip risk-chip--${lane.risk}`}>{lane.risk} risk</span>
                <span>{laneLegs.length} legs</span>
              </span>
              <CaretDown aria-hidden="true" />
            </summary>

            <div className="decomposition-reader-lane__body">
              <section className="decomposition-reader-seam">
                <div>
                  <span>Why this seam</span>
                  <p>{readable(lane.seam.rationale ?? lane.purpose ?? "No rationale recorded.")}</p>
                </div>
                <dl>
                  <div><dt>Consumes</dt><dd>{readable(lane.seam.inputContract ?? lane.seam.consumedInterface ?? "Not recorded")}</dd></div>
                  <div><dt>Produces</dt><dd>{readable(lane.seam.outputContract ?? "Not recorded")}</dd></div>
                  <div><dt>Owner</dt><dd>{lane.owner}</dd></div>
                </dl>
              </section>

              <section className="decomposition-reader-legs" aria-label={`${laneName(lane.label)} delivery legs`}>
                <header><GitBranch aria-hidden="true" /><h3>Delivery legs</h3><span>{laneLegs.length}</span></header>
                {laneLegs.map((leg) => {
                  const active = selected?.kind === "leg" && selected.id === leg.id;
                  return (
                    <details className={`decomposition-reader-leg ${active ? "is-selected" : ""}`} key={leg.id} open={active}>
                      <summary
                        role="button"
                        aria-expanded={active}
                        onClick={(event) => {
                          event.stopPropagation();
                          onSelect({ kind: "leg", id: leg.id });
                        }}
                      >
                        <span className="decomposition-reader-leg__order">{String(leg.order).padStart(2, "0")}</span>
                        <span><strong>{readable(leg.title)}</strong><small>{leg.tech ?? "Technology open"} / {leg.dependsOn.length} dependencies</small></span>
                        <LegStatus leg={leg} />
                        <CaretDown aria-hidden="true" />
                      </summary>
                      <div className="decomposition-reader-leg__body">
                        <p>{readable(leg.responsibility ?? "Responsibility is not recorded.")}</p>
                        <dl>
                          <div><dt>Consumes</dt><dd>{values(leg.consumes)}</dd></div>
                          <div><dt>Produces</dt><dd>{values(leg.produces)}</dd></div>
                          <div><dt>Proves</dt><dd>{values(leg.proves)}</dd></div>
                          <div><dt>Yields</dt><dd>{values(leg.yields)}</dd></div>
                        </dl>
                      </div>
                    </details>
                  );
                })}
              </section>
            </div>
          </details>
        );
      })}
    </div>
  );
}
