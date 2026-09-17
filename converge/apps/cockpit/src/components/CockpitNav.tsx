import {
  CaretDoubleLeft,
  CaretDoubleRight,
  ChatsCircle,
  ClockCounterClockwise,
  FlowArrow,
  GitBranch,
  Heartbeat,
  Kanban,
  Pulse,
  SealCheck,
  Stack,
  SquaresFour,
} from "@phosphor-icons/react";
import type { ComponentType } from "react";
import type { CockpitSurface, WorkspaceSnapshot } from "../types";

interface CockpitNavProps {
  snapshot: WorkspaceSnapshot;
  surface: CockpitSurface;
  expanded: boolean;
  onToggle: () => void;
  onSelect: (surface: CockpitSurface) => void;
}

interface NavItem {
  id: CockpitSurface;
  label: string;
  description: string;
  icon: ComponentType<{ size?: number; weight?: "regular" | "bold" | "fill" }>;
  count: (snapshot: WorkspaceSnapshot) => number | null;
  section: "Explain" | "Observe";
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "ask",
    label: "Ask",
    description: "Explain via ACP",
    icon: ChatsCircle,
    count: () => null,
    section: "Explain",
  },
  {
    id: "overview",
    label: "Overview",
    description: "Project at a glance",
    icon: SquaresFour,
    count: () => null,
    section: "Observe",
  },
  {
    id: "journey",
    label: "Journey",
    description: "Method and gates",
    icon: FlowArrow,
    count: (snapshot) => snapshot.method.passes.length,
    section: "Observe",
  },
  {
    id: "decompose",
    label: "Decompose",
    description: "Seams, lanes, and legs",
    icon: GitBranch,
    count: (snapshot) => snapshot.decomposition.swimlanes.length,
    section: "Observe",
  },
  {
    id: "artifacts",
    label: "Artifacts",
    description: "Pass outputs and trace",
    icon: Stack,
    count: (snapshot) => snapshot.artifacts.length,
    section: "Observe",
  },
  {
    id: "work",
    label: "Work",
    description: "Tasks and frontier",
    icon: Kanban,
    count: (snapshot) => snapshot.work.stats.total,
    section: "Observe",
  },
  {
    id: "runs",
    label: "Runs",
    description: "Current execution state",
    icon: Pulse,
    count: (snapshot) =>
      snapshot.execution.availability === "available"
        ? snapshot.execution.runs.length
        : null,
    section: "Observe",
  },
  {
    id: "proof",
    label: "Docs",
    description: "Readable proof",
    icon: SealCheck,
    count: (snapshot) => snapshot.artifacts.length,
    section: "Observe",
  },
  {
    id: "activity",
    label: "Activity",
    description: "Signals and issues",
    icon: ClockCounterClockwise,
    count: (snapshot) => snapshot.signals.length + snapshot.issues.length,
    section: "Observe",
  },
  {
    id: "health",
    label: "Health",
    description: "Operational checks",
    icon: Heartbeat,
    count: (snapshot) => snapshot.health.checks.length,
    section: "Observe",
  },
];

export function CockpitNav({
  snapshot,
  surface,
  expanded,
  onToggle,
  onSelect,
}: CockpitNavProps) {
  return (
    <aside
      id="cockpit-navigation"
      className={`cockpit-nav ${expanded ? "cockpit-nav--expanded" : "cockpit-nav--collapsed"}`}
      aria-label="Cockpit views"
    >
      <div className="cockpit-nav__heading">
        <span>Cockpit</span>
        <button
          type="button"
          className="rail-toggle"
          onClick={onToggle}
          aria-expanded={expanded}
          aria-controls="cockpit-navigation"
          aria-label={expanded ? "Collapse navigation" : "Expand navigation"}
          title={expanded ? "Collapse navigation" : "Expand navigation"}
        >
          {expanded ? (
            <CaretDoubleLeft aria-hidden="true" />
          ) : (
            <CaretDoubleRight aria-hidden="true" />
          )}
        </button>
      </div>

      <nav className="cockpit-nav__items">
        {NAV_ITEMS.map((item, index) => {
          const Icon = item.icon;
          const count = item.count(snapshot);
          const active = item.id === surface;
          return (
            <div className="nav-item-group" key={item.id}>
              {expanded && (index === 0 || NAV_ITEMS[index - 1].section !== item.section) ? (
                <span className="nav-section-label">{item.section}</span>
              ) : null}
              <button
                type="button"
                className={`nav-item ${active ? "nav-item--active" : ""}`}
                onClick={() => onSelect(item.id)}
                aria-current={active ? "page" : undefined}
                title={expanded ? undefined : item.label}
              >
                <span className="nav-item__icon">
                  <Icon size={20} weight={active ? "fill" : "regular"} />
                </span>
                <span className="nav-item__copy">
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
                {count !== null ? <span className="nav-item__count">{count}</span> : null}
              </button>
            </div>
          );
        })}
      </nav>

      <div className="cockpit-nav__status">
        <span
          className={`health-beacon health-beacon--${snapshot.health.overall}`}
          aria-hidden="true"
        />
        <span>
          <strong>{snapshot.health.overall}</strong>
          <small>
            {snapshot.issues.length} issue{snapshot.issues.length === 1 ? "" : "s"}
          </small>
        </span>
      </div>
    </aside>
  );
}
