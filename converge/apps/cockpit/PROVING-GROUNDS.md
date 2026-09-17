# Cockpit proving grounds

The product version does not imply that the release gates below have passed.

| Case | Lane | Current evidence | Release gate |
|---|---|---|---|
| `uc-01-analytics-engineering` | FULL | The prior V0 observation is not current release evidence; this checkout has no dated WorkspaceSnapshot 3.0 rerun for the case | Open |
| `uc-02` Data Engineering | NORMAL (planned) | No proving-ground workspace is present | Not run |
| `uc-03` Software Engineering | NORMAL (planned) | No proving-ground workspace is present | Not run |
| `uc-04` AI Engineering | FAST and failure paths (planned) | No proving-ground workspace is present | Not run |

The application is release-ready only when all four cases have exercised the
same WorkspaceSnapshot 3.0 contract without frontend-derived truth.

For `uc-01`, the proving ground must be rerun against WorkspaceSnapshot 3.0
before its current barrier, queue, attempts, or receipts can be claimed.
Cockpit must show whatever that fresh CLI snapshot reports; it must not create
tasks, advance a pass, or synthesize later lifecycle data. The gate remains
open until the dated rerun and owner review are recorded.

## New-surface evidence

| Capability | Current evidence | Boundary |
|---|---|---|
| Typed Decompose | Shell, schema, decoder, component, and live-fixture browser tests cover one seam, two legs, and one canonical dependency | Structural evidence; not owner approval of a real plan |
| Ask via ACP | Fake-agent tests cover ACP v1, verified context isolation, disabled Claude tools and settings, empty MCP, provider-session deletion, permission rejection, cancellation, redaction, bounds, and stale snapshots; Codex is statically blocked before spawn | No credentialed Codex or Claude turn is claimed |
| Markdown reader | A live-fixture browser test opens a SHA-bound README with headings, table, and code | Proves derived rendering, not document correctness |
| PDF reader | Server tests cover complete-source hash verification and bounded text extraction | Text preview does not reproduce visual layout, links, images, or attachments |
| Pass blade | Browser tests open Capture and verify Overview, Evidence, and Activity across six viewport classes | Shows the current snapshot projection; it is not a durable pass history |
| Overview and Activity | Component and browser tests cover bounded rollups, relationships, signals, and issues | No inferred trend, event, or historical metric is claimed |

Hermetic fixtures verify rendering, protocol, and interaction semantics. They
are replay and structural evidence, not evidence that a proving-ground case
completed or that a provider account is authenticated. A release sign-off still
needs a dated real-workspace run, one explicitly authorized provider smoke test
with before and after workspace hashes, and owner review of the provider data
and retention boundary.
