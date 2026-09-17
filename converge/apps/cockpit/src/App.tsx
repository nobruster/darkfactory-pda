import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { CloudSlash, SpinnerGap, WarningCircle } from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { ArtifactViewer } from "./components/ArtifactViewer";
import { ActivitySurface } from "./components/ActivitySurface";
import { AskSurface } from "./components/AskSurface";
import { useAskConversations } from "./ask/useAskConversations";
import { ArtifactsSurface } from "./components/ArtifactsSurface";
import { CockpitNav } from "./components/CockpitNav";
import { CommandBar } from "./components/CommandBar";
import { DecomposeSurface } from "./components/DecomposeSurface";
import { HealthSurface } from "./components/HealthSurface";
import { InspectorPanel } from "./components/InspectorPanel";
import { LineageCanvas } from "./components/LineageCanvas";
import { MobileNav } from "./components/MobileNav";
import { OverviewSurface } from "./components/OverviewSurface";
import { ProofSurface } from "./components/ProofSurface";
import { RunsSurface } from "./components/RunsSurface";
import { WorkSurface } from "./components/WorkSurface";
import { fallbackSnapshot } from "./data/fallback";
import { entityExists } from "./lib/entities";
import { decodeSnapshotPayload } from "./lib/snapshot";
import type {
  ArtifactRef,
  CockpitSurface,
  EntityRef,
  InspectorTab,
  SnapshotEnvelope,
  TransportState,
  WorkspaceSnapshot,
} from "./types";

const PANEL_KEYS = {
  left: "converge-cockpit:left-expanded",
  right: "converge-cockpit:right-expanded",
} as const;

function readPanelPreference(key: string) {
  try {
    const value = window.localStorage.getItem(key);
    return value === null ? null : value === "true";
  } catch {
    return null;
  }
}

function panelStateForViewport() {
  if (typeof window === "undefined") return { left: false, right: false };
  const desktop = window.matchMedia("(min-width: 1280px)").matches;
  if (!desktop) return { left: false, right: false };

  const cinema = window.matchMedia("(min-width: 1600px)").matches;
  return {
    left: readPanelPreference(PANEL_KEYS.left) ?? cinema,
    right: readPanelPreference(PANEL_KEYS.right) ?? true,
  };
}

function persistPanelPreference(key: string, value: boolean) {
  try {
    window.localStorage.setItem(key, String(value));
  } catch {
    // Panel preferences are optional. Operational state never depends on them.
  }
}

function initialSelection(snapshot: WorkspaceSnapshot): EntityRef | null {
  const passId = snapshot.method.activePassId ?? snapshot.method.passes[0]?.id;
  return passId ? { kind: "pass", id: passId } : null;
}

function selectionForSurface(
  snapshot: WorkspaceSnapshot,
  surface: CockpitSurface,
): EntityRef | null {
  if (surface === "ask") return initialSelection(snapshot);
  if (surface === "overview") return initialSelection(snapshot);
  if (surface === "journey") return initialSelection(snapshot);
  if (surface === "decompose") {
    if (snapshot.decomposition.availability !== "available") return null;
    const laneId = snapshot.decomposition.swimlanes[0]?.id;
    if (laneId) return { kind: "swimlane", id: laneId };
    const legId = snapshot.decomposition.legs[0]?.id;
    return legId ? { kind: "leg", id: legId } : null;
  }
  if (surface === "artifacts") {
    const id =
      snapshot.method.passes.find((pass) => pass.artifactIds.length > 0)?.id ??
      snapshot.method.passes[0]?.id ??
      null;
    return id ? { kind: "pass", id } : null;
  }
  if (surface === "work") {
    const id =
      snapshot.work.frontier.taskIds[0] ?? snapshot.work.tasks[0]?.id ?? null;
    return id ? { kind: "task", id } : null;
  }
  if (surface === "runs") {
    const id = snapshot.execution.runs.at(-1)?.id ?? null;
    return id ? { kind: "run", id } : null;
  }
  if (surface === "proof") {
    const receiptId = snapshot.receipts.items.at(-1)?.id;
    if (receiptId) return { kind: "receipt", id: receiptId };
    const artifactId = snapshot.artifacts[0]?.id;
    return artifactId ? { kind: "artifact", id: artifactId } : null;
  }
  if (surface === "activity") {
    const signalId = snapshot.signals[0]?.id;
    if (signalId) return { kind: "signal", id: signalId };
    const issueId = snapshot.issues[0]?.id;
    return issueId ? { kind: "issue", id: issueId } : null;
  }
  const issueId = snapshot.issues.find(
    (issue) => issue.severity === "blocking" || issue.severity === "error",
  )?.id;
  if (issueId) return { kind: "issue", id: issueId };
  const checkId = snapshot.health.checks[0]?.id;
  return checkId ? { kind: "health", id: checkId } : null;
}

function isNarrowViewport() {
  return window.matchMedia("(max-width: 1279px)").matches;
}

export function App() {
  const reduceMotion = useReducedMotion();
  const [envelope, setEnvelope] = useState<SnapshotEnvelope>({
    snapshot: fallbackSnapshot,
    transport: {
      stale: false,
      servedAt: fallbackSnapshot.observedAt,
    },
  });
  const [surface, setSurface] = useState<CockpitSurface>("overview");
  const [selected, setSelected] = useState<EntityRef | null>(() =>
    initialSelection(fallbackSnapshot),
  );
  const [inspectorTab, setInspectorTab] =
    useState<InspectorTab>("overview");
  const [leftExpanded, setLeftExpanded] = useState(
    () => panelStateForViewport().left,
  );
  const [rightExpanded, setRightExpanded] = useState(
    () => panelStateForViewport().right,
  );
  const [artifact, setArtifact] = useState<ArtifactRef | null>(null);
  // Ask conversations are owned here so leaving the Ask surface no longer
  // unmounts and discards the transcript.
  const askConversations = useAskConversations();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [connectionPaused, setConnectionPaused] = useState(false);
  const hydratedWorkspaceRef = useRef(false);
  const surfaceRef = useRef<CockpitSurface>(surface);
  surfaceRef.current = surface;

  const snapshot = envelope.snapshot;
  const transport = envelope.transport;

  const loadSnapshot = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/snapshot", {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`Snapshot unavailable (${response.status})`);
      }
      const next = decodeSnapshotPayload(await response.json());
      if (!next) throw new Error("WorkspaceSnapshot 3.0 contract mismatch");
      if (
        next.snapshot.source === "workspace" &&
        !hydratedWorkspaceRef.current
      ) {
        hydratedWorkspaceRef.current = true;
        setSelected(selectionForSurface(next.snapshot, surfaceRef.current));
      }
      setEnvelope(next);
      setLoadError(null);
      setConnectionPaused(false);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Snapshot unavailable";
      setLoadError(message);
      setEnvelope((current) => ({
        ...current,
        transport: {
          stale: true,
          servedAt: new Date().toISOString(),
          error: {
            code: "CLIENT_REFRESH_FAILED",
            message,
          },
        },
      }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSnapshot();
    const source = new EventSource("/api/events");
    const receive = (event: MessageEvent<string>) => {
      try {
        const next = decodeSnapshotPayload(JSON.parse(event.data) as unknown);
        if (!next) return;
        if (
          next.snapshot.source === "workspace" &&
          !hydratedWorkspaceRef.current
        ) {
          hydratedWorkspaceRef.current = true;
          setSelected(selectionForSurface(next.snapshot, surfaceRef.current));
        }
        setEnvelope(next);
        setLoadError(null);
        setConnectionPaused(false);
      } catch {
        setConnectionPaused(true);
      }
    };
    source.onmessage = receive;
    source.addEventListener("snapshot", receive as EventListener);
    source.onerror = () => setConnectionPaused(true);
    return () => source.close();
  }, [loadSnapshot]);

  useEffect(() => {
    setSelected((current) =>
      entityExists(snapshot, current) ? current : initialSelection(snapshot),
    );
    setArtifact((current) =>
      current &&
      snapshot.artifacts.some(
        (candidate) =>
          candidate.id === current.id && candidate.sha256 === current.sha256,
      )
        ? current
        : null,
    );
  }, [snapshot]);

  useEffect(() => {
    const closeDrawers = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || !isNarrowViewport()) return;
      setLeftExpanded(false);
      setRightExpanded(false);
    };
    window.addEventListener("keydown", closeDrawers);
    return () => window.removeEventListener("keydown", closeDrawers);
  }, []);

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 1280px)");
    const cinema = window.matchMedia("(min-width: 1600px)");
    const syncPanels = () => {
      const next = panelStateForViewport();
      setLeftExpanded(next.left);
      setRightExpanded(next.right);
    };
    desktop.addEventListener("change", syncPanels);
    cinema.addEventListener("change", syncPanels);
    return () => {
      desktop.removeEventListener("change", syncPanels);
      cinema.removeEventListener("change", syncPanels);
    };
  }, []);

  const toggleLeft = useCallback(() => {
    setLeftExpanded((current) => {
      const next = !current;
      persistPanelPreference(PANEL_KEYS.left, next);
      if (next && isNarrowViewport()) setRightExpanded(false);
      return next;
    });
  }, []);

  const toggleRight = useCallback(() => {
    setRightExpanded((current) => {
      const next = !current;
      persistPanelPreference(PANEL_KEYS.right, next);
      if (next && isNarrowViewport()) setLeftExpanded(false);
      return next;
    });
  }, []);

  const selectSurface = useCallback(
    (nextSurface: CockpitSurface) => {
      setSurface(nextSurface);
      if (nextSurface !== "ask") {
        const nextSelection = selectionForSurface(snapshot, nextSurface);
        setSelected(nextSelection);
      }
      setInspectorTab("overview");
      if (nextSurface === "ask") {
        setRightExpanded(false);
      } else if (nextSurface === "artifacts") {
        setRightExpanded(false);
      } else if (nextSurface === "proof" && isNarrowViewport()) {
        setRightExpanded(false);
      } else if (nextSurface === "journey" && !isNarrowViewport()) {
        setRightExpanded(true);
      }
      if (isNarrowViewport()) setLeftExpanded(false);
    },
    [snapshot],
  );

  const selectEntity = useCallback(
    (next: EntityRef) => {
      setSelected(next);
      setInspectorTab("overview");
      if (surface === "proof" && isNarrowViewport()) {
        setRightExpanded(false);
        return;
      }
      if (isNarrowViewport() || next.kind === "pass") {
        setRightExpanded(true);
        if (isNarrowViewport()) setLeftExpanded(false);
      }
    },
    [surface],
  );

  const closeDrawers = useCallback(() => {
    setLeftExpanded(false);
    setRightExpanded(false);
  }, []);

  const closeArtifact = useCallback(() => setArtifact(null), []);

  const transportMessage = useMemo(() => {
    if (loading) {
      return {
        tone: "loading",
        icon: SpinnerGap,
        title: "Refreshing workspace",
        message: "The current projection remains visible while Cockpit reads `cvg`.",
      };
    }
    if (loadError && snapshot.source === "fixture") {
      return {
        tone: "error",
        icon: CloudSlash,
        title: "Live workspace unavailable",
        message: "Showing the bundled replay fixture. No live state is being claimed.",
      };
    }
    if (transport.stale) {
      return {
        tone: "warning",
        icon: WarningCircle,
        title: "Last-good snapshot",
        message:
          transport.error?.message ??
          "The latest refresh failed. Values may no longer match the workspace.",
      };
    }
    if (connectionPaused) {
      return {
        tone: "warning",
        icon: WarningCircle,
        title: "Live signal paused",
        message: "Manual refresh remains available.",
      };
    }
    return null;
  }, [connectionPaused, loadError, loading, snapshot.source, transport]);
  const TransportIcon = transportMessage?.icon;

  return (
    <motion.main
      className={`cockpit-shell ${
        leftExpanded ? "cockpit-shell--left-open" : "cockpit-shell--left-closed"
      } ${
        rightExpanded ? "cockpit-shell--right-open" : "cockpit-shell--right-closed"
      } cockpit-shell--surface-${surface}`}
        initial={reduceMotion ? undefined : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.28 }}
    >
      <CommandBar
        snapshot={snapshot}
        transport={transport}
        loading={loading}
        connectionPaused={connectionPaused}
        leftExpanded={leftExpanded}
        rightExpanded={rightExpanded}
        onToggleLeft={toggleLeft}
        onToggleRight={toggleRight}
        onRefresh={() => void loadSnapshot()}
        onOpenActivity={() => selectSurface("activity")}
      />

      <div className="cockpit-workspace">
        <CockpitNav
          snapshot={snapshot}
          surface={surface}
          expanded={leftExpanded}
          onToggle={toggleLeft}
          onSelect={selectSurface}
        />

        <section className="cockpit-center" aria-label={`${surface} workspace`}>
          {transportMessage ? (
            <div
              className={`transport-notice transport-notice--${transportMessage.tone}`}
              role={transportMessage.tone === "error" ? "alert" : "status"}
            >
              {TransportIcon ? (
                <TransportIcon
                className={
                  transportMessage.tone === "loading"
                    ? "status-glyph--spin"
                    : ""
                }
                weight="fill"
                aria-hidden="true"
                />
              ) : null}
              <span>
                <strong>{transportMessage.title}</strong>
                <small>{transportMessage.message}</small>
              </span>
            </div>
          ) : null}

          {surface === "journey" ? (
            <LineageCanvas
              snapshot={snapshot}
              selected={selected}
              onSelect={selectEntity}
            />
          ) : null}
          {surface === "overview" ? (
            <OverviewSurface
              snapshot={snapshot}
              selected={selected}
              onSelect={selectEntity}
            />
          ) : null}
          {surface === "ask" ? (
            <AskSurface
              snapshot={snapshot}
              selected={selected}
              conversations={askConversations}
            />
          ) : null}
          {surface === "decompose" ? (
            <DecomposeSurface
              snapshot={snapshot}
              selected={selected}
              onSelect={selectEntity}
            />
          ) : null}
          {surface === "artifacts" ? (
            <ArtifactsSurface
              snapshot={snapshot}
              selected={selected}
              onSelect={selectEntity}
              onOpenArtifact={setArtifact}
            />
          ) : null}
          {surface === "work" ? (
            <WorkSurface
              snapshot={snapshot}
              selected={selected}
              onSelect={selectEntity}
            />
          ) : null}
          {surface === "runs" ? (
            <RunsSurface
              snapshot={snapshot}
              selected={selected}
              onSelect={selectEntity}
            />
          ) : null}
          {surface === "proof" ? (
            <ProofSurface
              snapshot={snapshot}
              selected={selected}
              onSelect={selectEntity}
              onOpenArtifact={setArtifact}
            />
          ) : null}
          {surface === "health" ? (
            <HealthSurface
              snapshot={snapshot}
              selected={selected}
              onSelect={selectEntity}
            />
          ) : null}
          {surface === "activity" ? (
            <ActivitySurface
              snapshot={snapshot}
              selected={selected}
              onSelect={selectEntity}
            />
          ) : null}
        </section>

        <InspectorPanel
          snapshot={snapshot}
          selected={selected}
          tab={inspectorTab}
          expanded={rightExpanded}
          placement={surface === "journey" ? "left" : "right"}
          onTabChange={setInspectorTab}
          onToggle={toggleRight}
          onOpenArtifact={setArtifact}
          onSelect={selectEntity}
        />

        <button
          type="button"
          className={`drawer-backdrop ${
            leftExpanded || rightExpanded ? "drawer-backdrop--visible" : ""
          }`}
        onClick={closeDrawers}
        aria-label="Close open panel"
        aria-hidden={!(leftExpanded || rightExpanded)}
        tabIndex={-1}
      />
      </div>

      <MobileNav surface={surface} onSelect={selectSurface} />
      <ArtifactViewer
        snapshot={snapshot}
        artifact={artifact}
        onClose={closeArtifact}
      />
    </motion.main>
  );
}
