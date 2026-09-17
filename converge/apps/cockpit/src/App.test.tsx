import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type {
  EntityRef,
  SnapshotEnvelope,
  WorkspaceSnapshot,
} from "./types";
import {
  makeScenarioEnvelope,
  makeScenarioSnapshot,
  makeStaleEnvelope,
} from "./test/scenarios";

vi.mock("motion/react", () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  motion: new Proxy(
    {},
    {
      get: (_target, tag: string) => tag,
    },
  ),
  useReducedMotion: () => true,
}));

vi.mock("./components/LineageCanvas", () => ({
  LineageCanvas: ({
    selected,
    onSelect,
  }: {
    selected: EntityRef | null;
    onSelect: (selection: EntityRef) => void;
  }) => (
    <section aria-label="Mock journey surface">
      <span>Journey selection {selected?.id ?? "none"}</span>
      <button
        type="button"
        onClick={() => onSelect({ kind: "pass", id: "pass-4" })}
      >
        Select consensus
      </button>
    </section>
  ),
}));

vi.mock("./components/WorkSurface", () => ({
  WorkSurface: ({
    selected,
    onSelect,
  }: {
    selected: EntityRef | null;
    onSelect: (selection: EntityRef) => void;
  }) => (
    <section aria-label="Mock work surface">
      <span>Work selection {selected?.id ?? "none"}</span>
      <button
        type="button"
        onClick={() => onSelect({ kind: "task", id: "T-blocked" })}
      >
        Select blocked task
      </button>
    </section>
  ),
}));

vi.mock("./components/RunsSurface", () => ({
  RunsSurface: () => <section aria-label="Mock runs surface">Runs surface</section>,
}));

vi.mock("./components/ProofSurface", () => ({
  ProofSurface: () => (
    <section aria-label="Mock proof surface">Proof surface</section>
  ),
}));

vi.mock("./components/HealthSurface", () => ({
  HealthSurface: () => (
    <section aria-label="Mock health surface">Health surface</section>
  ),
}));

vi.mock("./components/ArtifactViewer", () => ({
  ArtifactViewer: () => null,
}));

type SnapshotListener = (event: MessageEvent<string>) => void;

class EventSourceStub {
  static instances: EventSourceStub[] = [];

  onmessage: SnapshotListener | null = null;
  onerror: (() => void) | null = null;
  listeners = new Map<string, Set<SnapshotListener>>();
  closed = false;

  constructor(readonly url: string) {
    EventSourceStub.instances.push(this);
  }

  addEventListener(name: string, listener: EventListener) {
    const current = this.listeners.get(name) ?? new Set<SnapshotListener>();
    current.add(listener as SnapshotListener);
    this.listeners.set(name, current);
  }

  removeEventListener(name: string, listener: EventListener) {
    this.listeners.get(name)?.delete(listener as SnapshotListener);
  }

  emit(name: string, envelope: SnapshotEnvelope) {
    const event = new MessageEvent("message", {
      data: JSON.stringify(envelope),
    });
    for (const listener of this.listeners.get(name) ?? []) listener(event);
    if (name === "message") this.onmessage?.(event);
  }

  close() {
    this.closed = true;
  }
}

function liveEnvelope(
  mutate?: (snapshot: WorkspaceSnapshot) => void,
): SnapshotEnvelope {
  const snapshot = makeScenarioSnapshot((candidate) => {
    candidate.source = "workspace";
    candidate.snapshotId = "ws3_10000000000000000000000000000001";
    mutate?.(candidate);
  });
  return makeScenarioEnvelope(snapshot);
}

function jsonResponse(document: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(document), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

beforeEach(() => {
  EventSourceStub.instances = [];
  vi.stubGlobal("EventSource", EventSourceStub);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Cockpit application state boundary", () => {
  it("loads a WorkspaceSnapshot 3.0 envelope using GET and labels it live", async () => {
    const fetchMock = vi.fn().mockImplementation(() => jsonResponse(liveEnvelope()));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("Live workspace")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Overview" })).toBeTruthy();
    expect(screen.queryByText("CLI execution")).toBeNull();
    expect(screen.getAllByText(/Pass 4/).length).toBeGreaterThan(0);
    expect(EventSourceStub.instances[0]?.url).toBe("/api/events");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/snapshot",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("preserves typed selection and panel preferences through an SSE refresh", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => jsonResponse(liveEnvelope())));
    render(<App />);
    await screen.findByText("Live workspace");

    const navigation = screen.getByRole("complementary", {
      name: "Cockpit views",
    });
    await user.click(within(navigation).getByRole("button", { name: /Work/i }));
    await user.click(
      screen.getByRole("button", { name: "Select blocked task" }),
    );
    expect(screen.getByText("Work selection T-blocked")).toBeTruthy();
    expect(screen.getByText("Dependency-blocked task")).toBeTruthy();

    const navigationToggle = within(navigation).getByRole("button", {
      name: /(?:Expand|Collapse) navigation/,
    });
    if (navigationToggle.getAttribute("aria-expanded") !== "true") {
      await user.click(navigationToggle);
    }
    await user.click(
      within(navigation).getByRole("button", { name: "Collapse navigation" }),
    );
    const inspector = screen.getByRole("complementary", {
      name: "Selection inspector",
    });
    const inspectorToggle = within(inspector).getByRole("button", {
      name: /(?:Expand|Collapse) inspector/,
    });
    if (inspectorToggle.getAttribute("aria-expanded") !== "true") {
      await user.click(inspectorToggle);
    }
    await user.click(
      within(inspector).getByRole("button", { name: "Collapse inspector" }),
    );
    expect(window.localStorage.getItem("converge-cockpit:left-expanded")).toBe(
      "false",
    );
    expect(window.localStorage.getItem("converge-cockpit:right-expanded")).toBe(
      "false",
    );
    expect(Object.keys(window.localStorage).sort()).toEqual([
      "converge-cockpit:left-expanded",
      "converge-cockpit:right-expanded",
    ]);

    const next = liveEnvelope((snapshot) => {
      snapshot.snapshotId = "ws3_20000000000000000000000000000002";
      snapshot.observedAt = "2026-08-03T20:02:00.000Z";
    });
    EventSourceStub.instances[0].emit("snapshot", next);

    await waitFor(() =>
      expect(screen.getByText("Work selection T-blocked")).toBeTruthy(),
    );
    expect(screen.getByText("Dependency-blocked task")).toBeTruthy();
    expect(
      within(navigation).getByRole("button", { name: "Expand navigation" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Expand selection inspector" }),
    ).toBeTruthy();
  });

  it("keeps last-good data visible and marks stale transport explicitly", async () => {
    const stale = makeStaleEnvelope();
    stale.snapshot.source = "workspace";
    stale.snapshot.snapshotId = "ws3_30000000000000000000000000000003";
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => jsonResponse(stale)));

    render(<App />);

    expect((await screen.findAllByText("Last-good snapshot")).length).toBeGreaterThan(0);
    expect(
      screen.getByText("The CLI snapshot could not be refreshed."),
    ).toBeTruthy();
    expect(screen.queryByText("Replay fixture")).toBeNull();
  });

  it("fails visibly to the replay fixture without claiming live truth", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("bridge is offline")),
    );

    render(<App />);

    expect(await screen.findByText("Live workspace unavailable")).toBeTruthy();
    expect(screen.getByText(/Showing the bundled replay fixture/)).toBeTruthy();
    expect(screen.getByText("Replay fixture")).toBeTruthy();
    expect(screen.queryByText("Live workspace")).toBeNull();
  });
});
