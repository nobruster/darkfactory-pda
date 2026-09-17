import {
  ArrowClockwise,
  Broadcast,
  CaretDown,
  FlowArrow,
  GitBranch,
  Pulse,
  SidebarSimple,
  WarningOctagon,
  WarningCircle,
} from "@phosphor-icons/react";
import { useRef } from "react";
import type { TransportState, WorkspaceSnapshot } from "../types";
import { BrandMark } from "./BrandMark";

interface CommandBarProps {
  snapshot: WorkspaceSnapshot;
  transport: TransportState;
  loading: boolean;
  connectionPaused: boolean;
  leftExpanded: boolean;
  rightExpanded: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
  onRefresh: () => void;
  onOpenActivity: () => void;
}

export function CommandBar({
  snapshot,
  transport,
  loading,
  connectionPaused,
  leftExpanded,
  rightExpanded,
  onToggleLeft,
  onToggleRight,
  onRefresh,
  onOpenActivity,
}: CommandBarProps) {
  const pulseRef = useRef<HTMLDetailsElement | null>(null);
  const git = snapshot.project.git;
  const sourceLabel =
    snapshot.source === "fixture"
      ? "Replay fixture"
      : transport.stale
        ? "Last-good snapshot"
        : connectionPaused
          ? "Signal paused"
          : "Live workspace";
  const sourceTone =
    transport.stale || connectionPaused
      ? "warning"
      : snapshot.source === "fixture"
        ? "fixture"
        : "live";
  const sourceDetail =
    snapshot.source === "fixture"
      ? "Bundled replay data"
      : transport.stale
        ? "Last known CLI snapshot"
        : connectionPaused
          ? "Workspace stream paused"
          : "Current CLI snapshot";
  const frontier = snapshot.method.passes.find(
    (pass) => pass.id === snapshot.authorization.nextPassId,
  );
  const seriousIssues = snapshot.issues.filter(
    (issue) => issue.severity === "blocking" || issue.severity === "error",
  );
  const warningIssues = snapshot.issues.filter(
    (issue) => issue.severity === "warning",
  );
  const alertCount = seriousIssues.length + warningIssues.length;
  const frontierLabel = frontier
    ? `Pass ${frontier.order}: ${frontier.label}`
    : snapshot.authorization.state === "complete"
      ? "Descent complete"
      : "Frontier unresolved";

  function openActivity() {
    if (pulseRef.current) pulseRef.current.open = false;
    onOpenActivity();
  }

  return (
    <header className="command-bar">
      <div className="command-bar__leading">
        <button
          type="button"
          className="command-bar__panel-toggle command-bar__panel-toggle--left"
          onClick={onToggleLeft}
          aria-expanded={leftExpanded}
          aria-controls="cockpit-navigation"
          aria-label={leftExpanded ? "Collapse navigation" : "Expand navigation"}
          title={leftExpanded ? "Collapse navigation" : "Expand navigation"}
        >
          <SidebarSimple aria-hidden="true" />
        </button>
        <BrandMark />
      </div>

      <div className="command-bar__project">
        <strong>{snapshot.project.name}</strong>
        <span>
          <GitBranch aria-hidden="true" />
          {git.available
            ? `${git.branch ?? "detached"} / ${git.commit?.slice(0, 8) ?? "unknown"}`
            : "Git unavailable"}
          {git.dirty === true ? <em>local changes</em> : null}
        </span>
      </div>

      <div className="command-bar__actions">
        <details
          ref={pulseRef}
          className={`workspace-pulse workspace-pulse--${sourceTone} workspace-pulse--${snapshot.health.overall}`}
        >
          <summary aria-label={`Workspace pulse: ${sourceLabel}, ${alertCount} alerts`}>
            <span className="workspace-pulse__signal" aria-hidden="true">
              {alertCount > 0 ? (
                <WarningOctagon weight="fill" />
              ) : (
                <Broadcast weight="fill" />
              )}
            </span>
            <span className="workspace-pulse__copy" role="status" aria-live="polite">
              <strong>{alertCount > 0 ? `${alertCount} alerts` : "Workspace clear"}</strong>
              <small>{sourceLabel}</small>
            </span>
            <CaretDown className="workspace-pulse__caret" aria-hidden="true" />
          </summary>
          <div className="workspace-pulse__pane">
            <header>
              <span className="workspace-pulse__pane-icon">
                {alertCount > 0 ? (
                  <WarningOctagon weight="fill" aria-hidden="true" />
                ) : (
                  <Broadcast weight="fill" aria-hidden="true" />
                )}
              </span>
              <span>
                <strong>{alertCount > 0 ? "Workspace needs attention" : "Workspace is current"}</strong>
                <small>{snapshot.project.name}</small>
              </span>
            </header>
            <dl>
              <div>
                <dt><Broadcast weight="fill" aria-hidden="true" /> Source</dt>
                <dd>{sourceDetail}</dd>
              </div>
              <div>
                <dt><FlowArrow aria-hidden="true" /> Method</dt>
                <dd>{frontierLabel}</dd>
              </div>
              <div>
                <dt><WarningCircle weight="fill" aria-hidden="true" /> Attention</dt>
                <dd>{seriousIssues.length} critical, {warningIssues.length} warning</dd>
              </div>
            </dl>
            <p>{snapshot.authorization.rationale}</p>
            <button type="button" onClick={openActivity}>
              <Pulse aria-hidden="true" />
              Review activity and alerts
            </button>
          </div>
        </details>
        <button
          type="button"
          className="icon-button"
          onClick={onRefresh}
          disabled={loading}
          aria-label="Refresh workspace snapshot"
          title="Refresh workspace snapshot"
        >
          <ArrowClockwise
            className={loading ? "status-glyph--spin" : ""}
            aria-hidden="true"
          />
        </button>
        <button
          type="button"
          className="command-bar__panel-toggle command-bar__panel-toggle--right"
          onClick={onToggleRight}
          aria-expanded={rightExpanded}
          aria-controls="cockpit-inspector"
          aria-label={rightExpanded ? "Collapse inspector" : "Expand inspector"}
          title={rightExpanded ? "Collapse inspector" : "Expand inspector"}
        >
          <SidebarSimple mirrored aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
