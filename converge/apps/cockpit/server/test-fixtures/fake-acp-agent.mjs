#!/usr/bin/env node

import path from "node:path";
import { Readable, Writable } from "node:stream";

import {
  PROTOCOL_VERSION,
  RequestError,
  agent as createAgentApp,
  methods,
  ndJsonStream,
} from "@agentclientprotocol/sdk";

const flags = new Set(process.argv.slice(2));
const sessions = new Map();
const cancellations = new Map();
const cancelledSessions = new Set();
let nextSession = 1;

const app = createAgentApp({ name: "converge-fake-agent" })
  .onRequest(methods.agent.initialize, ({ params }) => ({
    protocolVersion: flags.has("--protocol-mismatch")
      ? PROTOCOL_VERSION + 1
      : params.protocolVersion,
    agentCapabilities: {
      loadSession: false,
      promptCapabilities: {},
      sessionCapabilities: {
        delete: {},
      },
    },
    authMethods: [
      {
        id: "fake-login",
        name: "Fake agent login",
        description: "Deterministic test authentication",
      },
    ],
    agentInfo: {
      name: "converge-fake-agent",
      title: "Converge Fake Agent",
      version: "1.0.0",
    },
  }))
  .onRequest(methods.agent.authenticate, () => ({}))
  .onRequest(methods.agent.session.new, ({ params }) => {
    if (
      !path.isAbsolute(params.cwd) ||
      params.mcpServers.length !== 0 ||
      params._meta?.disableBuiltInTools !== true ||
      params._meta?.claudeCode?.options?.tools?.length !== 0 ||
      params._meta?.claudeCode?.options?.settingSources?.length !== 0
    ) {
      throw new Error(
        "fake agent requires an absolute cwd, no MCP servers, and disabled built-in tools",
      );
    }
    const sessionId = `fake-session-${nextSession}`;
    nextSession += 1;
    sessions.set(sessionId, { cwd: params.cwd });
    return {
      sessionId,
      modes: {
        currentModeId: flags.has("--no-safe-mode") ? "agent" : "read-only",
        availableModes: flags.has("--no-safe-mode")
          ? [
              {
                id: "agent",
                name: "Agent",
                description: "Unsafe test mode",
              },
            ]
          : [
              {
                id: "read-only",
                name: "Read only",
                description: "Explain without workspace mutation",
              },
            ],
      },
      configOptions: [
        {
          id: "model",
          name: "Model",
          category: "model",
          type: "select",
          currentValue: "fake-sonnet",
          options: [
            { value: "fake-sonnet", name: "Fake Sonnet" },
            { value: "fake-opus", name: "Fake Opus" },
          ],
        },
        {
          id: "thinking",
          name: "Extended thinking",
          category: "thought_level",
          type: "boolean",
          currentValue: false,
        },
        {
          // A mode selector must never be settable through the model picker.
          id: "danger-mode",
          name: "Session mode",
          category: "mode",
          type: "select",
          currentValue: "read-only",
          options: [
            { value: "read-only", name: "Read only" },
            { value: "agent", name: "Agent" },
          ],
        },
      ],
    };
  })
  .onRequest(methods.agent.session.setConfigOption, ({ params }) => {
    const session = sessions.get(params.sessionId);
    if (!session) throw new Error("unknown fake session");
    session.config = { ...session.config, [params.configId]: params.value };
    // Echo only the option that changed, the way the pinned Claude adapter
    // does, so the client is forced to merge rather than replace.
    if (params.configId === "thinking") {
      return {
        configOptions: [
          {
            id: "thinking",
            name: "Extended thinking",
            category: "thought_level",
            type: "boolean",
            currentValue: session.config.thinking === true,
          },
        ],
      };
    }
    return {
      configOptions: [
        {
          id: "model",
          name: "Model",
          category: "model",
          type: "select",
          currentValue: session.config.model ?? "fake-sonnet",
          options: [
            { value: "fake-sonnet", name: "Fake Sonnet" },
            { value: "fake-opus", name: "Fake Opus" },
          ],
        },
      ],
    };
  })
  .onRequest(methods.agent.session.prompt, async ({ params, client }) => {
    const session = sessions.get(params.sessionId);
    if (!session) throw new Error("unknown fake session");
    if (flags.has("--auth-required")) {
      throw RequestError.authRequired();
    }
    if (flags.has("--hang")) {
      if (!cancelledSessions.delete(params.sessionId)) {
        await new Promise((resolve) => cancellations.set(params.sessionId, resolve));
      }
      return { stopReason: "cancelled" };
    }

    await client.notify(methods.client.session.update, {
      sessionId: params.sessionId,
      update: {
        sessionUpdate: "plan",
        entries: [
          { content: "Read the supplied grounding", priority: "high", status: "in_progress" },
        ],
      },
    });
    const kind = flags.has("--unsafe") ? "execute" : "read";
    await client.notify(methods.client.session.update, {
      sessionId: params.sessionId,
      update: {
        sessionUpdate: "tool_call",
        toolCallId: "fake-tool-1",
        title: kind === "read" ? "Read snapshot evidence" : "Run unsafe command",
        kind,
        status: "pending",
        locations: [{ path: path.join(session.cwd, "docs", "proof.md"), line: 1 }],
      },
    });
    const permission = await client.request(methods.client.session.requestPermission, {
      sessionId: params.sessionId,
      toolCall: {
        toolCallId: "fake-tool-1",
        title: "Request tool permission",
        kind,
        status: "pending",
      },
      options: [
        { optionId: "allow", name: "Allow once", kind: "allow_once" },
        { optionId: "reject", name: "Reject", kind: "reject_always" },
      ],
    });
    await client.notify(methods.client.session.update, {
      sessionId: params.sessionId,
      update: {
        sessionUpdate: "tool_call_update",
        toolCallId: "fake-tool-1",
        kind,
        title: "Tool permission resolved",
        status: permission.outcome.outcome === "selected" &&
          permission.outcome.optionId === "reject"
          ? "failed"
          : "completed",
      },
    });
    const promptText = params.prompt
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("\n");
    if (!promptText.includes("CONVERGE ASK GROUNDING")) {
      throw new Error("fake agent did not receive Converge grounding");
    }
    if (
      flags.has("--require-history") &&
      (
        !promptText.includes("UNTRUSTED PRIOR CONVERSATION") ||
        !promptText.includes("Earlier question") ||
        !promptText.includes("TOKEN=[REDACTED]") ||
        promptText.includes("super-secret-value") ||
        promptText.indexOf("UNTRUSTED PRIOR CONVERSATION") <
          promptText.indexOf("END CONVERGE ASK GROUNDING")
      )
    ) {
      throw new Error("fake agent did not receive bounded untrusted history");
    }
    for (const text of [
      "The snapshot-bound explanation is ready. ",
      "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz",
    ]) {
      await client.notify(methods.client.session.update, {
        sessionId: params.sessionId,
        update: {
          sessionUpdate: "agent_message_chunk",
          content: { type: "text", text },
        },
      });
    }
    return { stopReason: "end_turn" };
  })
  .onRequest(methods.agent.session.delete, ({ params }) => {
    sessions.delete(params.sessionId);
    return {};
  })
  .onNotification(methods.agent.session.cancel, ({ params }) => {
    const resolve = cancellations.get(params.sessionId);
    if (resolve) {
      resolve();
      cancellations.delete(params.sessionId);
    } else {
      cancelledSessions.add(params.sessionId);
    }
  });

app.connect(
  ndJsonStream(
    Writable.toWeb(process.stdout),
    Readable.toWeb(process.stdin),
  ),
);
