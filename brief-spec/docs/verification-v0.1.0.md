# Brief-Spec v0.1.0 verification record

This record separates deterministic product evidence from host and external-service evidence. It
describes the v0.1 acceptance run performed on 2026-07-31; it is not a promise that future host
versions behave identically.

## Deterministic release gates

- 212 behavioral tests passed on Python 3.13.9.
- Branch coverage was 96.45%, above the configured 85% gate.
- Ruff lint and format checks passed.
- The Apex experience pilot passed all five scenarios: DONE, REVIEW, Orient, Teach, and Spoken.
- Both skill packages passed the Codex skill validator.
- The Codex plugin bundle validator passed.
- Claude Code's strict plugin and marketplace validators passed.
- The release verifier passed 269 source and wheel checks.
- The wheel and source distribution passed Twine metadata validation.
- The built wheel installed with no runtime dependencies.
- Empty user and project homes completed install, repeated install, doctor probe, and uninstall for
  Codex, Claude, and Copilot.
- The Copilot project bridge returned both native and VS Code-compatible context envelopes.

## Native and live host evidence

| Host surface | Evidence | Result |
| --- | --- | --- |
| Codex CLI 0.144.5 | Isolated marketplace add and plugin install | Passed |
| Codex CLI 0.144.5 | Real SessionStart and UserPromptSubmit hook execution | Passed |
| Codex model turn | Authenticated generation after hook execution | Not completed: account usage limit |
| Claude Code 2.1.220 | Strict validation, local plugin load, lifecycle hooks, and live skill turn | Passed |
| Claude Code 2.1.220 | Generated Outcome Brief checked by `briefspec validate` | Passed |
| Copilot CLI 1.0.77 | Isolated direct install and marketplace install | Passed |
| Copilot CLI 1.0.77 | Live skill turn plus lifecycle state | Passed |
| Copilot CLI 1.0.77 | Generated Outcome Brief checked by `briefspec validate` | Passed |

The Codex host evidence proves discovery and real hook execution, but not a completed model-rendered
brief in that run. The failure occurred after the hooks ran, when Codex reported that the account
had reached its current usage limit.

## Structurally verified, externally pending

- VS Code: the project assets, PascalCase lifecycle events, dual response envelope, and generated
  commands are tested. Interactive discovery and Agent Debug Logs were not observed in the final
  acceptance environment.
- Copilot cloud agent: the checked-in bridge is deterministic, network-free, and locally executable.
  No GitHub cloud job was launched because that requires publishing the branch and starting an
  external repository task.
- GitHub.com Chat and Copilot code review: Brief-Spec makes no automatic lifecycle-integration claim.

These boundaries are release evidence, not defects hidden behind a generic “supported” label. A
future release should repeat every available live-host gate and replace pending entries only with
inspectable host proof.
