import { useMemo, useState } from "react";
import {
  Clock,
  FunnelSimple,
  Info,
  Pulse,
  WarningCircle,
} from "@phosphor-icons/react";
import type {
  EntityRef,
  Issue,
  Signal,
  WorkspaceSnapshot,
} from "../types";

interface ActivitySurfaceProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}

type RecordTypeFilter = "all" | "signal" | "issue";
type SeverityFilter =
  | "all"
  | "info"
  | "success"
  | "warning"
  | "error"
  | "blocking";

type ActivityRecord =
  | {
      category: "signal";
      id: string;
      kind: Signal["kind"];
      severity: Signal["severity"];
      summary: string;
      occurredAt: string | null;
      entity?: EntityRef;
      artifactIds: string[];
      sequence: number;
    }
  | {
      category: "issue";
      id: string;
      kind: Issue["domain"];
      severity: Issue["severity"];
      summary: string;
      occurredAt: null;
      entity?: EntityRef;
      artifactIds: string[];
      sequence: number;
      code: string;
      remediation?: string;
    };

const SEVERITY_OPTIONS: Array<{
  value: SeverityFilter;
  label: string;
}> = [
  { value: "all", label: "All severities" },
  { value: "blocking", label: "Blocking" },
  { value: "error", label: "Error" },
  { value: "warning", label: "Warning" },
  { value: "success", label: "Success" },
  { value: "info", label: "Info" },
];

function recordReference(record: ActivityRecord): EntityRef {
  return { kind: record.category, id: record.id };
}

function sameEntity(left: EntityRef | null, right: EntityRef) {
  return left?.kind === right.kind && left.id === right.id;
}

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString();
}

function severityRank(severity: ActivityRecord["severity"]) {
  return {
    blocking: 0,
    error: 1,
    warning: 2,
    success: 3,
    info: 4,
  }[severity];
}

function activityRecords(snapshot: WorkspaceSnapshot): ActivityRecord[] {
  const signals: ActivityRecord[] = snapshot.signals.map((signal, index) => ({
    category: "signal",
    id: signal.id,
    kind: signal.kind,
    severity: signal.severity,
    summary: signal.summary,
    occurredAt: signal.occurredAt,
    entity: signal.entity,
    artifactIds: signal.artifactIds,
    sequence: index,
  }));
  const issues: ActivityRecord[] = snapshot.issues.map((issue, index) => ({
    category: "issue",
    id: issue.id,
    kind: issue.domain,
    severity: issue.severity,
    summary: issue.message,
    occurredAt: null,
    entity: issue.entity,
    artifactIds: issue.artifactIds,
    sequence: snapshot.signals.length + index,
    code: issue.code,
    remediation: issue.remediation,
  }));

  return [...signals, ...issues];
}

function ActivityRecordCard({
  record,
  selected,
  onSelect,
}: {
  record: ActivityRecord;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}) {
  const reference = recordReference(record);
  const titleId = `activity-record-${record.category}-${record.id}`;

  return (
    <article
      className={`activity-record activity-record--${record.category} activity-record--${record.severity} ${
        sameEntity(selected, reference) ? "is-selected" : ""
      }`}
      aria-labelledby={titleId}
    >
      <div className="activity-record__main">
        <span className="activity-record__tone" aria-hidden="true" />
        <button
          type="button"
          className="activity-record__select"
          onClick={() => onSelect(reference)}
          aria-pressed={sameEntity(selected, reference)}
          aria-label={`Inspect ${record.category} ${record.summary}`}
        >
          <span className="activity-record__identity">
            <span>
              <strong>{record.category === "issue" ? "Issue" : "Signal"}</strong>
              <small>{record.kind}</small>
            </span>
            <span className={`activity-record__severity is-${record.severity}`}>
              {record.severity}
            </span>
          </span>
          <strong id={titleId} className="activity-record__summary">
            {record.summary}
          </strong>
          {record.category === "issue" ? (
            <code className="activity-record__code">{record.code}</code>
          ) : null}
        </button>
        {record.category === "signal" && record.occurredAt ? (
          <div className="activity-record__time">
            <Clock aria-hidden="true" />
            <time dateTime={record.occurredAt}>
              {formatTimestamp(record.occurredAt)}
            </time>
          </div>
        ) : null}
      </div>

      <footer className="activity-record__footer">
        <span>
          {record.artifactIds.length} evidence reference
          {record.artifactIds.length === 1 ? "" : "s"}
        </span>
        {record.entity ? (
          <button
            type="button"
            className="activity-record__entity"
            onClick={() => onSelect(record.entity as EntityRef)}
            aria-label={`Inspect related ${record.entity.kind} ${record.entity.id}`}
          >
            Related {record.entity.kind}
            <code>{record.entity.id}</code>
          </button>
        ) : (
          <span className="activity-record__unlinked">
            No entity reference recorded
          </span>
        )}
      </footer>

      {record.category === "issue" && record.remediation ? (
        <p className="activity-record__remediation">
          <strong>Recorded remediation</strong>
          {record.remediation}
        </p>
      ) : null}
    </article>
  );
}

function ActivityRecordCollection({
  records,
  ordered,
  selected,
  onSelect,
}: {
  records: ActivityRecord[];
  ordered?: boolean;
  selected: EntityRef | null;
  onSelect: (selection: EntityRef) => void;
}) {
  const items = records.map((record) => (
    <li key={`${record.category}:${record.id}`}>
      <ActivityRecordCard
        record={record}
        selected={selected}
        onSelect={onSelect}
      />
    </li>
  ));

  return ordered ? (
    <ol className="activity-list" aria-label="Timestamped snapshot signals">
      {items}
    </ol>
  ) : (
    <ul className="activity-list" aria-label="Snapshot records">
      {items}
    </ul>
  );
}

export function ActivitySurface({
  snapshot,
  selected,
  onSelect,
}: ActivitySurfaceProps) {
  const [recordType, setRecordType] = useState<RecordTypeFilter>("all");
  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const records = useMemo(() => activityRecords(snapshot), [snapshot]);
  const visibleRecords = records.filter(
    (record) =>
      (recordType === "all" || record.category === recordType) &&
      (severity === "all" || record.severity === severity),
  );
  const visibleIssues = visibleRecords
    .filter((record) => record.category === "issue")
    .sort(
      (left, right) =>
        severityRank(left.severity) - severityRank(right.severity) ||
        left.sequence - right.sequence,
    );
  const visibleTimedSignals = visibleRecords
    .filter(
      (record) => record.category === "signal" && record.occurredAt !== null,
    )
    .sort(
      (left, right) =>
        Date.parse(right.occurredAt as string) -
        Date.parse(left.occurredAt as string),
    );
  const visibleUntimedSignals = visibleRecords
    .filter(
      (record) => record.category === "signal" && record.occurredAt === null,
    )
    .sort((left, right) => left.sequence - right.sequence);
  const attentionCount = records.filter(
    (record) => record.severity === "blocking" || record.severity === "error",
  ).length;
  const evidenceLinkedCount = records.filter(
    (record) => record.artifactIds.length > 0,
  ).length;
  const timedSignalCount = snapshot.signals.filter(
    (signal) => signal.occurredAt !== null,
  ).length;

  return (
    <section
      className="surface surface--activity"
      aria-labelledby="activity-title"
    >
      <header className="surface-header activity-header">
        <div>
          <span>Current snapshot projection</span>
          <h1 id="activity-title">Activity</h1>
        </div>
        <div className="activity-header__summary">
          <Pulse weight="fill" aria-hidden="true" />
          <span>
            <strong>{records.length}</strong>
            bounded records
          </span>
        </div>
      </header>

      <div className="activity-toolbar">
        <div className="activity-boundary" role="note">
          <Info weight="fill" aria-hidden="true" />
          <p>
            Current WorkspaceSnapshot 3.0 only · bounded observation, not a
            durable audit history.
          </p>
        </div>

        <form
          className="activity-filters"
          aria-label="Filter bounded activity"
          onSubmit={(event) => event.preventDefault()}
        >
          <FunnelSimple aria-hidden="true" />
          <label htmlFor="activity-record-type">
            <span>Record type</span>
            <select
              id="activity-record-type"
              value={recordType}
              onChange={(event) =>
                setRecordType(event.target.value as RecordTypeFilter)
              }
            >
              <option value="all">Signals and issues</option>
              <option value="signal">Signals</option>
              <option value="issue">Issues</option>
            </select>
          </label>
          <label htmlFor="activity-severity">
            <span>Severity</span>
            <select
              id="activity-severity"
              value={severity}
              onChange={(event) =>
                setSeverity(event.target.value as SeverityFilter)
              }
            >
              {SEVERITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <output className="activity-filters__result" aria-live="polite">
            {visibleRecords.length} of {records.length} shown
          </output>
        </form>
      </div>

      <div className="activity-summary" aria-label="Activity snapshot summary">
        <span>
          <strong>{attentionCount}</strong>
          blocking or error
        </span>
        <span>
          <strong>{evidenceLinkedCount}</strong>
          evidence-linked
        </span>
        <span>
          <strong>
            {timedSignalCount}/{snapshot.signals.length}
          </strong>
          timed signals
        </span>
      </div>

      {visibleRecords.length > 0 ? (
        <div className="activity-feed">
          {visibleIssues.length > 0 ? (
            <section className="activity-group" aria-labelledby="activity-issues-title">
              <header>
                <span className="activity-group__marker is-attention" aria-hidden="true" />
                <div>
                  <h2 id="activity-issues-title">Needs attention</h2>
                  <p>Issues ranked by severity; issues do not carry timestamps.</p>
                </div>
                <strong>{visibleIssues.length}</strong>
              </header>
              <ActivityRecordCollection
                records={visibleIssues}
                selected={selected}
                onSelect={onSelect}
              />
            </section>
          ) : null}

          {visibleTimedSignals.length > 0 ? (
            <section className="activity-group" aria-labelledby="activity-timed-title">
              <header>
                <span className="activity-group__marker is-signal" aria-hidden="true" />
                <div>
                  <h2 id="activity-timed-title">Timed observations</h2>
                  <p>Signals ordered newest first from recorded timestamps.</p>
                </div>
                <strong>{visibleTimedSignals.length}</strong>
              </header>
              <ActivityRecordCollection
                records={visibleTimedSignals}
                ordered
                selected={selected}
                onSelect={onSelect}
              />
            </section>
          ) : null}

          {visibleUntimedSignals.length > 0 ? (
            <section className="activity-group" aria-labelledby="activity-untimed-title">
              <header>
                <span className="activity-group__marker is-signal" aria-hidden="true" />
                <div>
                  <h2 id="activity-untimed-title">Snapshot-order signals</h2>
                  <p>Timestamps unavailable · canonical snapshot order preserved.</p>
                </div>
                <strong>{visibleUntimedSignals.length}</strong>
              </header>
              <ActivityRecordCollection
                records={visibleUntimedSignals}
                selected={selected}
                onSelect={onSelect}
              />
            </section>
          ) : null}
        </div>
      ) : records.length === 0 ? (
        <div className="surface-state activity-empty" role="status">
          <Pulse size={28} weight="fill" aria-hidden="true" />
          <strong>No bounded activity observed</strong>
          <p>The current snapshot contains no signals or issues.</p>
        </div>
      ) : (
        <div className="surface-state activity-empty" role="status">
          <WarningCircle size={28} weight="fill" aria-hidden="true" />
          <strong>No records match these filters</strong>
          <p>Change the record type or severity to restore observed records.</p>
        </div>
      )}
    </section>
  );
}
