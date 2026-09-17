import {
  ArrowRight,
  CheckCircle,
  Circle,
  GitBranch,
  Stack,
  Target,
} from "@phosphor-icons/react";
import type {
  DecompositionLeg,
  EntityRef,
  WorkspaceSnapshot,
} from "../types";

interface DecompositionFocusProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

function readable(value: string) {
  return value
    .replaceAll("—", "-")
    .replaceAll("–", "-")
    .replaceAll(" · ", " / ");
}

function laneName(label: string) {
  return readable(label.replace(/^Swimlane\s*[·:]\s*/i, ""));
}

function values(items: string[], fallback = "Not recorded") {
  return items.length > 0 ? items.map(readable).join(", ") : fallback;
}

function StatusIcon({ status }: { status: DecompositionLeg["status"] }) {
  return status === "done" || status === "accepted" ? (
    <CheckCircle weight="fill" aria-hidden="true" />
  ) : (
    <Circle weight={status === "in_progress" ? "fill" : "regular"} aria-hidden="true" />
  );
}

function LegDetail({ leg }: { leg: DecompositionLeg }) {
  return (
    <article className="decomposition-leg-detail" aria-labelledby={`focused-leg-${leg.id}`}>
      <header>
        <span className="decomposition-leg-detail__order">{String(leg.order).padStart(2, "0")}</span>
        <span>
          <small>Delivery leg</small>
          <h3 id={`focused-leg-${leg.id}`}>{readable(leg.title)}</h3>
        </span>
        <span className={`decomposition-leg-detail__status is-${leg.status}`}>
          <StatusIcon status={leg.status} />
          {leg.status.replaceAll("_", " ")}
        </span>
      </header>

      <p className="decomposition-leg-detail__responsibility">
        {readable(leg.responsibility ?? "Responsibility is not recorded.")}
      </p>

      <div className="decomposition-leg-detail__tags" aria-label="Leg attributes">
        <span><Stack aria-hidden="true" />{leg.tech ?? "Technology open"}</span>
        <span><Target aria-hidden="true" />{leg.appetite ?? "No appetite recorded"}</span>
        <span><GitBranch aria-hidden="true" />{leg.dependsOn.length} dependencies</span>
      </div>

      {leg.dependsOn.length > 0 ? (
        <section className="decomposition-leg-detail__dependencies">
          <h4>Depends on</h4>
          <div>{leg.dependsOn.map((dependency) => <code key={dependency}>{dependency}</code>)}</div>
        </section>
      ) : null}

      <dl className="decomposition-leg-detail__contract">
        <div><dt>Consumes</dt><dd>{values(leg.consumes)}</dd></div>
        <div><dt>Produces</dt><dd>{values(leg.produces)}</dd></div>
        <div><dt>Independent because</dt><dd>{readable(leg.independence ?? "Not recorded")}</dd></div>
        <div><dt>Re-verify when</dt><dd>{readable(leg.reverifyWhen ?? "Not recorded")}</dd></div>
      </dl>

      <details className="decomposition-leg-detail__proof">
        <summary>
          <span><CheckCircle aria-hidden="true" />Acceptance proof</span>
          <strong>{leg.proves.length}</strong>
        </summary>
        <ul>{leg.proves.map((proof) => <li key={proof}>{readable(proof)}</li>)}</ul>
      </details>

      <details className="decomposition-leg-detail__proof">
        <summary>
          <span><Stack aria-hidden="true" />Expected yield</span>
          <strong>{leg.yields.length}</strong>
        </summary>
        <ul>{leg.yields.map((item) => <li key={item}>{readable(item)}</li>)}</ul>
      </details>
    </article>
  );
}

export function DecompositionFocus({
  snapshot,
  selected,
  onSelect,
}: DecompositionFocusProps) {
  const decomposition = snapshot.decomposition;
  const selectedLeg =
    selected?.kind === "leg"
      ? decomposition.legs.find((leg) => leg.id === selected.id)
      : null;
  const laneId =
    selected?.kind === "swimlane"
      ? selected.id
      : selectedLeg?.swimlaneId ?? decomposition.swimlanes[0]?.id;
  const lane = decomposition.swimlanes.find((candidate) => candidate.id === laneId);
  if (!lane) return null;

  const legs = lane.legIds
    .map((id) => decomposition.legs.find((candidate) => candidate.id === id))
    .filter((leg): leg is DecompositionLeg => Boolean(leg))
    .sort((left, right) => left.order - right.order);
  const focusedLeg = selectedLeg?.swimlaneId === lane.id ? selectedLeg : legs[0] ?? null;

  return (
    <div className="decomposition-focus decomposition-focus--mastery">
      <nav className="decomposition-focus__lanes" aria-label="Choose a swimlane">
        {decomposition.swimlanes.map((candidate) => (
          <button
            type="button"
            key={candidate.id}
            className={candidate.id === lane.id ? "is-active" : ""}
            onClick={() => onSelect({ kind: "swimlane", id: candidate.id })}
            aria-current={candidate.id === lane.id ? "true" : undefined}
          >
            <span className="decomposition-focus__lane-index">Swimlane</span>
            <strong>{laneName(candidate.label)}</strong>
            <span className="decomposition-focus__lane-tags">
              {candidate.thread ? <em>Steel thread</em> : null}
              <small>{candidate.legIds.length} legs</small>
              <small>{candidate.risk} risk</small>
            </span>
          </button>
        ))}
      </nav>

      <article className="decomposition-focus__canvas">
        <header className="decomposition-focus__identity">
          <div>
            <span>Swimlane</span>
            <h2>{laneName(lane.label)}</h2>
            <code>{lane.id}</code>
          </div>
          <div className="decomposition-focus__identity-tags">
            {lane.thread ? <span className="decomposition-tag decomposition-tag--thread">Steel thread</span> : null}
            <span className={`risk-chip risk-chip--${lane.risk}`}>{lane.risk} risk</span>
            <span className="decomposition-tag">Owner: {lane.owner}</span>
          </div>
        </header>

        <div className="decomposition-focus__brief">
          <section className="decomposition-focus__seam" aria-labelledby="focused-seam-title">
            <span>Why this seam</span>
            <h3 id="focused-seam-title">
              {readable(lane.seam.rationale ?? lane.purpose ?? "No rationale recorded.")}
            </h3>
            {lane.purpose && lane.purpose !== lane.seam.rationale ? <p>{readable(lane.purpose)}</p> : null}
          </section>

          <dl className="decomposition-focus__contract">
            <div><dt>Consumes</dt><dd>{readable(lane.seam.inputContract ?? lane.seam.consumedInterface ?? "Not recorded")}</dd></div>
            <div><dt>Produces</dt><dd>{readable(lane.seam.outputContract ?? "Not recorded")}</dd></div>
            <div><dt>Can evolve when</dt><dd>{readable(lane.seam.evolution ?? "Not recorded")}</dd></div>
          </dl>
        </div>

        <section className="decomposition-plan" aria-labelledby="decomposition-plan-title">
          <header>
            <GitBranch aria-hidden="true" />
            <span><h3 id="decomposition-plan-title">Delivery plan</h3><p>Select a leg to read its complete bounded contract.</p></span>
            <strong>{legs.length} legs</strong>
          </header>
          <div className="decomposition-plan__workspace">
            <nav className="decomposition-plan__legs" aria-label={`${laneName(lane.label)} delivery legs`}>
              {legs.map((leg) => {
                const active = focusedLeg?.id === leg.id;
                return (
                  <button
                    type="button"
                    key={leg.id}
                    className={active ? "is-active" : ""}
                    onClick={() => onSelect({ kind: "leg", id: leg.id })}
                    aria-pressed={active}
                  >
                    <span className="decomposition-plan__leg-order">{String(leg.order).padStart(2, "0")}</span>
                    <span className="decomposition-plan__leg-copy">
                      <strong>{readable(leg.title)}</strong>
                      <small>{leg.tech ?? "Technology open"}</small>
                    </span>
                    <span className={`decomposition-plan__leg-state is-${leg.status}`}><StatusIcon status={leg.status} /></span>
                    <ArrowRight aria-hidden="true" />
                  </button>
                );
              })}
            </nav>
            {focusedLeg ? <LegDetail leg={focusedLeg} /> : null}
          </div>
        </section>
      </article>
    </div>
  );
}
