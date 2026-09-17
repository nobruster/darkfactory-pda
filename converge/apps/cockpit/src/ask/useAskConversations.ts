import { useCallback, useMemo, useRef, useState } from "react";

import type { AskConversation, AskConversationTurn } from "./types";

const MAX_CONVERSATIONS = 24;
const MAX_TITLE_LENGTH = 72;

export function conversationTitle(question: string) {
  const collapsed = question.replace(/\s+/gu, " ").trim();
  if (collapsed.length <= MAX_TITLE_LENGTH) return collapsed;
  const clipped = collapsed.slice(0, MAX_TITLE_LENGTH);
  const boundary = clipped.lastIndexOf(" ");
  return `${(boundary > 32 ? clipped.slice(0, boundary) : clipped).trimEnd()}…`;
}

export interface AskConversationStore {
  conversations: AskConversation[];
  activeId: string | null;
  active: AskConversation | null;
  /** Conversations that have at least one turn, newest first. */
  history: AskConversation[];
  startConversation: () => string;
  selectConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
  appendTurn: (turn: AskConversationTurn) => void;
  patchTurn: (turnId: string, patch: Partial<AskConversationTurn>) => void;
  clearAll: () => void;
}

/**
 * Owns every Ask conversation for the session.
 *
 * This lives above the surface on purpose. Ask used to hold its transcript in
 * component state, so moving to any other surface unmounted it and discarded the
 * conversation. Nothing here is persisted to storage: transcripts survive
 * navigation but not a reload, which keeps provider answers off disk and matches
 * the `cockpit-ephemeral` persistence contract.
 */
export function useAskConversations(
  { now = () => Date.now() }: { now?: () => number } = {},
): AskConversationStore {
  const [conversations, setConversations] = useState<AskConversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const counterRef = useRef(0);

  const startConversation = useCallback(() => {
    counterRef.current += 1;
    const timestamp = now();
    const id = `ask-conversation-${timestamp}-${counterRef.current}`;
    setConversations((current) => {
      // Drop any empty conversation so repeatedly pressing New chat cannot
      // accumulate blank entries in the history list.
      const kept = current.filter((conversation) => conversation.turns.length > 0);
      return [
        {
          id,
          title: "New chat",
          createdAt: timestamp,
          updatedAt: timestamp,
          turns: [],
        },
        ...kept,
      ].slice(0, MAX_CONVERSATIONS);
    });
    setActiveId(id);
    return id;
  }, [now]);

  const selectConversation = useCallback((id: string) => {
    setActiveId((current) => (current === id ? current : id));
  }, []);

  const deleteConversation = useCallback((id: string) => {
    setConversations((current) =>
      current.filter((conversation) => conversation.id !== id),
    );
    setActiveId((current) => (current === id ? null : current));
  }, []);

  const appendTurn = useCallback(
    (turn: AskConversationTurn) => {
      const timestamp = now();
      // The new-conversation id is derived before the state updater runs, and
      // setActiveId is called outside it. A state updater must stay pure:
      // StrictMode double-invokes it, so advancing the counter or activating an
      // id inside would store one conversation and activate a different one,
      // leaving the transcript blank while history still counted the turn.
      if (activeId === null) {
        counterRef.current += 1;
        const id = `ask-conversation-${timestamp}-${counterRef.current}`;
        setConversations((current) =>
          [
            {
              id,
              title: conversationTitle(turn.question),
              createdAt: timestamp,
              updatedAt: timestamp,
              turns: [turn],
            },
            ...current.filter((conversation) => conversation.turns.length > 0),
          ].slice(0, MAX_CONVERSATIONS),
        );
        setActiveId(id);
        return;
      }
      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === activeId
            ? {
                ...conversation,
                title:
                  conversation.turns.length === 0
                    ? conversationTitle(turn.question)
                    : conversation.title,
                updatedAt: timestamp,
                turns: [...conversation.turns, turn],
              }
            : conversation,
        ),
      );
    },
    [activeId, now],
  );

  const patchTurn = useCallback(
    (turnId: string, patch: Partial<AskConversationTurn>) => {
      setConversations((current) =>
        current.map((conversation) =>
          conversation.turns.some((turn) => turn.id === turnId)
            ? {
                ...conversation,
                turns: conversation.turns.map((turn) =>
                  turn.id === turnId ? { ...turn, ...patch } : turn,
                ),
              }
            : conversation,
        ),
      );
    },
    [],
  );

  const clearAll = useCallback(() => {
    setConversations([]);
    setActiveId(null);
  }, []);

  const active = useMemo(
    () => conversations.find((conversation) => conversation.id === activeId) ?? null,
    [activeId, conversations],
  );
  const history = useMemo(
    () =>
      conversations
        .filter((conversation) => conversation.turns.length > 0)
        .sort((left, right) => right.updatedAt - left.updatedAt),
    [conversations],
  );

  return {
    conversations,
    activeId,
    active,
    history,
    startConversation,
    selectConversation,
    deleteConversation,
    appendTurn,
    patchTurn,
    clearAll,
  };
}
