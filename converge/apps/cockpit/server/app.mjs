import { readFile, stat } from "node:fs/promises";
import path from "node:path";

import {
  askCapabilitiesDocument,
  runAskOnce,
} from "./ask-http.mjs";
import { parseAskAgentIdRequest, publicAskError } from "./ask-contract.mjs";
import { publicError } from "./security.mjs";

const MAX_ASK_BODY_BYTES = 64 * 1024;
const CONTENT_TYPES = Object.freeze({
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
});

function setSecurityHeaders(response) {
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader("Referrer-Policy", "no-referrer");
  response.setHeader("X-Frame-Options", "DENY");
  response.setHeader(
    "Content-Security-Policy",
    "default-src 'self'; connect-src 'self'; font-src 'self' data:; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
  );
}

function sendJson(response, statusCode, document) {
  if (response.destroyed || response.writableEnded) return;
  const body = JSON.stringify(document);
  response.writeHead(statusCode, {
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  response.end(body);
}

function isJsonContentType(value) {
  if (typeof value !== "string") return false;
  return value.split(";", 1)[0].trim().toLowerCase() === "application/json";
}

async function readJsonBody(request, maxBytes = MAX_ASK_BODY_BYTES) {
  let size = 0;
  const chunks = [];
  for await (const chunk of request) {
    size += chunk.byteLength;
    if (size > maxBytes) {
      const error = new Error("request body is too large");
      error.code = "ASK_BODY_TOO_LARGE";
      throw error;
    }
    chunks.push(chunk);
  }
  if (size === 0) {
    const error = new Error("request body is required");
    error.code = "ASK_BODY_INVALID";
    throw error;
  }
  try {
    return JSON.parse(Buffer.concat(chunks, size).toString("utf8"));
  } catch (cause) {
    const error = new Error("request body is not valid JSON", { cause });
    error.code = "ASK_BODY_INVALID";
    throw error;
  }
}

function isAllowedAskOrigin(request) {
  const origin = request.headers.origin;
  const host = request.headers.host;
  return (
    typeof origin === "string" &&
    typeof host === "string" &&
    origin === `http://${host}`
  );
}

export function isAllowedHostHeader(value) {
  if (typeof value !== "string") {
    return false;
  }
  const match = value.match(
    /^(?:localhost|127\.0\.0\.1|\[::1\])(?::([0-9]{1,5}))?$/i,
  );
  return Boolean(
    match &&
      (match[1] === undefined ||
        (Number(match[1]) >= 1 && Number(match[1]) <= 65_535)),
  );
}

async function serveStatic(response, pathname, distRoot, headOnly) {
  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return false;
  }
  if (decoded.includes("\0") || decoded.includes("\\")) {
    return false;
  }

  const relative = decoded.replace(/^\/+/, "");
  const candidate = path.resolve(distRoot, relative || "index.html");
  if (
    candidate !== distRoot &&
    !candidate.startsWith(`${path.resolve(distRoot)}${path.sep}`)
  ) {
    return false;
  }

  let selected = candidate;
  try {
    const info = await stat(selected);
    if (!info.isFile()) {
      selected = path.join(distRoot, "index.html");
    }
  } catch {
    if (path.extname(relative)) {
      return false;
    }
    selected = path.join(distRoot, "index.html");
  }

  try {
    const contents = await readFile(selected);
    response.writeHead(200, {
      "Cache-Control":
        path.basename(selected) === "index.html"
          ? "no-cache"
          : "public, max-age=31536000, immutable",
      "Content-Type":
        CONTENT_TYPES[path.extname(selected).toLowerCase()] ??
        "application/octet-stream",
      "Content-Length": contents.byteLength,
    });
    response.end(headOnly ? undefined : contents);
    return true;
  } catch {
    return false;
  }
}

function beginEventStream(request, response, service, pollMs) {
  response.writeHead(200, {
    "Cache-Control": "no-cache, no-transform",
    Connection: "keep-alive",
    "Content-Type": "text/event-stream; charset=utf-8",
    "X-Accel-Buffering": "no",
  });
  response.write("retry: 4000\n\n");

  let closed = false;
  let lastEventSignature = null;
  let polling = false;

  const emitSnapshot = async (fresh) => {
    if (closed || polling) {
      return;
    }
    polling = true;
    try {
      const envelope = await service.getSnapshot({ fresh });
      const snapshotId = envelope.snapshot.snapshotId;
      const transportState = envelope.transport.stale
        ? `stale:${envelope.transport.error?.code ?? "unknown"}`
        : "fresh";
      const eventSignature = `${snapshotId}:${transportState}`;
      if (!closed && eventSignature !== lastEventSignature) {
        lastEventSignature = eventSignature;
        response.write(`id: ${snapshotId}\n`);
        response.write("event: snapshot\n");
        response.write(`data: ${JSON.stringify(envelope)}\n\n`);
      }
    } catch {
      if (!closed) {
        response.write(": snapshot temporarily unavailable\n\n");
      }
    } finally {
      polling = false;
    }
  };

  void emitSnapshot(false);
  const pollTimer = setInterval(() => void emitSnapshot(true), pollMs);
  const heartbeatTimer = setInterval(() => {
    if (!closed) {
      response.write(`: heartbeat ${Date.now()}\n\n`);
    }
  }, 15_000);
  pollTimer.unref();
  heartbeatTimer.unref();

  request.on("close", () => {
    closed = true;
    clearInterval(pollTimer);
    clearInterval(heartbeatTimer);
  });
}

export function createRequestHandler({
  config,
  service,
  artifactStore,
  askService = null,
  askRequestToken = "",
  pollMs = 5_000,
}) {
  return (request, response) => {
    setSecurityHeaders(response);

    void (async () => {
      if (!isAllowedHostHeader(request.headers.host)) {
        sendJson(
          response,
          403,
          publicError(
            "HOST_NOT_ALLOWED",
            "Converge Cockpit accepts requests only through a loopback host.",
          ),
        );
        return;
      }

      const url = new URL(request.url ?? "/", "http://localhost");
      const isGet = request.method === "GET";
      const isHead = request.method === "HEAD";
      // `/api/ask/options` spawns an adapter to read its model selectors, so it
      // carries the same POST guards as asking rather than being reachable as a
      // plain cross-origin GET.
      const isAskPostPath =
        url.pathname === "/api/ask" || url.pathname === "/api/ask/options";
      const isAskPost = isAskPostPath && request.method === "POST";

      if (url.pathname.startsWith("/api/") && !isGet && !isAskPost) {
        response.setHeader("Allow", isAskPostPath ? "GET, POST" : "GET");
        sendJson(
          response,
          405,
          publicError(
            "METHOD_NOT_ALLOWED",
            "Converge Cockpit exposes read-only GET endpoints.",
          ),
        );
        return;
      }

      if (url.pathname === "/api/ask/agents") {
        if (!askService) {
          sendJson(
            response,
            503,
            publicError(
              "ASK_UNAVAILABLE",
              "Ask Converge is not configured for this Cockpit process.",
            ),
          );
          return;
        }
        try {
          sendJson(
            response,
            200,
            await askCapabilitiesDocument(askService, askRequestToken),
          );
        } catch {
          sendJson(
            response,
            503,
            publicError(
              "ASK_UNAVAILABLE",
              "The local ACP agent registry is unavailable.",
            ),
          );
        }
        return;
      }

      if (isAskPost) {
        if (!askService) {
          sendJson(
            response,
            503,
            publicError(
              "ASK_UNAVAILABLE",
              "Ask Converge is not configured for this Cockpit process.",
            ),
          );
          return;
        }
        if (
          !isAllowedAskOrigin(request) ||
          request.headers["x-converge-request"] !== "ask-v1" ||
          request.headers["x-converge-csrf"] !== askRequestToken
        ) {
          sendJson(
            response,
            403,
            publicError(
              "ASK_REQUEST_NOT_ALLOWED",
              "Ask requests must originate from this local Cockpit session.",
            ),
          );
          return;
        }
        if (!isJsonContentType(request.headers["content-type"])) {
          sendJson(
            response,
            415,
            publicError(
              "ASK_CONTENT_TYPE_REQUIRED",
              "Ask requests require an application/json body.",
            ),
          );
          return;
        }
        const askAbort = new AbortController();
        const abortAsk = () => askAbort.abort();
        const abortIfDisconnected = () => {
          if (!response.writableEnded) abortAsk();
        };
        request.once("aborted", abortAsk);
        response.once("close", abortIfDisconnected);
        try {
          const body = await readJsonBody(request);
          if (url.pathname === "/api/ask/options") {
            const { agentId } = parseAskAgentIdRequest(body);
            sendJson(response, 200, await askService.probeAgentConfig(agentId));
            return;
          }
          sendJson(
            response,
            200,
            await runAskOnce(askService, body, { signal: askAbort.signal }),
          );
        } catch (error) {
          if (response.destroyed) return;
          if (
            error?.code === "ASK_BODY_TOO_LARGE" ||
            error?.code === "ASK_BODY_INVALID"
          ) {
            sendJson(
              response,
              error.code === "ASK_BODY_TOO_LARGE" ? 413 : 400,
              publicError(
                error.code,
                error.code === "ASK_BODY_TOO_LARGE"
                  ? "The Ask request body exceeds the local safety limit."
                  : "The Ask request body is invalid.",
              ),
            );
            return;
          }
          const publicFailure = publicAskError(error);
          sendJson(
            response,
            publicFailure.statusCode,
            publicFailure.document,
          );
        } finally {
          request.off("aborted", abortAsk);
          response.off("close", abortIfDisconnected);
        }
        return;
      }

      if (url.pathname === "/api/health") {
        sendJson(response, 200, {
          ok: true,
          service: "converge-cockpit",
          mode: "read-only",
          project: path.basename(config.projectRoot),
        });
        return;
      }

      if (url.pathname === "/api/snapshot") {
        try {
          sendJson(response, 200, await service.getSnapshot());
        } catch {
          sendJson(
            response,
            503,
            publicError(
              "SNAPSHOT_UNAVAILABLE",
              "The read-only workspace snapshot is unavailable.",
            ),
          );
        }
        return;
      }

      if (url.pathname === "/api/events") {
        beginEventStream(request, response, service, pollMs);
        return;
      }

      if (url.pathname === "/api/artifact") {
        const requestedPaths = url.searchParams.getAll("path");
        const requestedSnapshotIds = url.searchParams.getAll("snapshotId");
        const requestedHashes = url.searchParams.getAll("sha256");
        const requestedPath = requestedPaths[0];
        const requestedSnapshotId = requestedSnapshotIds[0];
        const expectedSha256 = requestedHashes[0];
        if (requestedPaths.length !== 1 || !requestedPath) {
          sendJson(
            response,
            400,
            publicError("ARTIFACT_PATH_REQUIRED", "A single artifact path is required."),
          );
          return;
        }
        if (requestedSnapshotIds.length !== 1 || !requestedSnapshotId) {
          sendJson(
            response,
            400,
            publicError(
              "SNAPSHOT_ID_REQUIRED",
              "Artifact reads must be bound to a workspace snapshot.",
            ),
          );
          return;
        }
        if (requestedHashes.length !== 1 || !expectedSha256) {
          sendJson(
            response,
            400,
            publicError(
              "ARTIFACT_SHA256_REQUIRED",
              "Artifact reads must include the SHA-256 captured by the workspace snapshot.",
            ),
          );
          return;
        }
        let envelope;
        try {
          envelope = await service.getSnapshot();
        } catch {
          sendJson(
            response,
            503,
            publicError(
              "SNAPSHOT_UNAVAILABLE",
              "The read-only workspace snapshot is unavailable.",
            ),
          );
          return;
        }
        if (envelope?.snapshot?.source !== "workspace") {
          sendJson(
            response,
            503,
            publicError(
              "SNAPSHOT_UNAVAILABLE",
              "The read-only workspace snapshot is unavailable.",
            ),
          );
          return;
        }
        try {
          if (envelope.snapshot.snapshotId !== requestedSnapshotId) {
            const error = new Error("the requested snapshot is no longer current");
            error.code = "SNAPSHOT_STALE";
            throw error;
          }
          sendJson(
            response,
            200,
            await artifactStore.read(requestedPath, {
              snapshotId: requestedSnapshotId,
              expectedSha256,
            }),
          );
        } catch (error) {
          const notAllowed = error?.code === "ARTIFACT_NOT_ALLOWED";
          const stale =
            error?.code === "SNAPSHOT_STALE" ||
            error?.code === "EVIDENCE_STALE";
          const tooLarge = error?.code === "ARTIFACT_TOO_LARGE";
          const invalidPdf = error?.code === "PDF_PREVIEW_INVALID";
          sendJson(
            response,
            stale ? 409 : notAllowed ? 403 : tooLarge ? 413 : invalidPdf ? 422 : 404,
            publicError(
              stale
                ? error.code
                : notAllowed
                  ? "ARTIFACT_NOT_ALLOWED"
                  : tooLarge
                    ? "ARTIFACT_TOO_LARGE"
                    : invalidPdf
                      ? "PDF_PREVIEW_INVALID"
                  : "ARTIFACT_NOT_FOUND",
              stale
                ? "The artifact no longer matches the captured workspace snapshot. Refresh before inspecting it."
                : notAllowed
                  ? "The requested artifact is not in the workspace evidence allowlist."
                  : tooLarge
                    ? "The requested artifact exceeds the safe preview limit."
                    : invalidPdf
                      ? "The requested PDF cannot be converted into a safe text preview."
                      : "The requested artifact is unavailable.",
            ),
          );
        }
        return;
      }

      if (url.pathname.startsWith("/api/")) {
        sendJson(
          response,
          404,
          publicError("NOT_FOUND", "No read-only endpoint exists at this path."),
        );
        return;
      }

      if (
        config.serveDist &&
        (isGet || isHead) &&
        (await serveStatic(response, url.pathname, config.distRoot, isHead))
      ) {
        return;
      }

      sendJson(
        response,
        404,
        publicError(
          "NOT_FOUND",
          config.serveDist
            ? "The requested resource was not found."
            : "Converge Cockpit is served separately in development mode.",
        ),
      );
    })().catch(() => {
      if (!response.headersSent) {
        sendJson(
          response,
          500,
          publicError(
            "COCKPIT_ERROR",
            "Converge Cockpit could not complete the request.",
          ),
        );
      } else {
        response.end();
      }
    });
  };
}

export { beginEventStream, serveStatic };
