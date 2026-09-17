import {
  ArrowCounterClockwise,
  CheckCircle,
  Gauge,
  Hourglass,
  WarningCircle,
} from "@phosphor-icons/react";
import type { EntityRef, ExecutionRun, WorkspaceSnapshot } from "../types";

interface RunsSurfaceProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

function RunGlyph({ state }: { state: string }) {
  const normalized = state.toLowerCase();
  if (["settled", "complete", "completed", "green", "pass"].includes(normalized)) {
    return <CheckCircle weight="fill" aria-hidden="true" />;
  }
  if (["red", "failed", "error", "blocked"].includes(normalized)) {
    return <WarningCircle weight="fill" aria-hidden="true" />;
  }
  if (["retry", "rework"].includes(normalized)) {
    return <ArrowCounterClockwise weight="bold" aria-hidden="true" />;
  }
  return <Hourglass weight="fill" aria-hidden="true" />;
}

function runTone(state: string) {
  const normalized = state.toLowerCase();
  if (["settled", "complete", "completed", "green", "pass"].includes(normalized)) {
    return "proven";
  }
  if (["red", "failed", "error", "blocked"].includes(normalized)) return "danger";
  return "active";
}

export function RunsSurface({
  snapshot,
  selected,
  onSelect,
}: RunsSurfaceProps) {
  const runsByTask = snapshot.execution.runs.reduce<
    Array<{ taskId: string; runs: ExecutionRun[] }>
  >((groups, run) => {
    const taskId = run.taskId ?? "unbound";
    const group = groups.find((item) => item.taskId === taskId);
    if (group) group.runs.push(run);
    else groups.push({ taskId, runs: [run] });
    return groups;
  }, []);

  return (
    <section className="surface surface--runs" aria-labelledby="runs-title">
      <header className="surface-header">
        <div>
          <span>Current observed execution state</span>
          <h1 id="runs-title">Runs</h1>
        </div>
        <div className="surface-header__stat">
          <Gauge aria-hidden="true" />
          <span>
            <strong>{snapshot.execution.runs.length}</strong>
            execution records
          </span>
        </div>
      </header>

      {snapshot.execution.availability === "unavailable" ? (
        <div className="surface-state">
          <Hourglass size={28} weight="fill" aria-hidden="true" />
          <strong>Execution state unavailable</strong>
          <p>The current snapshot does not expose execution records.</p>
        </div>
      ) : snapshot.execution.availability === "empty" ||
        snapshot.execution.runs.length === 0 ? (
        <div className="surface-state">
          <Hourglass size={28} weight="fill" aria-hidden="true" />
          <strong>No execution records observed</strong>
          <p>Current records appear after a task is bound and execution state is projected.</p>
        </div>
      ) : (
        <div className="run-lanes">
          {runsByTask.map((group) => {
            const task = snapshot.work.tasks.find(
              (candidate) => candidate.id === group.taskId,
            );
            return (
              <section key={group.taskId} className="run-lane">
                <header>
                  <span>{group.taskId === "unbound" ? "Unbound" : group.taskId}</span>
                  <strong>{task?.title ?? "Execution record"}</strong>
                  <small>{group.runs.length} current record{group.runs.length === 1 ? "" : "s"}</small>
                </header>
                <ol>
                  {group.runs.map((run, index) => {
                    const active =
                      selected?.kind === "run" && selected.id === run.id;
                    const tone = runTone(run.state);
                    const receipt = snapshot.receipts.items.find(
                      (item) =>
                        item.taskId === run.taskId &&
                        ["settled", "complete", "completed"].includes(
                          run.state.toLowerCase(),
                        ),
                    );
                    return (
                      <li key={run.id} className={`run-step run-step--${tone}`}>
                        <button
                          type="button"
                          className={active ? "is-selected" : ""}
                          onClick={() => onSelect({ kind: "run", id: run.id })}
                        >
                          <span className="run-step__index">{index + 1}</span>
                          <span className="run-step__glyph">
                            <RunGlyph state={run.state} />
                          </span>
                          <span className="run-step__copy">
                            <strong>
                              {run.attempt === null
                                ? "Attempt not recorded"
                                : `Attempt ${run.attempt}`}
                            </strong>
                            <small>{run.id}</small>
                          </span>
                          <span className="run-step__result">
                            <strong>{run.state}</strong>
                            <small>
                              {receipt
                                ? `${receipt.integrity} receipt`
                                : run.budgetIterations === null
                                  ? "budget unavailable"
                                  : `${run.budgetIterations} iteration budget`}
                            </small>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ol>
              </section>
            );
          })}
        </div>
      )}
    </section>
  );
}
