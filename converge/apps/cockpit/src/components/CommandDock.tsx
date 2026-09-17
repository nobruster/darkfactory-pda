import { useEffect, useState } from "react";
import {
  Check,
  ClipboardText,
  Command,
  LockKey,
  ShieldCheck,
} from "@phosphor-icons/react";
import type { WorkspaceSnapshot } from "../types";

interface CommandDockProps {
  snapshot: WorkspaceSnapshot;
}

export function CommandDock({ snapshot }: CommandDockProps) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const nextPass = snapshot.method.passes.find(
    (pass) => pass.id === snapshot.authorization.nextPassId,
  );

  useEffect(() => setCopyState("idle"), [snapshot.authorization.command]);

  async function copyCommand() {
    if (!snapshot.authorization.command) return;
    try {
      await navigator.clipboard.writeText(snapshot.authorization.command);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1600);
    } catch {
      setCopyState("error");
      window.setTimeout(() => setCopyState("idle"), 2200);
    }
  }

  return (
    <footer className="command-dock" aria-label="CLI frontier">
      <div
        className={`command-dock__state command-dock__state--${snapshot.authorization.state}`}
      >
        {snapshot.authorization.state === "allowed" ? (
          <ShieldCheck weight="fill" aria-hidden="true" />
        ) : (
          <LockKey weight="fill" aria-hidden="true" />
        )}
        <span>
          <small>CLI execution required</small>
          <strong>
            {nextPass
              ? `Pass ${nextPass.order} / ${nextPass.label}`
              : snapshot.authorization.state === "complete"
                ? "Method complete"
                : snapshot.authorization.state}
          </strong>
        </span>
      </div>

      <div className="command-dock__command" title={snapshot.authorization.rationale}>
        <Command aria-hidden="true" />
        <code>
          {snapshot.authorization.command ??
            (snapshot.authorization.state === "blocked"
              ? "No command authorized"
              : "No next command")}
        </code>
      </div>

      <button
        type="button"
        className="command-dock__copy"
        onClick={() => void copyCommand()}
        disabled={!snapshot.authorization.command}
        aria-label={
          copyState === "copied"
            ? "Command copied"
            : copyState === "error"
              ? "Command could not be copied"
              : "Copy authorized command"
        }
      >
        {copyState === "copied" ? (
          <Check weight="bold" aria-hidden="true" />
        ) : (
          <ClipboardText aria-hidden="true" />
        )}
        <span>
          {copyState === "copied"
            ? "Copied"
            : copyState === "error"
              ? "Unavailable"
              : "Copy"}
        </span>
      </button>

      <div className="command-dock__boundary">
        <strong>CLI execution required</strong>
        <span className="command-dock__metadata">
          <span>Browser read-only</span>
          <span>Mutation: {snapshot.authorization.mutation.replace("_", " ")}</span>
          <span>
            Dry run: {snapshot.authorization.dryRunSupported ? "supported" : "no"}
          </span>
          <span>Enabled: {snapshot.authorization.enabled ? "yes" : "no"}</span>
        </span>
        <details className="command-dock__rationale">
          <summary>Rationale</summary>
          <p>{snapshot.authorization.rationale}</p>
        </details>
      </div>
    </footer>
  );
}
