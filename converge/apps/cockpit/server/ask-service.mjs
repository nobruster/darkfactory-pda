import { randomUUID } from "node:crypto";

import {
  ASK_LIMITS,
  AskError,
  parseAskSessionId,
  parseAskTurnRequest,
  parseCreateAskSessionRequest,
  publicAskError,
  utf8Length,
} from "./ask-contract.mjs";
import { buildAskContext, composeAskPrompt } from "./ask-context.mjs";
import { AcpClient, AcpClientError } from "./acp/client.mjs";

function externalId(prefix, idFactory) {
  return `${prefix}_${String(idFactory()).replaceAll("-", "")}`;
}

function mapClientError(error) {
  if (error instanceof AskError) return error;
  if (!(error instanceof AcpClientError)) {
    return new AskError("ASK_AGENT_FAILED", { cause: error });
  }
  const mapping = {
    ACP_ADAPTER_UNAVAILABLE: "ASK_AGENT_UNAVAILABLE",
    ACP_ADAPTER_EXITED: "ASK_AGENT_FAILED",
    ACP_AUTH_REQUIRED: "ASK_AUTH_REQUIRED",
    ACP_AUTH_UNSUPPORTED: "ASK_AUTH_UNSUPPORTED",
    ACP_CONFIG_REJECTED: "ASK_CONFIG_REJECTED",
    ACP_OUTPUT_LIMIT: "ASK_OUTPUT_LIMIT",
    ACP_PROTOCOL_MISMATCH: "ASK_PROTOCOL_MISMATCH",
    ACP_SAFE_MODE_UNAVAILABLE: "ASK_AGENT_UNAVAILABLE",
    ACP_TIMEOUT: "ASK_TIMEOUT",
    ACP_UNSAFE_TOOL: "ASK_AGENT_FAILED",
  };
  return new AskError(mapping[error.code] ?? "ASK_AGENT_FAILED", { cause: error });
}

function sanitizeModes(modes) {
  if (!modes || typeof modes.currentModeId !== "string") return null;
  return Object.freeze({
    currentModeId: modes.currentModeId,
    availableModes: Object.freeze(
      (Array.isArray(modes.availableModes) ? modes.availableModes : [])
        .slice(0, 24)
        .filter((mode) => typeof mode?.id === "string" && typeof mode?.name === "string")
        .map((mode) => Object.freeze({
          id: mode.id,
          name: mode.name,
          description: typeof mode.description === "string" ? mode.description : null,
        })),
    ),
  });
}

export class AskService {
  constructor({
    registry,
    snapshotService,
    artifactStore,
    methodologyProvider,
    clientFactory = (options) => new AcpClient(options),
    idFactory = randomUUID,
    now = () => Date.now(),
    maxSessions = 4,
    sessionTtlMs = 10 * 60 * 1000,
    maxEvents = ASK_LIMITS.maxEvents,
    maxEventBytes = ASK_LIMITS.maxEventBytes,
  }) {
    if (!registry?.get || !registry?.list) {
      throw new TypeError("AskService requires an AgentRegistry");
    }
    if (!snapshotService?.getSnapshot) {
      throw new TypeError("AskService requires a SnapshotService");
    }
    if (typeof clientFactory !== "function") {
      throw new TypeError("AskService requires a client factory");
    }
    if (typeof methodologyProvider !== "function") {
      throw new TypeError("AskService requires a methodology provider");
    }
    this.registry = registry;
    this.snapshotService = snapshotService;
    this.artifactStore = artifactStore;
    this.methodologyProvider = methodologyProvider;
    this.clientFactory = clientFactory;
    this.idFactory = idFactory;
    this.now = now;
    this.maxSessions = maxSessions;
    this.sessionTtlMs = sessionTtlMs;
    this.maxEvents = maxEvents;
    this.maxEventBytes = maxEventBytes;
    this.sessions = new Map();
  }

  async listAgents() {
    return Object.freeze({
      schemaVersion: "1.0",
      agents: Object.freeze(await this.registry.list()),
    });
  }

  /**
   * Opens a disposable ACP session purely to read the model and reasoning
   * selectors the agent advertises, then tears it down. No prompt is sent, so
   * this costs a process spawn and zero model tokens. It is what lets the
   * composer show real options before the first question is asked.
   */
  async probeAgentConfig(agentId) {
    const adapter = this.registry.get(agentId);
    if (!adapter) throw new AskError("ASK_AGENT_NOT_FOUND");
    if (adapter.contextIsolation !== "verified") {
      throw new AskError("ASK_AGENT_UNAVAILABLE");
    }
    const client = this.clientFactory({ adapter, onEvent: () => true });
    try {
      const connection = await client.connect();
      const session = await client.createSession();
      return Object.freeze({
        schemaVersion: "1.0",
        agentId,
        agentInfo: connection.agentInfo ?? null,
        configOptions: session.configOptions ?? Object.freeze([]),
      });
    } catch (error) {
      throw mapClientError(error);
    } finally {
      await client.close();
    }
  }

  async createSession(candidate) {
    const request = parseCreateAskSessionRequest(candidate);
    await this.#removeExpired();
    if (this.sessions.size >= this.maxSessions) {
      throw new AskError("ASK_SESSION_LIMIT");
    }
    const adapter = this.registry.get(request.agentId);
    if (!adapter) throw new AskError("ASK_AGENT_NOT_FOUND");
    if (adapter.contextIsolation !== "verified") {
      throw new AskError("ASK_AGENT_UNAVAILABLE");
    }
    const envelope = await this.#currentSnapshot();
    let methodology;
    try {
      methodology = await this.methodologyProvider();
    } catch (error) {
      throw new AskError("ASK_METHODOLOGY_UNAVAILABLE", { cause: error });
    }
    const askContext = await buildAskContext({
      envelope,
      snapshotId: request.snapshotId,
      context: request.context,
      artifactStore: this.artifactStore,
      methodology,
    });
    const sessionId = externalId("ask", this.idFactory);
    const record = {
      id: sessionId,
      agentId: request.agentId,
      adapter,
      state: "initializing",
      createdAt: this.now(),
      expiresAt: this.now() + this.sessionTtlMs,
      grounding: askContext.grounding,
      stats: askContext.stats,
      contextText: askContext.contextText,
      client: null,
      connection: null,
      acpSessionId: null,
      modes: null,
      configOptions: Object.freeze([]),
      events: [],
      eventBytes: 0,
      nextSequence: 1,
      activeTurnId: null,
      turnPromise: null,
      turnUsed: false,
      cancelRequested: false,
      outputExceeded: false,
    };
    const client = this.clientFactory({
      adapter,
      onEvent: (event) => this.#appendProviderEvent(record, event),
    });
    record.client = client;
    this.sessions.set(sessionId, record);
    try {
      record.connection = await client.connect();
      const acpSession = await client.createSession();
      record.acpSessionId = acpSession.sessionId;
      record.modes = sanitizeModes(acpSession.modes);
      record.configOptions = acpSession.configOptions ?? Object.freeze([]);
      // Selections are applied to the fresh session before any prompt, which
      // keeps one disposable session per turn while still honouring the chosen
      // model and reasoning level.
      for (const selection of request.config) {
        record.configOptions = await client.setConfigOption(selection);
      }
      record.state = "ready";
      return this.#sessionDocument(record);
    } catch (error) {
      this.sessions.delete(sessionId);
      await client.close();
      throw mapClientError(error);
    }
  }

  getSession(sessionId) {
    const record = this.#requireSession(sessionId);
    return this.#sessionDocument(record);
  }

  async startTurn(sessionId, candidate) {
    const record = this.#requireSession(sessionId);
    const request = parseAskTurnRequest(candidate);
    if (record.activeTurnId) throw new AskError("ASK_BUSY");
    if (record.turnUsed) throw new AskError("ASK_TURN_ALREADY_USED");
    const envelope = await this.#currentSnapshot();
    if (
      request.snapshotId !== record.grounding.snapshotId ||
      envelope.snapshot.snapshotId !== record.grounding.snapshotId ||
      envelope.transport?.stale === true
    ) {
      throw new AskError("ASK_SNAPSHOT_STALE");
    }
    const turnId = externalId("turn", this.idFactory);
    record.activeTurnId = turnId;
    record.turnUsed = true;
    record.cancelRequested = false;
    record.outputExceeded = false;
    record.state = "running";
    this.#appendInternalEvent(record, {
      type: "turn.started",
      payload: Object.freeze({
        grounding: record.grounding,
        source: "agent_interpretation",
      }),
    });
    const prompt = composeAskPrompt(record.contextText, request.text, request.history);
    record.turnPromise = this.#runTurn(record, prompt);
    return Object.freeze({
      schemaVersion: "1.0",
      sessionId: record.id,
      turnId,
      state: "running",
    });
  }

  getEvents(sessionId, { after = 0 } = {}) {
    const record = this.#requireSession(sessionId);
    if (!Number.isInteger(after) || after < 0) {
      throw new AskError("ASK_INVALID_REQUEST");
    }
    return Object.freeze({
      schemaVersion: "1.0",
      sessionId: record.id,
      state: record.state,
      events: Object.freeze(record.events.filter((event) => event.sequence > after)),
      nextSequence: record.nextSequence,
    });
  }

  async cancelTurn(sessionId, turnId) {
    const record = this.#requireSession(sessionId);
    if (!record.activeTurnId || record.activeTurnId !== turnId) {
      throw new AskError("ASK_INVALID_REQUEST");
    }
    record.cancelRequested = true;
    await record.client.cancel();
    return Object.freeze({
      schemaVersion: "1.0",
      sessionId: record.id,
      turnId,
      state: "cancelling",
    });
  }

  async waitForTurn(sessionId) {
    const record = this.#requireSession(sessionId);
    await record.turnPromise;
    if (record.state === "completed") {
      const envelope = await this.#currentSnapshot();
      if (
        envelope.transport?.stale === true ||
        envelope.snapshot.snapshotId !== record.grounding.snapshotId
      ) {
        const stale = new AskError("ASK_SNAPSHOT_STALE");
        record.state = "failed";
        this.#appendInternalEvent(record, {
          type: "turn.failed",
          payload: publicAskError(stale).document.error,
        });
        throw stale;
      }
    }
    return this.#sessionDocument(record);
  }

  async deleteSession(sessionId) {
    const record = this.#requireSession(sessionId);
    this.sessions.delete(record.id);
    await record.client.close();
    return Object.freeze({ schemaVersion: "1.0", deleted: true, sessionId: record.id });
  }

  async close() {
    const records = [...this.sessions.values()];
    this.sessions.clear();
    await Promise.allSettled(records.map((record) => record.client.close()));
  }

  async #runTurn(record, prompt) {
    try {
      const result = await record.client.prompt(prompt);
      if (record.outputExceeded) throw new AskError("ASK_OUTPUT_LIMIT");
      record.state = result.stopReason === "cancelled" ? "cancelled" : "completed";
      this.#appendInternalEvent(record, {
        type: "turn.completed",
        payload: Object.freeze({ stopReason: result.stopReason }),
      });
    } catch (error) {
      const typed = record.outputExceeded
        ? new AskError("ASK_OUTPUT_LIMIT", { cause: error })
        : record.cancelRequested
          ? new AskError("ASK_CANCELLED", { cause: error })
          : mapClientError(error);
      record.state = typed.code === "ASK_CANCELLED" ? "cancelled" : "failed";
      this.#appendInternalEvent(record, {
        type: "turn.failed",
        payload: publicAskError(typed).document.error,
      });
    } finally {
      record.activeTurnId = null;
      await record.client.close();
    }
  }

  async #currentSnapshot() {
    try {
      return await this.snapshotService.getSnapshot({ fresh: true });
    } catch (error) {
      throw new AskError("ASK_AGENT_FAILED", { cause: error });
    }
  }

  #sessionDocument(record) {
    return Object.freeze({
      schemaVersion: "1.0",
      session: Object.freeze({
        id: record.id,
        agentId: record.agentId,
        protocolVersion: record.connection?.protocolVersion ?? null,
        state: record.state,
        createdAt: new Date(record.createdAt).toISOString(),
        expiresAt: new Date(record.expiresAt).toISOString(),
        grounding: record.grounding,
        agentInfo: record.connection?.agentInfo ?? null,
        capabilities: record.connection?.capabilities ?? null,
        authMethods: record.connection?.authMethods ?? Object.freeze([]),
        modes: record.modes,
        configOptions: record.configOptions,
        stats: record.stats,
      }),
    });
  }

  #requireSession(sessionId) {
    const id = parseAskSessionId(sessionId);
    const record = this.sessions.get(id);
    if (!record) throw new AskError("ASK_SESSION_NOT_FOUND");
    if (record.expiresAt <= this.now()) {
      this.sessions.delete(id);
      void record.client.close();
      throw new AskError("ASK_SESSION_EXPIRED");
    }
    return record;
  }

  #appendProviderEvent(record, event) {
    const accepted = this.#appendEvent(record, event, false);
    if (!accepted) record.outputExceeded = true;
    return accepted;
  }

  #appendInternalEvent(record, event) {
    this.#appendEvent(record, event, true);
  }

  #appendEvent(record, event, internal) {
    const document = Object.freeze({
      schemaVersion: "1.0",
      sequence: record.nextSequence,
      sessionId: record.id,
      turnId: record.activeTurnId,
      at: new Date(this.now()).toISOString(),
      type: event.type,
      payload: event.payload,
    });
    const bytes = utf8Length(JSON.stringify(document));
    if (bytes > this.maxEventBytes) return false;
    if (!internal) {
      if (
        record.events.length >= Math.max(0, this.maxEvents - 2) ||
        record.eventBytes + bytes > Math.max(0, this.maxEventBytes - 8 * 1024)
      ) {
        return false;
      }
    } else {
      while (
        record.events.length >= this.maxEvents ||
        record.eventBytes + bytes > this.maxEventBytes
      ) {
        const removable = record.events.findIndex((candidate) =>
          !candidate.type.startsWith("turn."));
        if (removable < 0) return false;
        const [removed] = record.events.splice(removable, 1);
        record.eventBytes -= utf8Length(JSON.stringify(removed));
      }
    }
    record.events.push(document);
    record.eventBytes += bytes;
    record.nextSequence += 1;
    return true;
  }

  async #removeExpired() {
    const expired = [...this.sessions.values()].filter(
      (record) => record.expiresAt <= this.now(),
    );
    for (const record of expired) this.sessions.delete(record.id);
    await Promise.allSettled(expired.map((record) => record.client.close()));
  }
}

export function createAskService(options) {
  return new AskService(options);
}

export { mapClientError };
