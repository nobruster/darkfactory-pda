import { useState } from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CommandDock } from "./CommandDock";
import { ArtifactViewer } from "./ArtifactViewer";
import { AskSurface } from "./AskSurface";
import { useAskConversations } from "../ask/useAskConversations";

import { DecomposeSurface } from "./DecomposeSurface";
import { HealthSurface } from "./HealthSurface";
import { InspectorPanel } from "./InspectorPanel";
import { ProofSurface } from "./ProofSurface";
import { RunsSurface } from "./RunsSurface";
import { WorkSurface } from "./WorkSurface";
import {
  makeEmptySnapshot,
  makeScenarioSnapshot,
} from "../test/scenarios";

/**
 * Ask conversations are owned by App, so the surface takes the store as a prop.
 * This harness supplies a real store instead of a stub, keeping these tests
 * exercising the same code path the application uses.
 */
function AskSurfaceHarness(props: {
  snapshot: Parameters<typeof AskSurface>[0]["snapshot"];
  selected: Parameters<typeof AskSurface>[0]["selected"];
}) {
  const conversations = useAskConversations();
  return <AskSurface {...props} conversations={conversations} />;
}

/**
 * Chooses question context through Ask's own picker. Context used to be settable
 * only by selecting an entity on another surface, so these tests clicked an
 * "Add selected context" button that no longer exists.
 */
async function pickAskContext(
  user: ReturnType<typeof userEvent.setup>,
  match: RegExp,
) {
  await user.click(screen.getByRole("button", { name: /Question context:/ }));
  const panel = screen.getByRole("dialog", { name: "Question context" });
  await user.click(within(panel).getByRole("button", { name: match }));
}

vi.mock("./WorkGraph", () => ({
  WorkGraph: () => <div aria-label="Work dependency graph">Graph projection</div>,
}));

vi.mock("./DecompositionGraph", () => ({
  DecompositionGraph: () => (
    <div aria-label="Swimlane decomposition graph">Lane graph projection</div>
  ),
}));

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

describe("Cockpit lifecycle surfaces", () => {
  it("renders canonical seams and lets the user inspect lanes and legs", async () => {
    const user = userEvent.setup();
    const snapshot = makeScenarioSnapshot();
    const onSelect = vi.fn();
    render(
      <DecomposeSurface
        snapshot={snapshot}
        selected={{ kind: "swimlane", id: "swimlane-checkout" }}
        onSelect={onSelect}
      />,
    );

    expect(
      screen.getByText(
        "The HTTP boundary isolates shopper intent from payment-provider settlement.",
      ),
    ).toBeTruthy();
    const summary = screen.getByLabelText("Decomposition summary");
    expect(summary.textContent).toContain("1swimlanes");
    expect(summary.textContent).toContain("2delivery legs");

    await user.click(screen.getByRole("button", { name: "Map" }));
    expect(screen.getByText("Lane graph projection")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Read" }));
    expect(screen.getByText("Why this seam")).toBeTruthy();
    expect(
      screen.getByText(
        "The HTTP boundary isolates shopper intent from payment-provider settlement.",
      ),
    ).toBeTruthy();
    await user.click(
      screen.getByRole("button", { name: /Settle payment outcome/i }),
    );
    expect(onSelect).toHaveBeenCalledWith({
      kind: "leg",
      id: "swimlane-checkout-leg-02",
    });
  });

  it("keeps empty decomposition explicit", () => {
    render(
      <DecomposeSurface
        snapshot={makeEmptySnapshot()}
        selected={null}
        onSelect={vi.fn()}
      />,
    );
    expect(
      screen.getByText("No canonical swimlane plans were observed"),
    ).toBeTruthy();
  });

  it("falls back to the readable projection for a graph above the density cap", () => {
    const snapshot = structuredClone(makeScenarioSnapshot());
    const template = snapshot.decomposition.edges[0];
    snapshot.decomposition.edges = Array.from({ length: 321 }, (_, index) => ({
      ...template,
      id: `decompedge_${index.toString(16).padStart(20, "0")}`,
    }));

    render(
      <DecomposeSurface
        snapshot={snapshot}
        selected={null}
        onSelect={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/Focus view protects readability for this large decomposition/),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Map" }).hasAttribute("disabled"),
    ).toBe(true);
    expect(screen.queryByText("Lane graph projection")).toBeNull();
    expect(screen.getAllByText("Accept checkout intent").length).toBeGreaterThan(0);
  });

  it("renders intentional empty work, run, and receipt states", async () => {
    const user = userEvent.setup();
    const snapshot = makeEmptySnapshot();
    const onSelect = vi.fn();
    const { rerender } = render(
      <WorkSurface
        snapshot={snapshot}
        selected={null}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByText("No work has been decomposed")).toBeTruthy();

    rerender(
      <RunsSurface
        snapshot={snapshot}
        selected={null}
        onSelect={onSelect}
      />,
    );
    expect(screen.getByText("No execution records observed")).toBeTruthy();

    rerender(
      <ProofSurface
        snapshot={snapshot}
        selected={null}
        onSelect={onSelect}
        onOpenArtifact={vi.fn()}
      />,
    );
    expect(screen.getByText("No settlements have emitted receipts.")).toBeTruthy();

    await user.click(
      screen.getByText("Task specification").closest("button") as HTMLElement,
    );
    expect(onSelect).toHaveBeenCalledWith({
      kind: "artifact",
      id: "artifact_22222222222222222222",
    });
  });

  it("keeps frontier, backlog, completed, and every Task-Spec state distinct", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <WorkSurface
        snapshot={makeScenarioSnapshot()}
        selected={null}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByRole("button", { name: "List" }));

    const frontier = screen.getByText("Frontier").closest("section");
    const backlog = screen.getByText("Backlog").closest("section");
    const completed = screen.getByText("Completed").closest("section");
    expect(frontier).toBeTruthy();
    expect(backlog).toBeTruthy();
    expect(completed).toBeTruthy();
    expect(within(frontier as HTMLElement).getByText("Dispatchable frontier task")).toBeTruthy();
    expect(within(backlog as HTMLElement).getByText("Dependency-blocked task")).toBeTruthy();
    expect(within(backlog as HTMLElement).getByText("Task in progress")).toBeTruthy();
    expect(within(backlog as HTMLElement).getByText("Parked task")).toBeTruthy();
    expect(within(completed as HTMLElement).getByText("Completed task")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: /Dependency-blocked task/i }));
    expect(onSelect).toHaveBeenCalledWith({ kind: "task", id: "T-blocked" });
  });

  it("renders RED, retry, resumed, and settled attempts as separate records", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <RunsSurface
        snapshot={makeScenarioSnapshot()}
        selected={null}
        onSelect={onSelect}
      />,
    );

    for (const state of ["red", "retry", "resumed", "settled"]) {
      expect(screen.getByText(state)).toBeTruthy();
    }

    await user.click(screen.getByRole("button", { name: /run-retry/i }));
    expect(onSelect).toHaveBeenCalledWith({ kind: "run", id: "run-retry" });
  });

  it("does not conflate verified, mismatched, and unavailable receipts", () => {
    const onSelect = vi.fn();
    render(
      <ProofSurface
        snapshot={makeScenarioSnapshot()}
        selected={null}
        onSelect={onSelect}
        onOpenArtifact={vi.fn()}
      />,
    );

    expect(screen.getByText("verified")).toBeTruthy();
    expect(screen.getByText("mismatch")).toBeTruthy();
    expect(screen.getByText("unavailable")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /T-progress/i }));
    expect(onSelect).toHaveBeenCalledWith({
      kind: "receipt",
      id: "receipt-mismatch",
    });
  });

  it("keeps health checks and typed issues selectable", () => {
    const onSelect = vi.fn();
    render(
      <HealthSurface
        snapshot={makeScenarioSnapshot()}
        selected={null}
        onSelect={onSelect}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /tracker-config/i }));
    expect(onSelect).toHaveBeenCalledWith({
      kind: "health",
      id: "tracker-config",
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: /Pass 4 needs an owner decision/i,
      }),
    );
    expect(onSelect).toHaveBeenCalledWith({
      kind: "issue",
      id: "issue_11111111111111111111",
    });
  });
});

describe("Ask Converge via ACP", () => {
  it("binds a natural-language turn to methodology and the live project without inheriting selection", async () => {
    const user = userEvent.setup();
    const snapshot = makeScenarioSnapshot((candidate) => {
      candidate.source = "workspace";
    });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input, init) => {
        const url = String(input);
        if (url === "/api/ask/agents") {
          return new Response(
            JSON.stringify({
              agents: [
                {
                  id: "codex",
                  label: "Codex",
                  adapter: "codex-acp",
                  availability: "blocked",
                  reason: "Local read and search tools cannot be suppressed.",
                },
                {
                  id: "claude",
                  label: "Claude Agent",
                  adapter: "claude-agent-acp",
                  availability: "available",
                  reason: null,
                },
              ],
              requestToken: "csrf-test-token-1234",
              policy: {
                transport: "ACP",
                workspaceAccess: "enforced-safe-mode",
                persistence: "cockpit-ephemeral",
                evidenceBoundary:
                  "Agent interpretation is not a Converge gate verdict, receipt, or proof.",
              },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        if (url === "/api/ask/options") {
          // The model picker reads real ACP selectors through a probe session.
          expect(init?.method).toBe("POST");
          expect(init?.headers).toEqual(
            expect.objectContaining({ "X-Converge-CSRF": "csrf-test-token-1234" }),
          );
          expect(JSON.parse(String(init?.body))).toEqual({ agentId: "claude" });
          return new Response(
            JSON.stringify({
              agentId: "claude",
              agentInfo: null,
              configOptions: [
                {
                  id: "model",
                  name: "Model",
                  description: null,
                  category: "model",
                  type: "select",
                  currentValue: "sonnet",
                  values: [
                    { value: "sonnet", name: "Sonnet", description: null, group: null },
                    { value: "opus", name: "Opus", description: null, group: null },
                  ],
                  settable: true,
                },
                {
                  id: "session-mode",
                  name: "Session mode",
                  description: null,
                  category: "mode",
                  type: "select",
                  currentValue: "plan",
                  values: [
                    { value: "plan", name: "Plan", description: null, group: null },
                  ],
                  settable: false,
                },
              ],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        expect(url).toBe("/api/ask");
        expect(init?.method).toBe("POST");
        expect(init?.headers).toEqual(
          expect.objectContaining({ "X-Converge-CSRF": "csrf-test-token-1234" }),
        );
        expect(JSON.parse(String(init?.body))).toEqual(
          expect.objectContaining({
            agentId: "claude",
            snapshotId: snapshot.snapshotId,
            context: {
              entity: null,
              artifactIds: [],
            },
          }),
        );
        return new Response(
          JSON.stringify({
            turnId: "turn_1",
            agentId: "claude",
            snapshotId: snapshot.snapshotId,
            grounding: {
              snapshotId: snapshot.snapshotId,
              observedAt: snapshot.observedAt,
              methodology: {
                tool: "cvg",
                version: snapshot.method.version,
                digest: "c".repeat(64),
              },
              entity: null,
              artifacts: [],
            },
            answer: "The checkout lane isolates shopper intent from settlement.",
            steps: [
              "Read the snapshot-bound lane.",
              "Trace the canonical dependency.",
            ],
            activity: [
              {
                id: "read-1",
                kind: "read",
                label: "Read checkout lane",
                status: "complete",
              },
            ],
            stopReason: "end_turn",
            elapsedMs: 420,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      },
    );

    const { container, rerender } = render(
      <AskSurfaceHarness
        snapshot={snapshot}
        selected={{ kind: "swimlane", id: "swimlane-checkout" }}
      />,
    );

    expect(screen.queryByRole("button", { name: /ChatGPT/i })).toBeNull();
    // Provider marks are inline SVG on currentColor, not external vendor
    // colour images, so nothing loads a *-color.svg URL any more.
    expect(container.querySelector(".ask-agent-mark svg")).toBeTruthy();
    expect(container.querySelector('img[src*="-color.svg"]')).toBeNull();
    expect(await screen.findByText("Verify on send")).toBeTruthy();
    expect(screen.queryByText("Ready over ACP")).toBeNull();

    // Engine and model live behind one composer control.
    await user.click(screen.getByRole("button", { name: /Engine and model/ }));
    const enginePanel = screen.getByRole("dialog", { name: "Engine and model" });
    const codexButton = within(enginePanel).getByRole("button", { name: /Codex/i });
    const claudeButton = within(enginePanel).getByRole("button", {
      name: /Claude Agent/i,
    });
    expect(claudeButton.getAttribute("aria-pressed")).toBe("true");
    // Codex is statically blocked, so it explains itself and cannot be chosen.
    // It stays a real focus target rather than being `disabled`, so the reason
    // is reachable by keyboard; activating it must still change nothing.
    expect((codexButton as HTMLButtonElement).disabled).toBe(false);
    expect(codexButton.getAttribute("aria-disabled")).toBe("true");
    expect(codexButton.getAttribute("aria-pressed")).toBe("false");
    expect(
      within(enginePanel).getByText(
        /Local read and search tools cannot be suppressed/,
      ),
    ).toBeTruthy();
    await user.click(codexButton);
    expect(codexButton.getAttribute("aria-pressed")).toBe("false");
    expect(claudeButton.getAttribute("aria-pressed")).toBe("true");
    // Selectable models come from the agent; a mode selector is never offered.
    expect(await within(enginePanel).findByText("Sonnet")).toBeTruthy();
    expect(within(enginePanel).getByText("Opus")).toBeTruthy();
    expect(within(enginePanel).queryByText("Session mode")).toBeNull();
    await user.click(within(enginePanel).getByRole("button", { name: /Opus/ }));
    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: /Engine and model:.*Opus/ })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /Question context: Whole workspace/ }),
    ).toBeTruthy();
    await user.click(
      within(screen.getByLabelText("Suggested questions")).getAllByRole("button")[0],
    );
    await user.click(screen.getByRole("button", { name: "Send question" }));
    expect(
      await screen.findByText(
        "The checkout lane isolates shopper intent from settlement.",
      ),
    ).toBeTruthy();
    expect(screen.getByText("Read the snapshot-bound lane.")).toBeTruthy();
    expect(screen.getByText(/answers are interpretation, never a gate verdict/i)).toBeTruthy();
    // registry + model-option probe + the turn itself
    expect(fetchSpy).toHaveBeenCalledTimes(3);

    const refreshedSnapshot = structuredClone(snapshot);
    refreshedSnapshot.snapshotId = `ws3_${"a".repeat(32)}`;
    refreshedSnapshot.observedAt = "2026-08-04T12:00:00.000Z";
    rerender(
      <AskSurfaceHarness
        snapshot={refreshedSnapshot}
        selected={{ kind: "swimlane", id: "swimlane-checkout" }}
      />,
    );
    expect(
      screen.getByText("The checkout lane isolates shopper intent from settlement."),
    ).toBeTruthy();
  });

  it("includes explicitly selected artifact text in the snapshot-bound request", async () => {
    const user = userEvent.setup();
    const snapshot = makeScenarioSnapshot((candidate) => {
      candidate.source = "workspace";
    });
    const artifact = snapshot.artifacts[0];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (String(input) === "/api/ask/agents") {
        return new Response(
          JSON.stringify({
            agents: [
              {
                id: "codex",
                label: "Codex",
                adapter: "codex-acp",
                availability: "blocked",
                reason: "Local reads cannot be suppressed.",
              },
              {
                id: "claude",
                label: "Claude Agent",
                adapter: "claude-agent-acp",
                availability: "available",
                reason: null,
              },
            ],
            requestToken: "csrf-artifact-token",
            policy: {
              transport: "ACP",
              workspaceAccess: "enforced-safe-mode",
              persistence: "cockpit-ephemeral",
              evidenceBoundary:
                "Agent interpretation is not a Converge gate verdict, receipt, or proof.",
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      const request = JSON.parse(String(init?.body));
      expect(request.context).toEqual({
        entity: { kind: "artifact", id: artifact.id },
        artifactIds: [artifact.id],
      });
      return new Response(
        JSON.stringify({
          turnId: "turn_artifact",
          agentId: "claude",
          snapshotId: snapshot.snapshotId,
          grounding: {
            snapshotId: snapshot.snapshotId,
            observedAt: snapshot.observedAt,
            methodology: {
              tool: "cvg",
              version: snapshot.method.version,
              digest: "d".repeat(64),
            },
            entity: { kind: "artifact", id: artifact.id },
            artifacts: [
              {
                id: artifact.id,
                label: artifact.label,
                path: artifact.path,
                sha256: artifact.sha256,
                truncated: false,
              },
            ],
          },
          answer: "The selected artifact is included by digest.",
          steps: [],
          activity: [],
          stopReason: "end_turn",
          elapsedMs: 10,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });

    render(
      <AskSurfaceHarness
        snapshot={snapshot}
        selected={{ kind: "artifact", id: artifact.id }}
      />,
    );
    await screen.findByText("Verify on send");
    await pickAskContext(user, /Selected elsewhere in Cockpit/);
    await user.type(
      screen.getByRole("textbox", {
        name: "Question for the selected ACP agent",
      }),
      "Explain this artifact.",
    );
    await user.click(screen.getByRole("button", { name: "Send question" }));
    expect(
      await screen.findByText("The selected artifact is included by digest."),
    ).toBeTruthy();
  });

  it.each([
    ["path", "docs/not-the-selected-artifact.md"],
    ["sha256", "f".repeat(64)],
  ] as const)(
    "rejects selected artifact grounding when its %s does not match the snapshot",
    async (field, mismatchedValue) => {
      const user = userEvent.setup();
      const snapshot = makeScenarioSnapshot((candidate) => {
        candidate.source = "workspace";
      });
      const artifact = snapshot.artifacts[0];
      vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
        if (String(input) === "/api/ask/agents") {
          return new Response(
            JSON.stringify({
              agents: [
                {
                  id: "claude",
                  label: "Claude Agent",
                  adapter: "claude-agent-acp",
                  availability: "available",
                  reason: null,
                },
              ],
              requestToken: "csrf-artifact-mismatch-token",
              policy: {
                transport: "ACP",
                workspaceAccess: "enforced-safe-mode",
                persistence: "cockpit-ephemeral",
                evidenceBoundary:
                  "Agent interpretation is not a Converge gate verdict, receipt, or proof.",
              },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            turnId: `turn_artifact_${field}_mismatch`,
            agentId: "claude",
            snapshotId: snapshot.snapshotId,
            grounding: {
              snapshotId: snapshot.snapshotId,
              observedAt: snapshot.observedAt,
              methodology: {
                tool: "cvg",
                version: snapshot.method.version,
                digest: "e".repeat(64),
              },
              entity: { kind: "artifact", id: artifact.id },
              artifacts: [
                {
                  id: artifact.id,
                  label: artifact.label,
                  path: artifact.path,
                  sha256: artifact.sha256,
                  truncated: false,
                  [field]: mismatchedValue,
                },
              ],
            },
            answer: "This response must not be rendered.",
            steps: [],
            activity: [],
            stopReason: "end_turn",
            elapsedMs: 10,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      });

      render(
        <AskSurfaceHarness
          snapshot={snapshot}
          selected={{ kind: "artifact", id: artifact.id }}
        />,
      );
      await screen.findByText("Verify on send");
      await pickAskContext(user, /Selected elsewhere in Cockpit/);
      await user.type(
        screen.getByRole("textbox", {
          name: "Question for the selected ACP agent",
        }),
        "Explain this artifact.",
      );
      await user.click(screen.getByRole("button", { name: "Send question" }));
      expect(
        await screen.findByText(
          "The agent response was not bound to this workspace snapshot.",
        ),
      ).toBeTruthy();
      expect(screen.queryByText("This response must not be rendered.")).toBeNull();
    },
  );

  it("starts a clean focused conversation and resets explicit selected context", async () => {
    const user = userEvent.setup();
    const snapshot = makeScenarioSnapshot((candidate) => {
      candidate.source = "workspace";
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          agents: [{
            id: "claude",
            label: "Claude Agent",
            adapter: "claude-agent-acp",
            availability: "available",
            reason: null,
          }],
          requestToken: "csrf-new-chat-token",
          policy: {
            transport: "ACP",
            workspaceAccess: "enforced-safe-mode",
            persistence: "cockpit-ephemeral",
            evidenceBoundary: "Interpretation only.",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(
      <AskSurfaceHarness
        snapshot={snapshot}
        selected={{ kind: "pass", id: "pass-4" }}
      />,
    );
    await screen.findByText("Verify on send");
    const textbox = screen.getByRole("textbox", {
      name: "Question for the selected ACP agent",
    }) as HTMLTextAreaElement;
    const newChat = screen.getByRole("button", { name: "Start new chat" });
    expect((newChat as HTMLButtonElement).disabled).toBe(false);
    await pickAskContext(user, /Selected elsewhere in Cockpit/);
    expect(
      screen.getByRole("button", { name: /Question context: Pass 4/ }),
    ).toBeTruthy();
    await user.type(textbox, "Draft project question");
    await user.click(newChat);
    expect(textbox.value).toBe("");
    expect(document.activeElement).toBe(textbox);
    // A new chat starts unscoped again.
    expect(
      screen.getByRole("button", { name: /Question context: Whole workspace/ }),
    ).toBeTruthy();
    expect(screen.queryByText(/^pass:pass-4$/i)).toBeNull();
  });

  it("renders actionable provider authentication recovery and restores the question", async () => {
    const user = userEvent.setup();
    const snapshot = makeScenarioSnapshot((candidate) => {
      candidate.source = "workspace";
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input) === "/api/ask/agents") {
        return new Response(
          JSON.stringify({
            agents: [{
              id: "claude",
              label: "Claude Agent",
              adapter: "claude-agent-acp",
              availability: "available",
              reason: null,
            }],
            requestToken: "csrf-auth-token-1",
            policy: {
              transport: "ACP",
              workspaceAccess: "enforced-safe-mode",
              persistence: "cockpit-ephemeral",
              evidenceBoundary: "Interpretation only.",
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "ASK_AUTH_REQUIRED",
            message:
              "The selected agent is not authenticated on this machine. Sign in with its local CLI, then try again.",
            retryable: true,
          },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      );
    });

    render(<AskSurfaceHarness snapshot={snapshot} selected={null} />);
    await screen.findByText("Verify on send");
    const textbox = screen.getByRole("textbox", {
      name: "Question for the selected ACP agent",
    }) as HTMLTextAreaElement;
    await user.type(textbox, "Why is the project blocked?");
    await user.click(screen.getByRole("button", { name: "Send question" }));
    expect(await screen.findByText(/not authenticated on this machine/i)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(textbox.value).toBe("Why is the project blocked?");
    expect(document.activeElement).toBe(textbox);
  });
});

describe("Cockpit proof and command boundaries", () => {
  it("copies the exact CLI command without exposing an execution control", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator.clipboard, "writeText", {
      configurable: true,
      value: writeText,
    });
    const snapshot = makeScenarioSnapshot();
    render(<CommandDock snapshot={snapshot} />);

    expect(screen.getByText("cvg review --check")).toBeTruthy();
    expect(screen.getByText("Browser read-only")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /run|execute/i })).toBeNull();

    await user.click(
      screen.getByRole("button", { name: "Copy authorized command" }),
    );
    expect(writeText).toHaveBeenCalledWith("cvg review --check");
    expect(screen.getByRole("button", { name: "Command copied" })).toBeTruthy();
  });

  it("shows inspector history only for explicitly linked signals", async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    const { rerender } = render(
      <InspectorPanel
        snapshot={makeScenarioSnapshot()}
        selected={{ kind: "run", id: "run-retry" }}
        tab="overview"
        expanded
        onTabChange={onTabChange}
        onToggle={vi.fn()}
        onOpenArtifact={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("run-retry")).toBeTruthy();
    expect(screen.queryByText(/Text mentions run-retry/)).toBeNull();

    await user.click(screen.getByRole("tab", { name: "Activity" }));
    expect(onTabChange).toHaveBeenCalledWith("activity");

    rerender(
      <InspectorPanel
        snapshot={makeScenarioSnapshot()}
        selected={{ kind: "run", id: "run-retry" }}
        tab="activity"
        expanded
        onTabChange={onTabChange}
        onToggle={vi.fn()}
        onOpenArtifact={vi.fn()}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("Retry was requested.")).toBeTruthy();
    expect(screen.getByText("RED evaluation.")).toBeTruthy();
    expect(screen.queryByText(/Text mentions run-retry/)).toBeNull();
  });

  it("does not request artifact bytes for replay fixtures", async () => {
    const snapshot = makeScenarioSnapshot();
    const artifact = snapshot.artifacts[0];
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValue(new Error("fixture previews must not reach the bridge"));

    render(
      <ArtifactViewer snapshot={snapshot} artifact={artifact} onClose={vi.fn()} />,
    );

    expect(await screen.findByText("Live workspace required")).toBeTruthy();
    expect(
      screen.getByText(
        /Replay fixture entries cannot be opened as verified artifacts/,
      ),
    ).toBeTruthy();
    expect(screen.getByText("not live evidence")).toBeTruthy();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("explains when the live workspace snapshot is unavailable", async () => {
    const snapshot = makeScenarioSnapshot();
    snapshot.source = "workspace";
    const artifact = snapshot.artifacts[0];
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("", { status: 503 }));

    render(
      <ArtifactViewer snapshot={snapshot} artifact={artifact} onClose={vi.fn()} />,
    );

    expect(await screen.findByText("Preview unavailable")).toBeTruthy();
    expect(
      screen.getByText(/The live workspace snapshot is unavailable/),
    ).toBeTruthy();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("keeps artifact reads snapshot-and-digest bound and restores focus", async () => {
    const user = userEvent.setup();
    const snapshot = makeScenarioSnapshot();
    snapshot.source = "workspace";
    const artifact = snapshot.artifacts[0];
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          path: artifact.path,
          label: artifact.label,
          kind: artifact.kind,
          format: "text",
          content: "canonical proof",
          truncated: false,
          redacted: false,
          sourceBytes: 15,
          sha256: artifact.sha256,
          snapshotId: snapshot.snapshotId,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            Open canonical proof
          </button>
          <ArtifactViewer
            snapshot={snapshot}
            artifact={open ? artifact : null}
            onClose={() => setOpen(false)}
          />
        </>
      );
    }

    render(<Harness />);
    const opener = screen.getByRole("button", { name: "Open canonical proof" });
    await user.click(opener);

    const close = await screen.findByRole("button", {
      name: "Close artifact viewer",
    });
    await waitFor(() => expect(document.activeElement).toBe(close));
    expect(fetchSpy).toHaveBeenCalledWith(
      `/api/artifact?path=${encodeURIComponent(artifact.path)}&snapshotId=${snapshot.snapshotId}&sha256=${artifact.sha256}`,
      expect.objectContaining({ method: "GET" }),
    );
    expect(await screen.findByText("canonical proof")).toBeTruthy();

    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Close artifact viewer" }),
      ).toBeNull(),
    );
    expect(document.activeElement).toBe(opener);
  });

  it("renders GFM Markdown without activating raw HTML, unsafe links, or remote images", async () => {
    const snapshot = makeScenarioSnapshot();
    snapshot.source = "workspace";
    const artifact = snapshot.artifacts.find((candidate) => candidate.path.endsWith(".md"));
    expect(artifact).toBeTruthy();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          path: artifact?.path,
          label: artifact?.label,
          kind: artifact?.kind,
          format: "markdown",
          content: [
            "---",
            "owner: delivery",
            "---",
            "# Safe document",
            "",
            "- [x] Verified item",
            "",
            "| Gate | State |",
            "| --- | --- |",
            "| Review | PASS |",
            "",
            "[Unsafe](javascript:alert(1))",
            "",
            "[Guide](https://example.com/guide)",
            "",
            "![Remote proof](https://attacker.example/proof.png)",
            "",
            "<script>window.readerCompromised = true</script>",
          ].join("\n"),
          truncated: false,
          redacted: true,
          sourceBytes: 320,
          sha256: artifact?.sha256,
          snapshotId: snapshot.snapshotId,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(
      <ArtifactViewer
        snapshot={snapshot}
        artifact={artifact ?? null}
        onClose={vi.fn()}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Safe document" })).toBeTruthy();
    expect(screen.getByRole("table")).toBeTruthy();
    expect(screen.getByText("Verified item")).toBeTruthy();
    expect(screen.getByText("Document metadata")).toBeTruthy();
    expect(screen.getByText("Image omitted: Remote proof")).toBeTruthy();
    expect(screen.queryByRole("img")).toBeNull();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText("Unsafe").closest("a")).toBeNull();
    expect(screen.getByRole("link", { name: "Guide" }).getAttribute("rel")).toBe(
      "noreferrer noopener",
    );
    expect(screen.getByText("credentials redacted")).toBeTruthy();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("renders redacted PDF page text without receiving raw PDF bytes", async () => {
    const user = userEvent.setup();
    const snapshot = makeScenarioSnapshot();
    snapshot.source = "workspace";
    const artifact = snapshot.artifacts[0];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          path: artifact.path,
          label: artifact.label,
          kind: artifact.kind,
          format: "pdf-text",
          pages: [
            { number: 1, text: "First verified page" },
            { number: 2, text: "Second page with [REDACTED]" },
          ],
          pageCount: 2,
          truncated: false,
          redacted: true,
          sourceBytes: 4_096,
          sha256: artifact.sha256,
          snapshotId: snapshot.snapshotId,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(
      <ArtifactViewer snapshot={snapshot} artifact={artifact} onClose={vi.fn()} />,
    );

    expect(await screen.findByText("First verified page")).toBeTruthy();
    expect(screen.getByText("Redacted page text only.", { exact: false })).toBeTruthy();
    expect(screen.getByText("Page 1 of 2")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Next PDF page" }));
    expect(screen.getByText("Second page with [REDACTED]")).toBeTruthy();
    expect(screen.getByText("Page 2 of 2")).toBeTruthy();
    expect(document.querySelector("iframe, object, embed")).toBeNull();
  });
});
