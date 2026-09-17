import {
  ArrowRight,
  ArrowSquareOut,
  CaretDoubleLeft,
  CaretDoubleRight,
  ClockCounterClockwise,
  FileCode,
  FlowArrow,
  Info,
  ShieldCheck,
  WarningCircle,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { KeyboardEvent } from "react";
import {
  artifactsByIds,
  relatedSignals,
  resolveEntity,
} from "../lib/entities";
import type {
  ArtifactRef,
  EntityRef,
  InspectorTab,
  WorkspaceSnapshot,
} from "../types";

interface InspectorPanelProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  tab: InspectorTab;
  expanded: boolean;
  placement?: "left" | "right";
  onTabChange: (tab: InspectorTab) => void;
  onToggle: () => void;
  onOpenArtifact: (artifact: ArtifactRef) => void;
  onSelect: (selection: EntityRef) => void;
}

const TABS: Array<{ id: InspectorTab; label: string; icon: typeof Info }> = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "evidence", label: "Evidence", icon: ShieldCheck },
  { id: "activity", label: "Activity", icon: ClockCounterClockwise },
];

function tabKeyDown(
  event: KeyboardEvent<HTMLButtonElement>,
  current: InspectorTab,
  onChange: (tab: InspectorTab) => void,
) {
  const currentIndex = TABS.findIndex((tab) => tab.id === current);
  let nextIndex = currentIndex;
  if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % TABS.length;
  else if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + TABS.length) % TABS.length;
  else if (event.key === "Home") nextIndex = 0;
  else if (event.key === "End") nextIndex = TABS.length - 1;
  else return;
  event.preventDefault();
  onChange(TABS[nextIndex].id);
  document.getElementById(`inspector-tab-${TABS[nextIndex].id}`)?.focus();
}

export function InspectorPanel({
  snapshot,
  selected,
  tab,
  expanded,
  placement = "right",
  onTabChange,
  onToggle,
  onOpenArtifact,
  onSelect,
}: InspectorPanelProps) {
  const reduceMotion = useReducedMotion();
  const entity = resolveEntity(snapshot, selected);
  const artifacts = entity ? artifactsByIds(snapshot, entity.artifactIds) : [];
  const activity = entity ? relatedSignals(snapshot, entity.ref) : [];
  const issues = selected
    ? snapshot.issues.filter(
        (issue) => issue.entity?.kind === selected.kind && issue.entity.id === selected.id,
      )
    : [];
  const pass =
    selected?.kind === "pass"
      ? snapshot.method.passes.find((candidate) => candidate.id === selected.id) ?? null
      : null;
  const passEdges = pass
    ? snapshot.method.edges.filter((edge) => edge.source === pass.id || edge.target === pass.id)
    : [];
  const currentAuthorization =
    pass && snapshot.authorization.nextPassId === pass.id ? snapshot.authorization : null;
  const passReview = pass?.order === 4 ? snapshot.review : null;
  const fixture = snapshot.source === "fixture";
  const ExpandIcon = placement === "left" ? CaretDoubleRight : CaretDoubleLeft;
  const CollapseIcon = placement === "left" ? CaretDoubleLeft : CaretDoubleRight;

  return (
    <aside
      id="cockpit-inspector"
      className={`inspector inspector--${placement} ${
        expanded ? "inspector--expanded" : "inspector--collapsed"
      }`}
      aria-label={pass ? `${pass.label} pass blade` : "Selection inspector"}
    >
      <header className="inspector__top">
        <button
          type="button"
          className="rail-toggle"
          onClick={onToggle}
          aria-expanded={expanded}
          aria-controls="cockpit-inspector"
          aria-label={expanded ? "Collapse inspector" : "Expand inspector"}
          title={expanded ? "Collapse inspector" : "Expand inspector"}
        >
          {expanded ? <CollapseIcon aria-hidden="true" /> : <ExpandIcon aria-hidden="true" />}
        </button>
        <span>{pass ? "Pass blade" : "Inspector"}</span>
      </header>

      {!expanded ? (
        <button type="button" className="inspector-peek" onClick={onToggle} aria-label="Expand selection inspector">
          <span className={`status-beacon status-beacon--${entity?.status ?? "empty"}`} />
          <span>{entity?.title ?? "No selection"}</span>
          <small>{artifacts.length}</small>
        </button>
      ) : (
        <>
          <div className="inspector__identity">
            {entity ? (
              <>
                <span>{entity.eyebrow}</span>
                <h2>{entity.title}</h2>
                <p>{entity.summary}</p>
                <div className="inspector__status-row">
                  <span className="inspector__status">
                    <span className={`status-beacon status-beacon--${entity.status}`} />
                    {entity.status.replaceAll("_", " ")}
                  </span>
                  {pass ? <span className="inspector__gate">Gate {pass.gate.verdict ?? "not evaluated"}</span> : null}
                </div>
              </>
            ) : (
              <>
                <span>Nothing selected</span>
                <h2>Choose an observed entity</h2>
                <p>Select a pass, lane, leg, task, run, receipt, file, check, or issue.</p>
              </>
            )}
          </div>

          <div className="inspector-tabs" role="tablist" aria-label="Inspector views">
            {TABS.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  type="button"
                  key={item.id}
                  id={`inspector-tab-${item.id}`}
                  role="tab"
                  tabIndex={tab === item.id ? 0 : -1}
                  aria-selected={tab === item.id}
                  aria-controls="inspector-tabpanel"
                  className={tab === item.id ? "is-active" : ""}
                  onClick={() => onTabChange(item.id)}
                  onKeyDown={(event) => tabKeyDown(event, item.id, onTabChange)}
                >
                  <Icon aria-hidden="true" />
                  {item.label}
                </button>
              );
            })}
          </div>

          <div
            id="inspector-tabpanel"
            className="inspector__content"
            role="tabpanel"
            aria-labelledby={`inspector-tab-${tab}`}
            tabIndex={0}
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={`${selected?.kind ?? "none"}:${selected?.id ?? "none"}:${tab}`}
                initial={reduceMotion ? false : { opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0, x: -5 }}
                transition={{ duration: 0.16 }}
              >
                {tab === "overview" ? (
                  entity ? (
                    <div className="inspector-overview">
                      {currentAuthorization ? (
                        <section className={`pass-authorization is-${currentAuthorization.state}`}>
                          <span>Current authorization</span>
                          <strong>{currentAuthorization.state}</strong>
                          <p>{currentAuthorization.rationale}</p>
                          {currentAuthorization.command ? <code>{currentAuthorization.command}</code> : null}
                        </section>
                      ) : null}
                      <dl className="detail-list">
                        {entity.details.map((detail) => (
                          <div key={detail.label}>
                            <dt>{detail.label}</dt>
                            <dd>{detail.value}</dd>
                          </div>
                        ))}
                      </dl>
                      {passEdges.length > 0 ? (
                        <section className="pass-relationships">
                          <header><FlowArrow aria-hidden="true" /><strong>Method relationships</strong></header>
                          {passEdges.map((edge) => {
                            const incoming = edge.target === pass?.id;
                            const relatedId = incoming ? edge.source : edge.target;
                            const related = snapshot.method.passes.find((candidate) => candidate.id === relatedId);
                            return (
                              <button type="button" key={edge.id} onClick={() => onSelect({ kind: "pass", id: relatedId })}>
                                <span>{incoming ? "From" : "To"} · {edge.kind}</span>
                                <strong>{related ? `Pass ${related.order} · ${related.label}` : relatedId}</strong>
                                <ArrowRight mirrored={incoming} aria-hidden="true" />
                              </button>
                            );
                          })}
                        </section>
                      ) : null}
                      {passReview ? (
                        <section className="pass-review">
                          <header><WarningCircle weight="fill" aria-hidden="true" /><span><strong>Consensus review</strong><small>Round {passReview.round} · {passReview.verdict}</small></span></header>
                          <p>{passReview.unresolvedCount} unresolved objection{passReview.unresolvedCount === 1 ? "" : "s"}</p>
                          {passReview.objections.map((objection) => (
                            <div key={objection.id}><strong>{objection.title}</strong><small>{objection.severity} · {objection.resolved ? "resolved" : "open"}</small></div>
                          ))}
                          {passReview.openQuestions.map((question) => (
                            <div key={question.id}><strong>{question.question}</strong><small>{question.owner}{question.blocksBuild ? " · blocks build" : ""}</small></div>
                          ))}
                        </section>
                      ) : null}
                      {issues.length > 0 ? (
                        <section className="inspector-issues">
                          <header><WarningCircle aria-hidden="true" /><strong>Linked issues</strong></header>
                          {issues.map((issue) => (
                            <button type="button" key={issue.id} onClick={() => onSelect({ kind: "issue", id: issue.id })}>
                              <span className={`status-beacon status-beacon--${issue.severity}`} />
                              <span><strong>{issue.message}</strong><small>{issue.code} · {issue.severity}</small></span>
                            </button>
                          ))}
                        </section>
                      ) : null}
                    </div>
                  ) : (
                    <InspectorEmpty copy="Overview appears after an entity is selected." />
                  )
                ) : null}

                {tab === "evidence" ? (
                  artifacts.length > 0 ? (
                    <>
                      {fixture ? (
                        <p className="inspector-boundary-note">Replay metadata is visible, but verified file bytes require a live workspace.</p>
                      ) : null}
                      <div className="inspector-proof-list">
                        {artifacts.map((artifact) => (
                          <button
                            type="button"
                            key={artifact.id}
                            onClick={() => onOpenArtifact(artifact)}
                            disabled={fixture}
                            title={fixture ? "Connect a live workspace to read verified bytes" : "Open verified preview"}
                          >
                            <FileCode aria-hidden="true" />
                            <span>
                              <strong>{artifact.label}</strong>
                              <small>{artifact.path}</small>
                              <code>{artifact.sha256.slice(0, 12)}</code>
                            </span>
                            <ArrowSquareOut aria-hidden="true" />
                          </button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <InspectorEmpty copy="No hash-bound evidence is linked to this entity." />
                  )
                ) : null}

                {tab === "activity" ? (
                  activity.length > 0 ? (
                    <>
                      <p className="inspector-boundary-note">Current snapshot signals—not a durable event history.</p>
                      <ol className="inspector-history">
                        {activity.map((signal) => (
                          <li key={signal.id}>
                            <span className={`status-beacon status-beacon--${signal.severity}`} aria-hidden="true" />
                            <div>
                              <strong>{signal.summary}</strong>
                              <small>{signal.kind}</small>
                              <time dateTime={signal.occurredAt ?? undefined}>
                                {signal.occurredAt ? new Date(signal.occurredAt).toLocaleString() : "Time unavailable"}
                              </time>
                            </div>
                          </li>
                        ))}
                      </ol>
                    </>
                  ) : (
                    <InspectorEmpty copy="No current signals reference this entity." />
                  )
                ) : null}
              </motion.div>
            </AnimatePresence>
          </div>
        </>
      )}
    </aside>
  );
}

function InspectorEmpty({ copy }: { copy: string }) {
  return (
    <div className="inspector-empty">
      <Info aria-hidden="true" />
      <p>{copy}</p>
    </div>
  );
}
