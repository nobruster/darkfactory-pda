import {
  CheckCircle,
  Info,
  Pulse,
  WarningCircle,
  XCircle,
} from "@phosphor-icons/react";
import type { EntityRef, WorkspaceSnapshot } from "../types";

interface HealthSurfaceProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

function HealthIcon({ status }: { status: string }) {
  if (status === "healthy") {
    return <CheckCircle weight="fill" aria-hidden="true" />;
  }
  if (status === "blocked") {
    return <XCircle weight="fill" aria-hidden="true" />;
  }
  if (status === "degraded") {
    return <WarningCircle weight="fill" aria-hidden="true" />;
  }
  return <Info weight="fill" aria-hidden="true" />;
}

export function HealthSurface({
  snapshot,
  selected,
  onSelect,
}: HealthSurfaceProps) {
  return (
    <section className="surface surface--health" aria-labelledby="health-title">
      <header className="surface-header">
        <div>
          <span>Operational confidence</span>
          <h1 id="health-title">Health</h1>
        </div>
        <div className={`health-summary health-summary--${snapshot.health.overall}`}>
          <Pulse weight="fill" aria-hidden="true" />
          <span>
            <strong>{snapshot.health.overall}</strong>
            workspace posture
          </span>
        </div>
      </header>

      <div className="health-layout">
        <section className="health-matrix" aria-labelledby="health-matrix-title">
          <header>
            <h2 id="health-matrix-title">Checks</h2>
            <span>{snapshot.health.checks.length} observed</span>
          </header>
          <div className="health-grid">
            {snapshot.health.checks.map((check) => (
              <button
                type="button"
                key={check.id}
                className={`health-cell health-cell--${check.status} ${
                  selected?.kind === "health" && selected.id === check.id
                    ? "is-selected"
                    : ""
                }`}
                onClick={() => onSelect({ kind: "health", id: check.id })}
              >
                <span className="health-cell__icon">
                  <HealthIcon status={check.status} />
                </span>
                <span className="health-cell__copy">
                  <strong>{check.component}</strong>
                  <small>{check.summary}</small>
                </span>
                <span className="health-cell__requirement">
                  {check.required ? "required" : "optional"}
                </span>
                <span className="health-cell__status">{check.status}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="issue-list" aria-labelledby="issue-list-title">
          <header>
            <h2 id="issue-list-title">Issues</h2>
            <span>{snapshot.issues.length} observed</span>
          </header>
          {snapshot.issues.length === 0 ? (
            <div className="inline-state">
              <CheckCircle aria-hidden="true" />
              No issues are attached to this snapshot.
            </div>
          ) : (
            snapshot.issues.map((issue) => (
              <button
                type="button"
                key={issue.id}
                className={`issue-row issue-row--${issue.severity} ${
                  selected?.kind === "issue" && selected.id === issue.id
                    ? "is-selected"
                    : ""
                }`}
                onClick={() => onSelect({ kind: "issue", id: issue.id })}
              >
                <span className="issue-row__severity">
                  <WarningCircle weight="fill" aria-hidden="true" />
                  {issue.severity}
                </span>
                <strong>{issue.message}</strong>
                <small>
                  {issue.code} / {issue.domain}
                </small>
              </button>
            ))
          )}
        </section>
      </div>
    </section>
  );
}
