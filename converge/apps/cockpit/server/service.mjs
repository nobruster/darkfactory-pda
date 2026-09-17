const SAFE_ERROR_CODES = new Set([
  "CLI_SNAPSHOT_INVALID",
  "CLI_SNAPSHOT_REJECTED",
  "CLI_SNAPSHOT_TIMEOUT",
  "SNAPSHOT_SCHEMA_INVALID",
  "SNAPSHOT_SCHEMA_UNAVAILABLE",
]);

function transportError(error) {
  const code = SAFE_ERROR_CODES.has(error?.code)
    ? error.code
    : "SNAPSHOT_REFRESH_FAILED";
  const messages = {
    CLI_SNAPSHOT_INVALID: "The CLI returned an unreadable snapshot.",
    CLI_SNAPSHOT_REJECTED: "The CLI rejected the snapshot request.",
    CLI_SNAPSHOT_TIMEOUT: "The CLI snapshot request timed out.",
    SNAPSHOT_SCHEMA_INVALID:
      "The CLI snapshot does not match WorkspaceSnapshot 3.0.",
    SNAPSHOT_SCHEMA_UNAVAILABLE:
      "The WorkspaceSnapshot 3.0 contract is unavailable.",
    SNAPSHOT_REFRESH_FAILED: "The CLI snapshot could not be refreshed.",
  };
  return { code, message: messages[code] };
}

export class SnapshotService {
  constructor({
    build,
    cacheMs = 1_500,
    now = () => Date.now(),
  }) {
    if (typeof build !== "function") {
      throw new TypeError("SnapshotService requires a build function");
    }
    this.build = build;
    this.cacheMs = cacheMs;
    this.now = now;
    this.cached = null;
    this.cachedAt = 0;
    this.lastAttemptAt = 0;
    this.lastRefreshError = null;
    this.inFlight = null;
  }

  envelope() {
    if (!this.cached) {
      throw new Error("no last-good workspace snapshot is available");
    }
    const stale = this.lastRefreshError !== null;
    return {
      snapshot: this.cached,
      transport: {
        stale,
        servedAt: new Date(this.now()).toISOString(),
        ...(stale ? { error: this.lastRefreshError } : {}),
      },
    };
  }

  async refresh() {
    this.lastAttemptAt = this.now();
    try {
      const snapshot = await this.build();
      this.cached = snapshot;
      this.cachedAt = this.now();
      this.lastRefreshError = null;
    } catch (error) {
      this.lastRefreshError = transportError(error);
      if (!this.cached) {
        throw error;
      }
    }
  }

  async getSnapshot({ fresh = false } = {}) {
    const cacheIsCurrent =
      this.cached &&
      this.now() - this.lastAttemptAt < this.cacheMs;
    if (!fresh && cacheIsCurrent) {
      return this.envelope();
    }

    if (!this.inFlight) {
      this.inFlight = this.refresh().finally(() => {
        this.inFlight = null;
      });
    }
    await this.inFlight;
    return this.envelope();
  }
}

export { transportError };
