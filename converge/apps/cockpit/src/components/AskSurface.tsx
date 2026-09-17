import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import {
  ArrowRight,
  ArrowUp,
  Check,
  CaretDown,
  CircleNotch,
  ClockCounterClockwise,
  CloudSlash,
  Cube,
  LockKey,
  MagnifyingGlass,
  Plus,
  ShieldCheck,
  Sliders,
  Stop,
  Trash,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type {
  AskAgent,
  AskCapabilities,
  AskConfigOption,
  AskConfigSelection,
  AskConversationTurn,
  AskFailure,
  AskTurnResponse,
} from "../ask/types";
import type { AskConversationStore } from "../ask/useAskConversations";
import {
  askContextCandidates,
  filterContextCandidates,
} from "../ask/context-candidates";
import { resolveEntity, sameEntity } from "../lib/entities";
import type { EntityRef, WorkspaceSnapshot } from "../types";

interface AskSurfaceProps {
  snapshot: WorkspaceSnapshot;
  selected: EntityRef | null;
  conversations: AskConversationStore;
}

class AskRequestError extends Error {
  code: string;
  retryable: boolean;

  constructor(failure: AskFailure) {
    super(failure.message);
    this.name = "AskRequestError";
    this.code = failure.code;
    this.retryable = failure.retryable;
  }
}

function safeAssistantLink(href: string | undefined) {
  if (!href) return null;
  if (href.startsWith("#")) return href;
  try {
    const parsed = new URL(href);
    return ["https:", "http:", "mailto:"].includes(parsed.protocol)
      ? href
      : null;
  } catch {
    return null;
  }
}

const askMarkdownComponents: Components = {
  a({ node: _node, href, children, ...props }) {
    const safeHref = safeAssistantLink(href);
    if (!safeHref) return <span className="ask-answer__unsafe-link">{children}</span>;
    const external = !safeHref.startsWith("#");
    return (
      <a
        {...props}
        href={safeHref}
        {...(external ? { target: "_blank", rel: "noreferrer noopener" } : {})}
      >
        {children}
      </a>
    );
  },
  img({ node: _node, alt }) {
    return (
      <span className="ask-answer__omitted-media" role="note">
        {alt ? `Image omitted: ${alt}` : "Image omitted from the answer"}
      </span>
    );
  },
  pre({ node: _node, children, ...props }) {
    return <pre {...props} tabIndex={0}>{children}</pre>;
  },
  table({ node: _node, children, ...props }) {
    return (
      <div className="ask-answer__table" role="region" aria-label="Scrollable answer table" tabIndex={0}>
        <table {...props}>{children}</table>
      </div>
    );
  },
};

export function suggestionsFor(
  snapshot: WorkspaceSnapshot,
  requestedEntity: EntityRef | null,
) {
  const activePass = snapshot.method.passes.find(
    (pass) => pass.id === snapshot.method.activePassId,
  );
  const activeLabel = activePass
    ? `Pass ${activePass.order}: ${activePass.label}`
    : "the current Converge frontier";
  const stateQuestion = activePass && snapshot.authorization.state === "blocked"
    ? `Why is this project blocked at ${activeLabel}, and what exact evidence or owner decision would authorize the next pass?`
    : !activePass && snapshot.authorization.state === "complete"
      ? "The Converge lane is complete, but is delivery complete? Explain the remaining work, execution, receipts, and unresolved evidence."
      : `Why is ${activeLabel} ${activePass?.status ?? "current"}, what evidence supports that state, and what should happen next?`;
  const riskQuestion = snapshot.review?.unresolvedCount
    ? `Which of the ${snapshot.review.unresolvedCount} unresolved review decisions carries the most downstream risk, and what does it block?`
    : snapshot.issues.length > 0
      ? `Which observed project issue matters most right now, what does it block, and how can the team verify the recovery?`
      : snapshot.work.frontier.taskIds.length > 0
        ? `Which task is genuinely dispatchable now, what does it depend on, and what proof will show it is done?`
        : "What changed most recently, and what should the team verify before continuing?";
  const projectSuggestions = [
    { label: "State and authority", question: stateQuestion },
    {
      label: "End-to-end trace",
      question:
        "Trace this project from intent through seams, tasks, execution, and proof. Where is the weakest link?",
    },
    { label: "Risk and evidence", question: riskQuestion },
  ];
  if (!requestedEntity) return projectSuggestions;
  const entity = resolveEntity(snapshot, requestedEntity);
  const title = entity?.title ?? `${requestedEntity.kind}:${requestedEntity.id}`;
  return [
    {
      label: "Selected context",
      question: `Explain ${title}: why it exists, what it depends on, what it produced, and what remains unresolved.`,
    },
    ...projectSuggestions.slice(0, 2),
  ];
}

const EMPTY_CAPABILITIES: AskCapabilities = {
  agents: [
    {
      id: "codex",
      label: "Codex",
      adapter: "codex-acp",
      availability: "not_configured",
      reason: "The Codex ACP adapter has not been configured.",
    },
    {
      id: "claude",
      label: "Claude Agent",
      adapter: "claude-agent-acp",
      availability: "not_configured",
      reason: "The Claude Agent ACP adapter has not been configured.",
    },
  ],
  requestToken: "",
  policy: {
    transport: "ACP",
    workspaceAccess: "enforced-safe-mode",
    persistence: "cockpit-ephemeral",
    evidenceBoundary:
      "Agent interpretation is not a Converge gate verdict, receipt, or proof.",
  },
};

/**
 * Monochrome provider marks drawn inline so they inherit `currentColor`.
 *
 * The previous implementation loaded vendor full-colour SVGs as external `<img>`
 * URLs, which CSS cannot recolour — that is why they read as stickers dropped
 * into a restrained dark interface rather than as part of it.
 */
function AgentMark({ id }: { id: AskAgent["id"] }) {
  return (
    <span className={`ask-agent-mark ask-agent-mark--${id}`} aria-hidden="true">
      {id === "claude" ? (
        <svg viewBox="0 0 24 24" fill="none" focusable="false">
          {Array.from({ length: 6 }, (_unused, index) => {
            const angle = (index * Math.PI) / 6 + Math.PI / 12;
            const x = Math.cos(angle) * 8.5;
            const y = Math.sin(angle) * 8.5;
            return (
              <line
                key={angle}
                x1={12 - x}
                y1={12 - y}
                x2={12 + x}
                y2={12 + y}
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
              />
            );
          })}
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" focusable="false">
          <path
            d="M12 2.6 20.1 7.3v9.4L12 21.4 3.9 16.7V7.3z"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinejoin="round"
          />
          <path
            d="M12 8.1 15.6 10.2v4.2L12 16.5 8.4 14.4v-4.2z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </span>
  );
}

function seconds(ms: number | null | undefined) {
  return typeof ms === "number" ? `${(ms / 1000).toFixed(1)}s` : "—";
}

function kib(bytes: number) {
  return `${Math.round(bytes / 1024).toLocaleString()} KiB`;
}

/**
 * The evidence a turn was actually given, plus where its wall-clock went.
 *
 * The grounding block already travelled with every answer but was collapsed to
 * a single line, so a reader could not check an interpretation against its
 * sources or see why a turn took as long as it did.
 */
function AskSources({ response }: { response: AskTurnResponse }) {
  const { grounding, timings, context } = response;
  const artifacts = grounding.artifacts ?? [];
  const counts = context
    ? [
        `${context.methodCommands} cvg commands`,
        `${context.passes} passes`,
        `${context.swimlanes} swimlanes`,
        `${context.legs} legs`,
        `${context.tasks} Task-Specs`,
        `${context.runs} runs`,
        `${context.receipts} receipts`,
        `${context.artifactsCatalogued} artifacts catalogued`,
        `${context.issues} issues`,
        `${context.signals} signals`,
        `${context.healthChecks} health checks`,
      ]
    : [];

  return (
    <details className="ask-sources">
      <summary>
        <ShieldCheck weight="fill" aria-hidden="true" />
        <span>
          Grounded in Converge {grounding.methodology.version}, snapshot{" "}
          {grounding.snapshotId.slice(0, 12)}
        </span>
        <em>
          {seconds(timings?.totalMs ?? response.elapsedMs)}
          {context ? ` · ${kib(context.contextBytes)} sent` : ""}
        </em>
      </summary>

      <div className="ask-sources__body">
        <section>
          <h4>Sources</h4>
          <dl>
            <div>
              <dt>Method</dt>
              <dd>
                {grounding.methodology.tool} {grounding.methodology.version}
                <code>{grounding.methodology.digest.slice(0, 12)}</code>
              </dd>
            </div>
            <div>
              <dt>Snapshot</dt>
              <dd>
                <code>{grounding.snapshotId}</code>
                observed {new Date(grounding.observedAt).toLocaleString()}
              </dd>
            </div>
            <div>
              <dt>Focus</dt>
              <dd>
                {grounding.entity
                  ? `${grounding.entity.kind}:${grounding.entity.id}`
                  : "Whole workspace snapshot"}
              </dd>
            </div>
            {artifacts.length > 0 ? (
              <div>
                <dt>Documents</dt>
                <dd>
                  <ul className="ask-sources__artifacts">
                    {artifacts.map((artifact) => (
                      <li key={artifact.id}>
                        <strong>{artifact.label}</strong>
                        <code>{artifact.path}</code>
                        <code>sha256 {artifact.sha256.slice(0, 12)}</code>
                        {artifact.truncated ? <em>truncated</em> : null}
                      </li>
                    ))}
                  </ul>
                </dd>
              </div>
            ) : null}
          </dl>
          {counts.length > 0 ? (
            <p className="ask-sources__counts">{counts.join(" · ")}</p>
          ) : null}
        </section>

        {timings ? (
          <section>
            <h4>Time</h4>
            <dl>
              <div>
                <dt>Preparing</dt>
                <dd>
                  {seconds(timings.prepareMs)}
                  <small>cvg snapshot, method, adapter start, session setup</small>
                </dd>
              </div>
              <div>
                <dt>Answering</dt>
                <dd>
                  {seconds(timings.answerMs)}
                  <small>provider thinking and writing</small>
                </dd>
              </div>
              <div>
                <dt>Total</dt>
                <dd>{seconds(timings.totalMs)}</dd>
              </div>
            </dl>
            {context ? (
              <p className="ask-sources__counts">
                {kib(context.contextBytes)} of a {kib(context.maxContextBytes)} budget,
                re-sent in full because every message runs in a fresh session.
              </p>
            ) : null}
          </section>
        ) : null}

        <p className="ask-sources__boundary">
          This is an interpretation read off a snapshot. It is never a gate verdict,
          receipt, or proof — only <code>cvg</code> gate commands produce those.
        </p>
      </div>
    </details>
  );
}

function agentReady(agent: AskAgent | undefined) {
  return agent?.availability === "ready" || agent?.availability === "available";
}

function availabilityLabel(agent: AskAgent) {
  if (agent.availability === "available") return "Installed; auth checked when you ask";
  if (agent.availability === "ready") return "Ready over ACP";
  if (agent.availability === "authentication_required") return "Sign-in required";
  if (agent.availability === "not_configured") return "Adapter not configured";
  if (agent.availability === "blocked") return "Blocked by the safe-access policy";
  return "Unavailable";
}

function compactAvailabilityLabel(agent: AskAgent) {
  if (agent.availability === "available") return "Verify on send";
  if (agent.availability === "ready") return "Ready over ACP";
  if (agent.availability === "authentication_required") return "Sign-in required";
  if (agent.availability === "not_configured") return "Not configured";
  if (agent.availability === "blocked") return "Safe mode blocked";
  return "Unavailable";
}

function scopeLabel(selected: EntityRef | null) {
  return selected ? `${selected.kind}:${selected.id}` : "workspace snapshot";
}

function readableScopeLabel(snapshot: WorkspaceSnapshot, selected: EntityRef | null) {
  const entity = resolveEntity(snapshot, selected);
  if (!entity) return selected ? scopeLabel(selected) : "Workspace snapshot";
  return `${entity.eyebrow}: ${entity.title}`;
}

function contextKey(snapshotId: string, selected: EntityRef | null) {
  return `${snapshotId}:${selected?.kind ?? "workspace"}:${selected?.id ?? "all"}`;
}

function groundingMatches(
  value: unknown,
  snapshot: WorkspaceSnapshot,
  requestedEntity: EntityRef | null,
): value is AskTurnResponse["grounding"] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const candidate = value as Partial<AskTurnResponse["grounding"]>;
  const entity = candidate.entity;
  const entityMatches =
    requestedEntity === null
      ? entity === null
      : entity?.kind === requestedEntity.kind && entity.id === requestedEntity.id;
  const artifacts = candidate.artifacts;
  const methodology = candidate.methodology;
  const methodologyMatches =
    methodology?.tool === "cvg" &&
    methodology.version === snapshot.method.version &&
    typeof methodology.digest === "string" &&
    /^[a-f0-9]{64}$/.test(methodology.digest);
  const artifactMetadataIsValid =
    Array.isArray(artifacts) &&
    artifacts.every(
      (artifact) =>
        typeof artifact?.id === "string" &&
        typeof artifact.label === "string" &&
        typeof artifact.path === "string" &&
        typeof artifact.sha256 === "string" &&
        typeof artifact.truncated === "boolean",
    );
  const selectedArtifact =
    requestedEntity?.kind === "artifact"
      ? snapshot.artifacts.find((artifact) => artifact.id === requestedEntity.id) ?? null
      : null;
  const artifactsMatch =
    artifactMetadataIsValid &&
    (requestedEntity?.kind === "artifact"
      ? selectedArtifact !== null &&
        artifacts.length === 1 &&
        artifacts[0].id === selectedArtifact.id &&
        artifacts[0].path === selectedArtifact.path &&
        artifacts[0].sha256 === selectedArtifact.sha256
      : artifacts.length === 0);
  return (
    candidate.snapshotId === snapshot.snapshotId &&
    typeof candidate.observedAt === "string" &&
    methodologyMatches &&
    entityMatches &&
    artifactsMatch
  );
}

function historyFrom(turns: AskConversationTurn[]) {
  const bounded = (value: string) => {
    const bytes = new TextEncoder().encode(value);
    return bytes.byteLength <= 1_800
      ? value
      : new TextDecoder().decode(bytes.slice(0, 1_800));
  };
  return turns
    .filter((turn) => turn.state === "complete" && turn.response)
    .flatMap((turn) => [
      { role: "user" as const, text: bounded(turn.question) },
      { role: "assistant" as const, text: bounded(turn.response?.answer ?? "") },
    ])
    .slice(-6);
}

/** Selections the composer sends, derived from the agent's advertised options. */
function selectionsFrom(
  options: AskConfigOption[],
  chosen: Record<string, string | boolean>,
): AskConfigSelection[] {
  return options
    .filter((option) => option.settable && Object.hasOwn(chosen, option.id))
    .map((option) => ({
      configId: option.id,
      type: option.type,
      value: chosen[option.id],
    }))
    .filter((selection) =>
      selection.type === "boolean"
        ? typeof selection.value === "boolean"
        : typeof selection.value === "string",
    );
}

function currentValueOf(
  option: AskConfigOption,
  chosen: Record<string, string | boolean>,
) {
  return Object.hasOwn(chosen, option.id) ? chosen[option.id] : option.currentValue;
}

function modelSummary(
  options: AskConfigOption[],
  chosen: Record<string, string | boolean>,
) {
  const model = options.find(
    (option) => option.category === "model" && option.type === "select",
  );
  if (!model) return null;
  const value = currentValueOf(model, chosen);
  if (typeof value !== "string") return null;
  return model.values.find((entry) => entry.value === value)?.name ?? value;
}

export function AskSurface({ snapshot, selected, conversations }: AskSurfaceProps) {
  const [capabilities, setCapabilities] = useState<AskCapabilities>(EMPTY_CAPABILITIES);
  const [agentId, setAgentId] = useState<AskAgent["id"]>("codex");
  const [question, setQuestion] = useState("");
  const [contextRef, setContextRef] = useState<EntityRef | null>(null);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [enginePanelOpen, setEnginePanelOpen] = useState(false);
  const [contextPanelOpen, setContextPanelOpen] = useState(false);
  const [historyPanelOpen, setHistoryPanelOpen] = useState(false);
  const [contextQuery, setContextQuery] = useState("");
  const [configByAgent, setConfigByAgent] = useState<
    Record<string, AskConfigOption[]>
  >({});
  const [configState, setConfigState] = useState<
    Record<string, "idle" | "loading" | "ready" | "unsupported">
  >({});
  const [configError, setConfigError] = useState<string | null>(null);
  const [chosenConfig, setChosenConfig] = useState<
    Record<string, Record<string, string | boolean>>
  >({});
  const requestRef = useRef<{ controller: AbortController; turnId: string } | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const composerRef = useRef<HTMLDivElement | null>(null);
  const projectIdentityRef = useRef(snapshot.project.root);
  const liveContextRef = useRef(contextKey(snapshot.snapshotId, contextRef));
  liveContextRef.current = contextKey(snapshot.snapshotId, contextRef);

  const turns = conversations.active?.turns ?? [];

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoadingAgents(true);
      try {
        const response = await fetch("/api/ask/agents", {
          method: "GET",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`Agent registry unavailable (${response.status})`);
        const candidate = (await response.json()) as Partial<AskCapabilities>;
        if (
          !Array.isArray(candidate.agents) ||
          !candidate.policy ||
          typeof candidate.requestToken !== "string" ||
          candidate.requestToken.length < 16
        ) {
          throw new Error("Agent registry returned an invalid contract");
        }
        setCapabilities(candidate as AskCapabilities);
        const firstReady = candidate.agents.find(agentReady);
        if (firstReady) setAgentId(firstReady.id);
        setRegistryError(null);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setCapabilities(EMPTY_CAPABILITIES);
        setRegistryError(error instanceof Error ? error.message : "Agent registry unavailable");
      } finally {
        setLoadingAgents(false);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (projectIdentityRef.current === snapshot.project.root) return;
    projectIdentityRef.current = snapshot.project.root;
    requestRef.current?.controller.abort();
    requestRef.current = null;
    conversations.clearAll();
    setQuestion("");
    setContextRef(null);
    setConfigByAgent({});
    setConfigState({});
    setChosenConfig({});
  }, [conversations, snapshot.project.root]);

  useEffect(
    () => () => {
      requestRef.current?.controller.abort();
    },
    [],
  );

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 220)}px`;
    textarea.style.overflowY = textarea.scrollHeight > 220 ? "auto" : "hidden";
  }, [question]);

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (!transcript) return;
    if (turns.length === 0) {
      if (typeof transcript.scrollTo === "function") {
        transcript.scrollTo({ top: 0, behavior: "auto" });
      } else {
        transcript.scrollTop = 0;
      }
      return;
    }
    if (typeof transcript.scrollTo === "function") {
      transcript.scrollTo({ top: transcript.scrollHeight, behavior: "smooth" });
    } else {
      transcript.scrollTop = transcript.scrollHeight;
    }
  }, [turns.length]);

  // Dismiss the composer popovers on outside click or Escape.
  useEffect(() => {
    if (!enginePanelOpen && !contextPanelOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (composerRef.current?.contains(event.target as Node)) return;
      setEnginePanelOpen(false);
      setContextPanelOpen(false);
    }
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key !== "Escape") return;
      setEnginePanelOpen(false);
      setContextPanelOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [contextPanelOpen, enginePanelOpen]);

  const selectedAgent = useMemo(
    () => capabilities.agents.find((agent) => agent.id === agentId) ?? capabilities.agents[0],
    [agentId, capabilities.agents],
  );
  const replay = snapshot.source === "fixture";
  const asking = turns.some((turn) => turn.state === "pending");
  const requestedEntity = contextRef;
  const alternateAgent = capabilities.agents.find(
    (agent) => agent.id !== selectedAgent?.id && agentReady(agent),
  );
  const visibleSuggestions = useMemo(
    () => suggestionsFor(snapshot, requestedEntity),
    [snapshot, requestedEntity],
  );
  const contextCandidates = useMemo(
    () => askContextCandidates(snapshot),
    [snapshot],
  );
  const filteredCandidates = useMemo(
    () => filterContextCandidates(contextCandidates, contextQuery),
    [contextCandidates, contextQuery],
  );
  const activeOptions = configByAgent[agentId] ?? [];
  const activeChosen = chosenConfig[agentId] ?? {};
  const settableOptions = activeOptions.filter((option) => option.settable);
  const activeModel = modelSummary(activeOptions, activeChosen);
  const canAsk =
    !replay &&
    !asking &&
    question.trim().length >= 2 &&
    agentReady(selectedAgent);

  /**
   * Reads the model and reasoning selectors the agent advertises. Deferred until
   * the picker is opened so no adapter process is spawned just by visiting Ask.
   */
  async function loadAgentConfig(targetId: AskAgent["id"]) {
    if (configState[targetId] === "loading" || configByAgent[targetId]) return;
    const agent = capabilities.agents.find((candidate) => candidate.id === targetId);
    if (!agentReady(agent) || !capabilities.requestToken) return;
    setConfigState((current) => ({ ...current, [targetId]: "loading" }));
    setConfigError(null);
    try {
      const response = await fetch("/api/ask/options", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-Converge-Request": "ask-v1",
          "X-Converge-CSRF": capabilities.requestToken,
        },
        body: JSON.stringify({ agentId: targetId }),
      });
      const body = (await response.json()) as {
        configOptions?: AskConfigOption[];
        error?: { message?: string };
      };
      if (!response.ok) {
        throw new Error(
          body.error?.message ?? "The agent did not report its model options.",
        );
      }
      const options = Array.isArray(body.configOptions) ? body.configOptions : [];
      setConfigByAgent((current) => ({ ...current, [targetId]: options }));
      setConfigState((current) => ({
        ...current,
        [targetId]: options.some((option) => option.settable) ? "ready" : "unsupported",
      }));
    } catch (error) {
      setConfigState((current) => ({ ...current, [targetId]: "idle" }));
      setConfigError(
        error instanceof Error ? error.message : "Model options are unavailable.",
      );
    }
  }

  function toggleEnginePanel() {
    const next = !enginePanelOpen;
    setEnginePanelOpen(next);
    setContextPanelOpen(false);
    if (next) void loadAgentConfig(agentId);
  }

  function chooseAgent(nextId: AskAgent["id"]) {
    // The unusable engines are `aria-disabled`, not `disabled`, so they still
    // receive clicks: readiness has to be enforced here rather than by the DOM.
    const agent = capabilities.agents.find((candidate) => candidate.id === nextId);
    if (!agentReady(agent)) return;
    setAgentId(nextId);
    void loadAgentConfig(nextId);
  }

  function chooseConfigValue(optionId: string, value: string | boolean) {
    setChosenConfig((current) => ({
      ...current,
      [agentId]: { ...(current[agentId] ?? {}), [optionId]: value },
    }));
  }

  function patchTurn(turnId: string, patch: Partial<AskConversationTurn>) {
    conversations.patchTurn(turnId, patch);
  }

  function stopTurn() {
    const active = requestRef.current;
    if (!active) return;
    active.controller.abort();
    requestRef.current = null;
    patchTurn(active.turnId, {
      state: "cancelled",
      error: {
        code: "ASK_CANCELLED",
        message: "Stopped before the provider completed the response.",
        retryable: true,
      },
    });
  }

  function startNewConversation() {
    stopTurn();
    conversations.startConversation();
    setQuestion("");
    // A new chat starts unscoped: carrying the previous question's entity into a
    // fresh conversation would silently narrow an answer the reader did not ask
    // to narrow.
    setContextRef(null);
    setContextQuery("");
    setHistoryPanelOpen(false);
    setEnginePanelOpen(false);
    setContextPanelOpen(false);
    textareaRef.current?.focus();
  }

  function openConversation(id: string) {
    stopTurn();
    conversations.selectConversation(id);
    setHistoryPanelOpen(false);
  }

  function chooseSuggestion(suggestion: string) {
    setQuestion(suggestion);
    textareaRef.current?.focus();
  }

  function chooseContext(next: EntityRef | null) {
    setContextRef(next);
    setContextPanelOpen(false);
    setContextQuery("");
  }

  function retryTurn(turn: AskConversationTurn) {
    setQuestion(turn.question);
    textareaRef.current?.focus();
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!canAsk || !selectedAgent) return;

    const text = question.trim();
    const turnId = `turn-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const turn: AskConversationTurn = {
      id: turnId,
      agentId: selectedAgent.id,
      question: text,
      scope: requestedEntity,
      state: "pending",
      response: null,
      error: null,
    };
    const priorHistory = historyFrom(turns);
    conversations.appendTurn(turn);
    setQuestion("");
    const controller = new AbortController();
    requestRef.current = { controller, turnId };
    const requestedContext = contextKey(snapshot.snapshotId, requestedEntity);
    const config = selectionsFrom(activeOptions, activeChosen);

    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-Converge-Request": "ask-v1",
          "X-Converge-CSRF": capabilities.requestToken,
        },
        body: JSON.stringify({
          agentId: selectedAgent.id,
          snapshotId: snapshot.snapshotId,
          text,
          history: priorHistory,
          context: {
            entity: requestedEntity,
            artifactIds:
              requestedEntity?.kind === "artifact" ? [requestedEntity.id] : [],
          },
          ...(config.length > 0 ? { config } : {}),
        }),
        signal: controller.signal,
      });
      let body: Partial<AskTurnResponse> | {
        error?: { code?: string; message?: string; retryable?: boolean };
      } = {};
      try {
        body = await response.json() as typeof body;
      } catch {
        // Preserve a stable recovery message when an upstream response is empty
        // or malformed instead of surfacing a JSON parser exception.
      }
      if (!response.ok) {
        const failure = "error" in body ? body.error : undefined;
        throw new AskRequestError({
          code: failure?.code ?? "ASK_AGENT_FAILED",
          message:
            failure?.message ??
            "The selected agent did not return a valid response. Try again or choose another available engine.",
          retryable: failure?.retryable ?? response.status >= 500,
        });
      }
      if (
        !("answer" in body) ||
        typeof body.answer !== "string" ||
        body.snapshotId !== snapshot.snapshotId ||
        body.agentId !== selectedAgent.id ||
        !groundingMatches(body.grounding, snapshot, requestedEntity) ||
        !Array.isArray(body.steps) ||
        !Array.isArray(body.activity)
      ) {
        throw new Error("The agent response was not bound to this workspace snapshot.");
      }
      if (requestedEntity && liveContextRef.current !== requestedContext) {
        throw new Error("The selected project context changed before the answer completed.");
      }
      patchTurn(turnId, {
        state: "complete",
        response: body as AskTurnResponse,
        error: null,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      patchTurn(turnId, {
        state: "error",
        error:
          error instanceof AskRequestError
            ? { code: error.code, message: error.message, retryable: error.retryable }
            : {
                code: "ASK_AGENT_FAILED",
                message:
                  error instanceof Error
                    ? error.message
                    : "The agent could not answer this question.",
                retryable: true,
              },
      });
    } finally {
      if (requestRef.current?.controller === controller) requestRef.current = null;
    }
  }

  function composerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    formRef.current?.requestSubmit();
  }

  const historyCount = conversations.history.length;

  return (
    <section
      className={`surface surface--ask ask-chat${turns.length === 0 ? " ask-chat--empty" : ""}`}
      aria-labelledby="ask-title"
    >
      <header className="ask-chat__header">
        <div className="ask-chat__identity">
          <h1 id="ask-title">Ask</h1>
          <span>Converge and {snapshot.project.name}</span>
        </div>
        <div className="ask-chat__header-actions">
          <button
            type="button"
            className={`ask-header-button${historyPanelOpen ? " is-open" : ""}`}
            onClick={() => setHistoryPanelOpen((open) => !open)}
            aria-expanded={historyPanelOpen}
            aria-label={`Conversation history, ${historyCount} saved`}
          >
            <ClockCounterClockwise aria-hidden="true" />
            History
            {historyCount > 0 ? <em>{historyCount}</em> : null}
          </button>
          <button
            type="button"
            className="ask-new-chat"
            onClick={startNewConversation}
            aria-label="Start new chat"
          >
            <Plus aria-hidden="true" />
            New chat
          </button>
        </div>
      </header>

      {historyPanelOpen ? (
        <div className="ask-history" role="region" aria-label="Conversation history">
          {historyCount === 0 ? (
            <p className="ask-history__empty">
              Conversations you start appear here for this session. They are kept in
              memory only and are never written to disk.
            </p>
          ) : (
            <ul>
              {conversations.history.map((conversation) => (
                <li key={conversation.id}>
                  <button
                    type="button"
                    className={
                      conversation.id === conversations.activeId ? "is-active" : ""
                    }
                    onClick={() => openConversation(conversation.id)}
                  >
                    <strong>{conversation.title}</strong>
                    <small>
                      {conversation.turns.length}{" "}
                      {conversation.turns.length === 1 ? "question" : "questions"}
                    </small>
                  </button>
                  <button
                    type="button"
                    className="ask-history__delete"
                    onClick={() => conversations.deleteConversation(conversation.id)}
                    aria-label={`Delete conversation ${conversation.title}`}
                  >
                    <Trash aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      <div className="ask-chat__transcript" ref={transcriptRef} aria-live="polite">
        {turns.length === 0 ? (
          <div className="ask-hero">
            <img
              className="ask-hero__mark"
              src="/brand/converge-icon-color-light.svg"
              alt=""
              width={64}
              height={64}
              draggable={false}
              aria-hidden="true"
            />
            <h2>What should we explore in {snapshot.project.name}?</h2>
            <p>Ask about the method, decisions, delivery, execution, or proof.</p>
            {/* Openers sit with the invitation they answer, above the composer,
                rather than stranded below the input. */}
            <div className="ask-suggestions" aria-label="Suggested questions">
              {visibleSuggestions.map((suggestion) => (
                <button
                  type="button"
                  key={suggestion.question}
                  onClick={() => chooseSuggestion(suggestion.question)}
                >
                  <span>
                    <strong>{suggestion.question}</strong>
                    <small>{suggestion.label}</small>
                  </span>
                  <ArrowRight aria-hidden="true" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="ask-thread">
            {turns.map((turn) => {
              const agent = capabilities.agents.find((candidate) => candidate.id === turn.agentId);
              const engine = turn.response?.engine ?? [];
              return (
                <article className="ask-turn" key={turn.id}>
                  <div className="ask-turn__user">
                    <div className="ask-bubble">
                      <p>{turn.question}</p>
                      {turn.scope ? <small>{scopeLabel(turn.scope)}</small> : null}
                    </div>
                  </div>
                  <div className="ask-reply">
                    <header className="ask-reply__provider">
                      <AgentMark id={turn.agentId} />
                      <strong>{agent?.label ?? turn.agentId}</strong>
                      {engine.length > 0 ? (
                        <span className="ask-reply__engine">
                          {engine.map((entry) => entry.label).filter(Boolean).join(" · ")}
                        </span>
                      ) : null}
                      <small>via ACP</small>
                    </header>
                    {turn.state === "pending" ? (
                      <div className="ask-thinking-line" role="status">
                        <CircleNotch className="status-glyph--spin" aria-hidden="true" />
                        <span>Reading Converge and the live project context...</span>
                      </div>
                    ) : null}
                    {turn.state === "cancelled" ? (
                      <div className="ask-reply__error is-cancelled">
                        <Stop weight="fill" aria-hidden="true" />
                        {turn.error?.message}
                      </div>
                    ) : null}
                    {turn.state === "error" ? (
                      <div className="ask-reply__error" role="alert">
                        <WarningCircle weight="fill" aria-hidden="true" />
                        <div className="ask-reply__error-copy">
                          <strong>{turn.error?.message}</strong>
                          <span className="ask-reply__recovery">
                            {turn.error?.retryable ? (
                              <button type="button" onClick={() => retryTurn(turn)}>
                                Try again
                              </button>
                            ) : null}
                            {alternateAgent ? (
                              <button type="button" onClick={() => chooseAgent(alternateAgent.id)}>
                                Use {alternateAgent.label}
                              </button>
                            ) : null}
                          </span>
                        </div>
                      </div>
                    ) : null}
                    {turn.response ? (
                      <>
                        <div className="ask-reply__answer">
                          <Markdown
                            remarkPlugins={[remarkGfm]}
                            components={askMarkdownComponents}
                            skipHtml
                          >
                            {turn.response.answer}
                          </Markdown>
                        </div>
                        {turn.response.steps.length > 0 ? (
                          <details className="ask-response-details">
                            <summary>{turn.response.steps.length} explanation steps</summary>
                            <ol>
                              {turn.response.steps.map((step, index) => (
                                <li key={`${index}-${step}`}><span>{index + 1}</span><p>{step}</p></li>
                              ))}
                            </ol>
                          </details>
                        ) : null}
                        {turn.response.activity.length > 0 ? (
                          <details className="ask-response-details">
                            <summary>{turn.response.activity.length} bounded activities</summary>
                            <ol>
                              {turn.response.activity.map((item) => (
                                <li key={item.id}>
                                  <span><Check aria-hidden="true" /></span>
                                  <p><strong>{item.label}</strong>{item.detail ? `: ${item.detail}` : ""}</p>
                                </li>
                              ))}
                            </ol>
                          </details>
                        ) : null}
                        <AskSources response={turn.response} />
                      </>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>

      <div className="ask-chat__composer-zone" ref={composerRef}>
        {registryError ? (
          <div className="ask-inline-state" role="alert">
            <WarningCircle weight="fill" aria-hidden="true" /> {registryError}
          </div>
        ) : null}
        {selectedAgent && !agentReady(selectedAgent) ? (
          <div className="ask-inline-state" role="status">
            <CloudSlash weight="fill" aria-hidden="true" />
            <span><strong>{selectedAgent.label} cannot start safely.</strong> {selectedAgent.reason ?? availabilityLabel(selectedAgent)}</span>
            {alternateAgent ? (
              <button
                type="button"
                className="ask-inline-state__action"
                onClick={() => chooseAgent(alternateAgent.id)}
              >
                Use {alternateAgent.label}
                <ArrowRight aria-hidden="true" />
              </button>
            ) : null}
          </div>
        ) : null}
        {replay ? (
          <div className="ask-inline-state" role="status">
            <LockKey weight="fill" aria-hidden="true" /> Connect a live workspace to ask an ACP agent.
          </div>
        ) : null}

        <form ref={formRef} className="ask-composer" onSubmit={submit}>
          <textarea
            ref={textareaRef}
            value={question}
            onChange={(event) => setQuestion(event.target.value.slice(0, 8000))}
            onKeyDown={composerKeyDown}
            placeholder="Ask about the project or the Converge method..."
            aria-label="Question for the selected ACP agent"
            disabled={replay || loadingAgents}
            rows={1}
          />
          <div className="ask-composer__bar">
            <div className="ask-composer__tools">
              <div className="ask-popover-anchor">
                <button
                  type="button"
                  className={`ask-engine-button${enginePanelOpen ? " is-open" : ""}`}
                  onClick={toggleEnginePanel}
                  disabled={loadingAgents}
                  aria-expanded={enginePanelOpen}
                  aria-haspopup="dialog"
                  aria-label={`Engine and model: ${selectedAgent?.label ?? "none"}${
                    activeModel ? `, ${activeModel}` : ""
                  }`}
                >
                  <AgentMark id={selectedAgent?.id ?? "claude"} />
                  <span className="ask-engine-button__copy">
                    <strong>{selectedAgent?.label ?? "Engine"}</strong>
                    <small>
                      {loadingAgents
                        ? "Checking"
                        : activeModel ??
                          (selectedAgent ? compactAvailabilityLabel(selectedAgent) : "")}
                    </small>
                  </span>
                  <CaretDown aria-hidden="true" />
                </button>
                {enginePanelOpen ? (
                  <div className="ask-popover" role="dialog" aria-label="Engine and model">
                    {/* The engine choices stay a named group so the picker keeps one
                        stable accessible identity as the visual design moves. */}
                    <div
                      className="ask-popover__engine-group"
                      role="group"
                      aria-label="Choose ACP agent"
                    >
                      <p className="ask-popover__title">Engine</p>
                      <ul className="ask-popover__engines">
                        {capabilities.agents.map((agent) => {
                          const ready = agentReady(agent);
                          return (
                            <li key={agent.id}>
                              <button
                                type="button"
                                className={agent.id === agentId ? "is-active" : ""}
                                onClick={() => chooseAgent(agent.id)}
                                /*
                                 * An unusable engine stays focusable and announces why.
                                 * `disabled` would drop it out of the tab order, so the
                                 * one place that explains the safe-mode block would be
                                 * unreachable by keyboard and screen reader alike.
                                 */
                                aria-disabled={!ready}
                                aria-pressed={agent.id === agentId}
                                aria-label={`${agent.label}, ${availabilityLabel(agent)}`}
                              >
                                <AgentMark id={agent.id} />
                                <span>
                                  <strong>{agent.label}</strong>
                                  <small>{compactAvailabilityLabel(agent)}</small>
                                </span>
                                {agent.id === agentId ? <Check aria-hidden="true" /> : null}
                              </button>
                              {/* A blocked engine explains itself instead of being a
                                  dressed-up disabled button. */}
                              {agent.availability === "blocked" && agent.reason ? (
                                <p className="ask-popover__blocked">{agent.reason}</p>
                              ) : null}
                            </li>
                          );
                        })}
                      </ul>
                    </div>

                    {configState[agentId] === "loading" ? (
                      <p className="ask-popover__note">
                        <CircleNotch className="status-glyph--spin" aria-hidden="true" />
                        Reading the options this agent offers…
                      </p>
                    ) : null}
                    {configError ? (
                      <p className="ask-popover__note is-error">{configError}</p>
                    ) : null}
                    {configState[agentId] === "unsupported" ? (
                      <p className="ask-popover__note">
                        This agent does not advertise selectable models over ACP.
                      </p>
                    ) : null}

                    {settableOptions.map((option) => {
                      const value = currentValueOf(option, activeChosen);
                      return (
                        <div className="ask-popover__group" key={option.id}>
                          <p className="ask-popover__title">
                            {option.category === "model" ? <Cube aria-hidden="true" /> : <Sliders aria-hidden="true" />}
                            {option.name}
                          </p>
                          {option.type === "boolean" ? (
                            <label className="ask-toggle">
                              <input
                                type="checkbox"
                                checked={value === true}
                                onChange={(event) =>
                                  chooseConfigValue(option.id, event.target.checked)
                                }
                              />
                              <span>{option.description ?? option.name}</span>
                            </label>
                          ) : (
                            <ul className="ask-popover__values">
                              {option.values.map((entry) => (
                                <li key={entry.value}>
                                  <button
                                    type="button"
                                    className={entry.value === value ? "is-active" : ""}
                                    onClick={() => chooseConfigValue(option.id, entry.value)}
                                    aria-pressed={entry.value === value}
                                  >
                                    <span>
                                      <strong>{entry.name}</strong>
                                      {entry.description ? <small>{entry.description}</small> : null}
                                    </span>
                                    {entry.value === value ? <Check aria-hidden="true" /> : null}
                                  </button>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>

              <div className="ask-popover-anchor">
                <button
                  type="button"
                  className={`ask-context-button${contextPanelOpen ? " is-open" : ""}${contextRef ? " has-context" : ""}`}
                  onClick={() => {
                    setContextPanelOpen((open) => !open);
                    setEnginePanelOpen(false);
                  }}
                  aria-expanded={contextPanelOpen}
                  aria-haspopup="dialog"
                  aria-label={`Question context: ${
                    contextRef ? readableScopeLabel(snapshot, contextRef) : "Whole workspace"
                  }`}
                >
                  <MagnifyingGlass aria-hidden="true" />
                  {contextRef ? readableScopeLabel(snapshot, contextRef) : "Whole workspace"}
                  <CaretDown aria-hidden="true" />
                </button>
                {contextRef ? (
                  <button
                    type="button"
                    className="ask-context-clear"
                    onClick={() => chooseContext(null)}
                    aria-label="Ask about the whole workspace instead"
                  >
                    <X aria-hidden="true" />
                  </button>
                ) : null}
                {contextPanelOpen ? (
                  <div className="ask-popover" role="dialog" aria-label="Question context">
                    <p className="ask-popover__title">What this question is about</p>
                    <p className="ask-popover__hint">
                      Every question already carries the Converge method and the full
                      workspace snapshot. Naming one entity adds its detail
                      {contextRef?.kind === "artifact" ? " and document text" : ""}, and
                      focuses the answer.
                    </p>
                    <input
                      type="search"
                      className="ask-popover__search"
                      value={contextQuery}
                      onChange={(event) => setContextQuery(event.target.value.slice(0, 120))}
                      placeholder="Search passes, legs, tasks, artifacts…"
                      aria-label="Search workspace entities"
                    />
                    <ul className="ask-popover__values">
                      <li>
                        <button
                          type="button"
                          className={contextRef === null ? "is-active" : ""}
                          onClick={() => chooseContext(null)}
                        >
                          <span>
                            <strong>Whole workspace</strong>
                            <small>Method plus the entire observed snapshot</small>
                          </span>
                          {contextRef === null ? <Check aria-hidden="true" /> : null}
                        </button>
                      </li>
                      {selected && !sameEntity(selected, contextRef) ? (
                        <li>
                          <button type="button" onClick={() => chooseContext(selected)}>
                            <span>
                              <strong>{readableScopeLabel(snapshot, selected)}</strong>
                              <small>Selected elsewhere in Cockpit</small>
                            </span>
                          </button>
                        </li>
                      ) : null}
                      {filteredCandidates.map((candidate) => (
                        <li key={candidate.key}>
                          <button
                            type="button"
                            className={sameEntity(candidate.ref, contextRef) ? "is-active" : ""}
                            onClick={() => chooseContext(candidate.ref)}
                            aria-pressed={sameEntity(candidate.ref, contextRef)}
                          >
                            <span>
                              <strong>{candidate.title}</strong>
                              <small>{candidate.eyebrow}</small>
                            </span>
                            {sameEntity(candidate.ref, contextRef) ? (
                              <Check aria-hidden="true" />
                            ) : null}
                          </button>
                        </li>
                      ))}
                      {filteredCandidates.length === 0 ? (
                        <li className="ask-popover__empty">
                          No entity in this snapshot matches that search.
                        </li>
                      ) : null}
                    </ul>
                  </div>
                ) : null}
              </div>
            </div>
            <div className="ask-composer__actions">
              <span className="ask-composer__hint">
                {question.length >= 7_000
                  ? `${question.length.toLocaleString()} / 8,000`
                  : "Enter to send"}
              </span>
              {asking ? (
                <button type="button" className="ask-send ask-send--stop" onClick={stopTurn} aria-label="Stop response">
                  <Stop weight="fill" aria-hidden="true" />
                </button>
              ) : (
                <button type="submit" className="ask-send" disabled={!canAsk} aria-label="Send question">
                  <ArrowUp weight="bold" aria-hidden="true" />
                </button>
              )}
            </div>
          </div>
        </form>

        <div className="ask-session-boundary" aria-label="Ask evidence boundary">
          <ShieldCheck weight="fill" aria-hidden="true" />
          <span>
            Read-only ACP. Converge {snapshot.method.version} / snapshot {snapshot.snapshotId.slice(0, 12)}. Answers are interpretation, never a gate verdict.
          </span>
        </div>
      </div>
    </section>
  );
}
