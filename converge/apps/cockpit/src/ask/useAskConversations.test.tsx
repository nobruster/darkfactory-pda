import { StrictMode, useState } from "react";
import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { AskSurface } from "../components/AskSurface";
import { makeScenarioSnapshot } from "../test/scenarios";
import type { AskConversationTurn } from "./types";
import { conversationTitle, useAskConversations } from "./useAskConversations";

function turn(id: string, question: string): AskConversationTurn {
  return {
    id,
    agentId: "claude",
    question,
    scope: null,
    state: "complete",
    response: null,
    error: null,
  };
}

describe("Ask conversation store", () => {
  it("titles a conversation from its first question and keeps later titles stable", () => {
    const { result } = renderHook(() => useAskConversations(), {
      // StrictMode double-invokes state updaters, which is what catches an
      // impure updater that stores one conversation and activates another.
      wrapper: StrictMode,
    });

    act(() => {
      result.current.appendTurn(turn("turn-1", "  Why is the lane   blocked?  "));
    });
    expect(result.current.active?.title).toBe("Why is the lane blocked?");
    expect(result.current.active?.turns).toHaveLength(1);

    act(() => {
      result.current.appendTurn(turn("turn-2", "And what unblocks it?"));
    });
    expect(result.current.active?.title).toBe("Why is the lane blocked?");
    expect(result.current.active?.turns).toHaveLength(2);
    // Both turns belong to one conversation, not two.
    expect(result.current.history).toHaveLength(1);
  });

  it("archives the current conversation instead of discarding it on New chat", () => {
    const { result } = renderHook(() => useAskConversations(), {
      // StrictMode double-invokes state updaters, which is what catches an
      // impure updater that stores one conversation and activates another.
      wrapper: StrictMode,
    });

    act(() => {
      result.current.appendTurn(turn("turn-1", "First conversation"));
    });
    const firstId = result.current.activeId;

    act(() => {
      result.current.startConversation();
    });
    expect(result.current.activeId).not.toBe(firstId);
    expect(result.current.active?.turns).toHaveLength(0);
    // The earlier conversation is still reachable.
    expect(result.current.history.map((entry) => entry.id)).toEqual([firstId]);

    act(() => {
      result.current.appendTurn(turn("turn-2", "Second conversation"));
    });
    expect(result.current.history).toHaveLength(2);

    act(() => {
      result.current.selectConversation(firstId as string);
    });
    expect(result.current.active?.turns[0].question).toBe("First conversation");
  });

  it("does not accumulate empty conversations when New chat is pressed repeatedly", () => {
    const { result } = renderHook(() => useAskConversations(), {
      // StrictMode double-invokes state updaters, which is what catches an
      // impure updater that stores one conversation and activates another.
      wrapper: StrictMode,
    });

    act(() => {
      result.current.startConversation();
    });
    act(() => {
      result.current.startConversation();
    });
    act(() => {
      result.current.startConversation();
    });
    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.history).toHaveLength(0);
  });

  it("patches a turn in place and deletes conversations", () => {
    const { result } = renderHook(() => useAskConversations(), {
      // StrictMode double-invokes state updaters, which is what catches an
      // impure updater that stores one conversation and activates another.
      wrapper: StrictMode,
    });

    act(() => {
      result.current.appendTurn(turn("turn-1", "Pending question"));
    });
    act(() => {
      result.current.patchTurn("turn-1", { state: "error" });
    });
    expect(result.current.active?.turns[0].state).toBe("error");

    const id = result.current.activeId as string;
    act(() => {
      result.current.deleteConversation(id);
    });
    expect(result.current.conversations).toHaveLength(0);
    expect(result.current.activeId).toBeNull();
  });

  it("truncates a long question on a word boundary for the history label", () => {
    const long =
      "Explain precisely why this delivery leg remains unproven and what evidence the owner must record before the next pass can be authorized";
    const title = conversationTitle(long);
    expect(title.endsWith("…")).toBe(true);
    expect(title.length).toBeLessThanOrEqual(73);
    expect(title).not.toMatch(/\s…$/);
  });
});

describe("Ask transcript across surface navigation", () => {
  it("keeps the transcript when Ask unmounts and remounts", async () => {
    const user = userEvent.setup();
    const snapshot = makeScenarioSnapshot((candidate) => {
      candidate.source = "workspace";
    });

    /**
     * Mirrors App: the store lives above the surface, and the surface is
     * conditionally rendered. Ask previously held its transcript in component
     * state, so this navigation discarded the conversation entirely.
     */
    function Harness() {
      const conversations = useAskConversations();
      const [showAsk, setShowAsk] = useState(true);
      return (
        <>
          <button type="button" onClick={() => setShowAsk((open) => !open)}>
            Toggle surface
          </button>
          <button
            type="button"
            onClick={() => conversations.appendTurn(turn("turn-1", "Seeded question"))}
          >
            Seed turn
          </button>
          {showAsk ? (
            <AskSurface
              snapshot={snapshot}
              selected={null}
              conversations={conversations}
            />
          ) : (
            <p>Another surface</p>
          )}
        </>
      );
    }

    render(
      <StrictMode>
        <Harness />
      </StrictMode>,
    );
    await user.click(screen.getByRole("button", { name: "Seed turn" }));
    expect(screen.getByText("Seeded question")).toBeTruthy();

    // Leave Ask, then come back.
    await user.click(screen.getByRole("button", { name: "Toggle surface" }));
    expect(screen.getByText("Another surface")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Toggle surface" }));

    expect(screen.getByText("Seeded question")).toBeTruthy();
  });
});
