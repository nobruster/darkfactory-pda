import {
  ArrowRight,
  Broadcast,
  CheckCircle,
  ClockCounterClockwise,
  FileText,
  FlowArrow,
  GitBranch,
  Heartbeat,
  Kanban,
  Pulse,
  SealCheck,
  ShieldWarning,
  Stack,
  WarningCircle,
} from "@phosphor-icons/react";
import type {
  EntityRef,
  PassState,
  Signal,
  WorkspaceSnapshot,
} from "../types";
import { StatusGlyph } from "./StatusGlyph";

interface OverviewSurfaceProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

const LIST_LIMIT = 4;

function isSelected(
  selected: EntityRef | null,
  kind: EntityRef["kind"],
  id: string,
) {
  return selected?.kind === kind && selected.id === id;
}

function formatObservedAt(value: string) {
  return new Date(value).toLocaleString();
}

function recentSignals(signals: Signal[]) {
  return [...signals]
    .sort((left, right) => {
      const rightTime = right.occurredAt ? Date.parse(right.occurredAt) : 0;
      const leftTime = left.occurredAt ? Date.parse(left.occurredAt) : 0;
      if (rightTime !== leftTime) return rightTime - leftTime;
      return left.id.localeCompare(right.id);
    })
    .slice(0, LIST_LIMIT);
}

function passAriaLabel(pass: PassState, activePassId: string | null) {
  return pass.id === activePassId
    ? `Inspect active pass ${pass.order} ${pass.label}`
    : `Inspect pass ${pass.order} ${pass.label}`;
}

function MethodPass({
  pass,
  activePassId,
  selected,
  onSelect,
}: {
  pass: PassState;
  activePassId: string | null;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}) {
  const active = pass.id === activePassId;
  const chosen = isSelected(selected, "pass", pass.id);
  return (
    <button
      type="button"
      className={`overview-method-pass overview-method-pass--${pass.status} ${active ? "is-active" : ""} ${chosen ? "is-selected" : ""}`}
      onClick={() => onSelect({ kind: "pass", id: pass.id })}
      aria-label={passAriaLabel(pass, activePassId)}
      aria-pressed={chosen}
    >
      <span className="overview-method-pass__index">{pass.order}</span>
      <span className="overview-method-pass__copy">
        <strong>{pass.label}</strong>
        <small>{pass.status}</small>
      </span>
      <span className={`overview-method-pass__state status-${pass.status}`}>
        <StatusGlyph status={pass.status} />
      </span>
    </button>
  );
}

export function OverviewSurface({
  snapshot,
  selected,
  onSelect,
}: OverviewSurfaceProps) {
  const activePass = snapshot.method.passes.find(
    (pass) => pass.id === snapshot.method.activePassId,
  );
  const frontierPass = snapshot.method.passes.find(
    (pass) => pass.id === snapshot.authorization.nextPassId,
  );
  const completePasses = snapshot.method.passes.filter(
    (pass) => pass.status === "complete",
  ).length;
  const seriousIssues = snapshot.issues.filter(
    (issue) => issue.severity === "blocking" || issue.severity === "error",
  );
  const noteworthyChecks = snapshot.health.checks.filter(
    (check) => check.status !== "healthy",
  );
  const visibleChecks = (
    noteworthyChecks.length > 0 ? noteworthyChecks : snapshot.health.checks
  ).slice(0, 3);
  const frontierTasks = snapshot.work.frontier.taskIds
    .map((id) => snapshot.work.tasks.find((task) => task.id === id))
    .filter((task) => task !== undefined)
    .slice(0, LIST_LIMIT);
  const visibleArtifacts = snapshot.artifacts.slice(0, LIST_LIMIT);
  const activity = recentSignals(snapshot.signals);
  const verifiedReceipts = snapshot.receipts.items.filter(
    (receipt) => receipt.integrity === "verified" && receipt.freshness === "current",
  ).length;
  const headline = activePass
    ? `${activePass.label} is the current method frontier.`
    : snapshot.authorization.state === "complete"
      ? "The method descent is complete. Delivery still needs proof."
      : "The next authorized move is not yet resolved.";

  return (
    <section className="surface surface--overview" aria-labelledby="overview-title">
      <header className="surface-header overview-header overview-header--mastery">
        <div>
          <span>Live project control center</span>
          <h1 id="overview-title">Overview</h1>
        </div>
        <div
          className={`overview-header__health overview-header__health--${snapshot.health.overall}`}
          aria-label={`Workspace health ${snapshot.health.overall}`}
        >
          <Heartbeat weight="fill" aria-hidden="true" />
          <span>
            <strong>{snapshot.health.overall}</strong>
            {seriousIssues.length} critical alerts
          </span>
        </div>
      </header>

      <div className="overview-control-center">
        <section className="overview-pulse" aria-labelledby="overview-pulse-title">
          <div className="overview-pulse__narrative">
            <span className="overview-pulse__label">
              <Broadcast weight="fill" aria-hidden="true" />
              Workspace pulse
            </span>
            <h2 id="overview-pulse-title">{headline}</h2>
            <p>{snapshot.authorization.rationale}</p>
            <div className="overview-pulse__command">
              <span>{snapshot.authorization.command ? "Next command" : "Method state"}</span>
              <code>{snapshot.authorization.command ?? "No next CLI command is recorded."}</code>
            </div>
          </div>

          <dl className="overview-vitals" aria-label="Workspace vital signs">
            <div>
              <dt>Method</dt>
              <dd><strong>{completePasses}</strong><span>of {snapshot.method.passes.length} complete</span></dd>
            </div>
            <div>
              <dt>Delivery</dt>
              <dd><strong>{snapshot.work.stats.total}</strong><span>Task-Specs</span></dd>
            </div>
            <div>
              <dt>Proof</dt>
              <dd><strong>{verifiedReceipts}</strong><span>current receipts</span></dd>
            </div>
            <div className={seriousIssues.length > 0 ? "is-attention" : "is-clear"}>
              <dt>Attention</dt>
              <dd><strong>{seriousIssues.length}</strong><span>critical alerts</span></dd>
            </div>
          </dl>
        </section>

        <section className="overview-method-map" aria-labelledby="overview-method-title">
          <header>
            <span className="overview-section-icon"><FlowArrow aria-hidden="true" /></span>
            <span>
              <h2 id="overview-method-title">Method map</h2>
              <p>Every state comes from the current CLI projection.</p>
            </span>
            <span className="overview-method-map__frontier">
              <small>{activePass ? "Active" : frontierPass ? "Next" : "Lane"}</small>
              <strong>{activePass?.label ?? frontierPass?.label ?? "Complete"}</strong>
            </span>
          </header>
          <div className="overview-method-rail" aria-label="Converge pass sequence">
            {snapshot.method.passes.map((pass, index) => (
              <div className="overview-method-rail__step" key={pass.id}>
                {index > 0 ? <span className="overview-method-rail__connector" aria-hidden="true" /> : null}
                <MethodPass
                  pass={pass}
                  activePassId={snapshot.method.activePassId}
                  selected={selected}
                  onSelect={onSelect}
                />
              </div>
            ))}
          </div>
        </section>

        <section className="overview-delivery" aria-labelledby="overview-delivery-title">
          <header>
            <span className="overview-section-icon"><GitBranch aria-hidden="true" /></span>
            <span>
              <h2 id="overview-delivery-title">Delivery coverage</h2>
              <p>Method outputs become work, execution, and verifiable settlement.</p>
            </span>
          </header>
          <div
            className="overview-delivery-flow"
            role="region"
            aria-label="Delivery evidence flow"
            tabIndex={0}
          >
            <div><GitBranch aria-hidden="true" /><strong>{snapshot.decomposition.legs.length}</strong><span>delivery legs</span></div>
            <ArrowRight aria-hidden="true" />
            <div><Kanban aria-hidden="true" /><strong>{snapshot.work.stats.total}</strong><span>Task-Specs</span></div>
            <ArrowRight aria-hidden="true" />
            <div><Pulse aria-hidden="true" /><strong>{snapshot.execution.runs.length}</strong><span>runs</span></div>
            <ArrowRight aria-hidden="true" />
            <div><SealCheck aria-hidden="true" /><strong>{snapshot.receipts.items.length}</strong><span>receipts</span></div>
            <ArrowRight aria-hidden="true" />
            <div className={verifiedReceipts > 0 ? "is-proven" : "is-attention"}><CheckCircle weight="fill" aria-hidden="true" /><strong>{verifiedReceipts}</strong><span>current proof</span></div>
          </div>
          <p className="overview-delivery__boundary">
            The snapshot exposes {snapshot.decomposition.legs.length} delivery legs and {snapshot.work.stats.total} canonical Task-Specs. It does not publish a one-to-one mapping, so Cockpit does not infer one.
          </p>
        </section>

        <div className="overview-operating-grid">
          <section className="overview-attention" aria-labelledby="overview-attention-title">
            <header>
              <span className="overview-section-icon"><ShieldWarning weight="fill" aria-hidden="true" /></span>
              <span><h2 id="overview-attention-title">Attention</h2><p>Checks and issues that can change what is safe to trust.</p></span>
              <strong>{noteworthyChecks.length + seriousIssues.length}</strong>
            </header>
            <div className="overview-attention__body">
              <div className="overview-attention__checks" aria-label="Noteworthy checks">
                {visibleChecks.map((check) => (
                  <button
                    type="button"
                    key={check.id}
                    className={`overview-attention-row overview-attention-row--${check.status} ${isSelected(selected, "health", check.id) ? "is-selected" : ""}`}
                    onClick={() => onSelect({ kind: "health", id: check.id })}
                    aria-pressed={isSelected(selected, "health", check.id)}
                  >
                    <Heartbeat weight="fill" aria-hidden="true" />
                    <span><strong>{check.component}</strong><small>{check.summary}</small></span>
                    <em>{check.status}</em>
                  </button>
                ))}
              </div>
              <div className="overview-attention__issues" aria-label="Observed issues">
                {seriousIssues.slice(0, 3).map((issue) => (
                  <button
                    type="button"
                    key={issue.id}
                    className={`overview-attention-row overview-attention-row--${issue.severity} ${isSelected(selected, "issue", issue.id) ? "is-selected" : ""}`}
                    onClick={() => onSelect({ kind: "issue", id: issue.id })}
                    aria-pressed={isSelected(selected, "issue", issue.id)}
                  >
                    <WarningCircle weight="fill" aria-hidden="true" />
                    <span><strong>{issue.message}</strong><small>{issue.code}</small></span>
                    <em>{issue.severity}</em>
                  </button>
                ))}
                {seriousIssues.length === 0 ? <p>No critical issues are attached to this snapshot.</p> : null}
              </div>
            </div>
          </section>

          <section className="overview-work-proof" aria-labelledby="overview-work-proof-title">
            <header>
              <span className="overview-section-icon"><Stack aria-hidden="true" /></span>
              <span><h2 id="overview-work-proof-title">Work and proof</h2><p>Dispatchable work beside its canonical evidence.</p></span>
            </header>
            <div className="overview-work-proof__split">
              <section aria-labelledby="overview-frontier-tasks">
                <header><h3 id="overview-frontier-tasks">Frontier tasks</h3><span>{frontierTasks.length}</span></header>
                {frontierTasks.length > 0 ? frontierTasks.map((task) => (
                  <button
                    type="button"
                    key={task.id}
                    className={isSelected(selected, "task", task.id) ? "is-selected" : ""}
                    onClick={() => onSelect({ kind: "task", id: task.id })}
                  >
                    <Kanban aria-hidden="true" />
                    <span><strong>{task.title}</strong><small>{task.priority ?? "No priority"} / {task.effort ?? "No effort"} / {task.status}</small></span>
                    <ArrowRight aria-hidden="true" />
                  </button>
                )) : <p>No dispatchable frontier task is recorded.</p>}
              </section>
              <section aria-labelledby="overview-artifact-inventory">
                <header><h3 id="overview-artifact-inventory">Artifact inventory</h3><span>{snapshot.artifacts.length}</span></header>
                {visibleArtifacts.map((artifact) => (
                  <button
                    type="button"
                    key={artifact.id}
                    className={isSelected(selected, "artifact", artifact.id) ? "is-selected" : ""}
                    onClick={() => onSelect({ kind: "artifact", id: artifact.id })}
                  >
                    <FileText aria-hidden="true" />
                    <span><strong>{artifact.label}</strong><small>{artifact.path}</small></span>
                    <ArrowRight aria-hidden="true" />
                  </button>
                ))}
              </section>
            </div>
          </section>
        </div>

        <section className="overview-activity" aria-labelledby="overview-activity-title">
          <header>
            <span className="overview-section-icon"><ClockCounterClockwise aria-hidden="true" /></span>
            <span>
              <h2 id="overview-activity-title">Current snapshot signals</h2>
              <p>Snapshot order unless a signal records its own timestamp. This is not a durable audit history.</p>
            </span>
          </header>
          {activity.length > 0 ? (
            <ol className="overview-activity__timeline">
              {activity.map((signal) => (
                <li key={signal.id}>
                  <button
                    type="button"
                    className={`overview-signal overview-signal--${signal.severity} ${isSelected(selected, "signal", signal.id) ? "is-selected" : ""}`}
                    onClick={() => onSelect({ kind: "signal", id: signal.id })}
                    aria-pressed={isSelected(selected, "signal", signal.id)}
                  >
                    <span className="overview-signal__marker" aria-hidden="true" />
                    <span><strong>{signal.summary}</strong><small>{signal.kind} / {signal.severity}</small></span>
                    {signal.occurredAt ? <time dateTime={signal.occurredAt}>{formatObservedAt(signal.occurredAt)}</time> : <em>Snapshot order</em>}
                  </button>
                </li>
              ))}
            </ol>
          ) : <p className="overview-empty-copy">No signals are attached to this snapshot.</p>}
        </section>

        <footer className="overview-project-context" aria-label="Project context">
          <GitBranch aria-hidden="true" />
          <span><strong>{snapshot.project.name}</strong><small>{snapshot.project.root}</small></span>
          <dl>
            <div><dt>Lane</dt><dd>{snapshot.project.lane}</dd></div>
            <div><dt>Branch</dt><dd>{snapshot.project.git.branch ?? "Unavailable"}</dd></div>
            <div><dt>Commit</dt><dd><code>{snapshot.project.git.commit?.slice(0, 12) ?? "Unavailable"}</code></dd></div>
            <div><dt>Observed</dt><dd><time dateTime={snapshot.observedAt}>{formatObservedAt(snapshot.observedAt)}</time></dd></div>
          </dl>
        </footer>
      </div>
    </section>
  );
}
