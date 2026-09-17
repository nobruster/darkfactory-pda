import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  ArrowsSplit,
  Cpu,
  GitBranch,
  Graph,
  ListBullets,
  LockKey,
  RocketLaunch,
  SealCheck,
  Stack,
} from "@phosphor-icons/react";
import type { EntityRef, WorkTask, WorkspaceSnapshot } from "../types";
import { WorkGraph, type WorkPresentation } from "./WorkGraph";

interface WorkSurfaceProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

type WorkView = "graph" | "list";

function isMobileViewport() {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches;
}

function taskDepth(
  task: WorkTask,
  byId: ReadonlyMap<string, WorkTask>,
  visiting = new Set<string>(),
): number {
  if (task.dependsOn.length === 0 || visiting.has(task.id)) return 0;
  const next = new Set(visiting);
  next.add(task.id);
  return 1 + Math.max(0, ...task.dependsOn.map((id) => {
    const dependency = byId.get(id);
    return dependency ? taskDepth(dependency, byId, next) : 0;
  }));
}

function buildPresentation(snapshot: WorkspaceSnapshot): Record<string, WorkPresentation> {
  const byId = new Map(snapshot.work.tasks.map((task) => [task.id, task] as const));
  const depths = new Map(snapshot.work.tasks.map((task) => [task.id, taskDepth(task, byId)] as const));
  const depthCounts = new Map<number, number>();
  for (const depth of depths.values()) depthCounts.set(depth, (depthCounts.get(depth) ?? 0) + 1);

  return Object.fromEntries(snapshot.work.tasks.map((task) => {
    const depth = depths.get(task.id) ?? 0;
    const latestRun = [...snapshot.execution.runs].reverse().find((run) => run.taskId === task.id);
    return [task.id, {
      engine: latestRun?.runtime.primaryRuntime ?? "unassigned",
      topology: (depthCounts.get(depth) ?? 0) > 1 ? "parallel branch" : "serial path",
      depth,
    } satisfies WorkPresentation];
  }));
}

function WorkRow({
  task,
  selected,
  presentation,
  onSelect,
}: {
  task: WorkTask;
  selected: boolean;
  presentation: WorkPresentation;
  onSelect: (selection: EntityRef) => void;
}) {
  return (
    <button
      type="button"
      className={`work-row work-row--mastery ${selected ? "work-row--selected" : ""}`}
      onClick={() => onSelect({ kind: "task", id: task.id })}
      aria-pressed={selected}
    >
      <span className={`state-mark state-mark--${task.status}`} aria-hidden="true" />
      <span className="work-row__copy">
        <strong>{task.title}</strong>
        <code>{task.id}</code>
        <span className="work-row__tags">
          <em><GitBranch aria-hidden="true" />{presentation.topology}</em>
          <em><Cpu aria-hidden="true" />Engine: {presentation.engine}</em>
          <em>Agent: {task.agent ?? "unassigned"}</em>
          <em>{task.priority ?? "No priority"}</em>
          <em>{task.effort ?? "No effort"}</em>
        </span>
      </span>
      <span className="work-row__state">
        <strong>{task.dispatchable ? "Dispatchable" : task.status.replaceAll("_", " ")}</strong>
        <small>{task.dependsOn.length} dependencies</small>
      </span>
      <ArrowRight aria-hidden="true" />
    </button>
  );
}

export function WorkSurface({ snapshot, selected, onSelect }: WorkSurfaceProps) {
  const [mobile, setMobile] = useState(isMobileViewport);
  const [view, setView] = useState<WorkView>(() => isMobileViewport() ? "list" : "graph");
  useEffect(() => {
    const media = window.matchMedia("(max-width: 767px)");
    const syncView = () => {
      setMobile(media.matches);
      if (media.matches) setView("list");
    };
    media.addEventListener("change", syncView);
    return () => media.removeEventListener("change", syncView);
  }, []);

  const frontier = useMemo(
    () => snapshot.work.frontier.taskIds
      .map((id) => snapshot.work.tasks.find((task) => task.id === id))
      .filter((task): task is WorkTask => Boolean(task)),
    [snapshot.work.frontier.taskIds, snapshot.work.tasks],
  );
  const completed = snapshot.work.tasks.filter((task) => task.status === "done");
  const backlog = snapshot.work.tasks.filter(
    (task) => task.status !== "done" && !snapshot.work.frontier.taskIds.includes(task.id),
  );
  const presentation = useMemo(() => buildPresentation(snapshot), [snapshot]);
  const legCount = snapshot.decomposition.legs.length;
  const taskCount = snapshot.work.stats.total;
  const gap = Math.max(0, legCount - taskCount);

  return (
    <section className="surface surface--work surface--work-mastery" aria-labelledby="work-title">
      <header className="surface-header work-header-mastery">
        <div>
          <span>Canonical Task-Spec inventory</span>
          <h1 id="work-title">Work</h1>
        </div>
        <div className="segmented-control" aria-label="Work presentation">
          <button type="button" className={view === "graph" ? "is-active" : ""} onClick={() => setView("graph")} aria-pressed={view === "graph"} disabled={mobile} title={mobile ? "Graph is available on wider screens" : undefined}>
            <Graph aria-hidden="true" />Graph
          </button>
          <button type="button" className={view === "list" ? "is-active" : ""} onClick={() => setView("list")} aria-pressed={view === "list"}>
            <ListBullets aria-hidden="true" />List
          </button>
        </div>
      </header>

      {snapshot.work.availability === "unavailable" ? (
        <div className="surface-state">
          <LockKey size={28} weight="fill" aria-hidden="true" />
          <strong>Work inventory unavailable</strong>
          <p>The snapshot did not expose a canonical task graph.</p>
        </div>
      ) : snapshot.work.availability === "empty" || snapshot.work.tasks.length === 0 ? (
        <div className="surface-state">
          <RocketLaunch size={28} weight="fill" aria-hidden="true" />
          <strong>No work has been decomposed</strong>
          <p>Tasking will populate this view when canonical tasks exist.</p>
        </div>
      ) : (
        <>
          <section className="work-coverage" aria-labelledby="work-coverage-title">
            <div className="work-coverage__relationship">
              <span><GitBranch aria-hidden="true" /><strong>{legCount}</strong><small>delivery legs</small></span>
              <ArrowRight aria-hidden="true" />
              <span><Stack aria-hidden="true" /><strong>{taskCount}</strong><small>Task-Specs</small></span>
            </div>
            <div className="work-coverage__copy">
              <h2 id="work-coverage-title">Tasking is a separate inventory</h2>
              <p>
                This snapshot has {legCount} decomposition legs and {taskCount} canonical tasks. {gap > 0 ? `${gap} legs do not have a published one-to-one task mapping.` : "Every count aligns, but the snapshot still does not claim a one-to-one mapping."}
              </p>
            </div>
            <dl className="work-coverage__stats">
              <div><dt>At frontier</dt><dd>{snapshot.work.frontier.taskIds.length}</dd></div>
              <div><dt>Ready</dt><dd>{snapshot.work.stats.ready}</dd></div>
              <div><dt>Blocked</dt><dd>{snapshot.work.stats.blocked}</dd></div>
              <div><dt>Done</dt><dd>{snapshot.work.stats.done}</dd></div>
            </dl>
          </section>

          <div className="work-legend" aria-label="Work metadata legend">
            <span><ArrowsSplit aria-hidden="true" />Topology is derived from dependency depth</span>
            <span><Cpu aria-hidden="true" />Engine comes from an observed run, otherwise unassigned</span>
          </div>

          {view === "graph" && !mobile ? (
            <WorkGraph
              tasks={snapshot.work.tasks}
              frontierIds={snapshot.work.frontier.taskIds}
              presentation={presentation}
              selected={selected}
              onSelect={onSelect}
            />
          ) : (
            <div className="work-list-groups work-list-groups--mastery">
              <section>
                <header><RocketLaunch weight="fill" aria-hidden="true" /><span><strong>Frontier</strong><small>{frontier.length} dispatchable</small></span></header>
                <div>{frontier.length > 0 ? frontier.map((task) => <WorkRow key={task.id} task={task} presentation={presentation[task.id]} selected={selected?.kind === "task" && selected.id === task.id} onSelect={onSelect} />) : <p className="work-group-empty">No task is currently dispatchable.</p>}</div>
              </section>
              <section>
                <header><LockKey weight="fill" aria-hidden="true" /><span><strong>Backlog</strong><small>{backlog.length} dependency gated</small></span></header>
                <div>{backlog.length > 0 ? backlog.map((task) => <WorkRow key={task.id} task={task} presentation={presentation[task.id]} selected={selected?.kind === "task" && selected.id === task.id} onSelect={onSelect} />) : <p className="work-group-empty">No dependency-gated task is recorded.</p>}</div>
              </section>
              <section>
                <header><SealCheck weight="fill" aria-hidden="true" /><span><strong>Completed</strong><small>{completed.length} settled</small></span></header>
                <div>{completed.length > 0 ? completed.map((task) => <WorkRow key={task.id} task={task} presentation={presentation[task.id]} selected={selected?.kind === "task" && selected.id === task.id} onSelect={onSelect} />) : <p className="work-group-empty">No Task-Spec has reached done in this snapshot.</p>}</div>
              </section>
            </div>
          )}
        </>
      )}
    </section>
  );
}
