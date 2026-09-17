# Converge Cockpit visual system

Cockpit is a read-only operational projection of canonical Converge state. It
is built for understanding the full journey from intent to settlement without
turning the browser into a second execution authority.

## Product posture

- The repository and `cvg` CLI remain canonical.
- The deterministic observation surfaces fetch WorkspaceSnapshot 3.0 and render
  only what the snapshot can prove. Ask is explicitly separated as agent
  interpretation.
- The command bar exposes a compact method-frontier summary. Exact command and
  gate context live inside the relevant pass blade; Cockpit cannot execute or
  mutate anything.
- Ask sends bounded snapshot context through ACP only when a context-only
  provider mode is verified. Its prose remains visually and semantically
  separate from proof.
- Empty, unavailable, loading, stale, blocked, and error states are visually and
  textually distinct.
- Panel preferences are the only client state persisted in localStorage.

## Shell

The interface fills `100dvh` with no floating outer frame:

- A 56 px command bar identifies the workspace, Git state, transport freshness,
  and panel controls.
- A left navigation rail is 56 px collapsed and 256 px expanded. It groups Ask
  under Explain and Overview, Journey, Decompose, Work, Runs, Docs, Activity,
  and Health under Observe.
- The center is a full-bleed operational surface.
- A 430 px inspector uses readable Overview, Evidence, and Activity tabs to
  keep typed entity context in one place. Journey places an open pass blade to
  the left of the graph so the method remains visible as one connected view.
- There is no persistent bottom execution dock. The released height belongs to
  project understanding, documents, and graph navigation.

## Responsive behavior

- At 1600 px and wider, both side panels start expanded.
- From 1280 px through 1599 px, navigation starts collapsed and the inspector
  starts docked open.
- From 1024 px through 1279 px, both panels start closed and the inspector opens
  as an overlay.
- At 1023 px and narrower, navigation and inspector are mutually exclusive
  drawers.
- Below 768 px, Journey, Decompose, and Work use semantic lists instead of
  React Flow, the inspector becomes a full-width sheet, and all nine views move
  to a horizontally scrollable bottom navigation bar.
- Saved desktop panel preferences are restored where docked panels fit. Smaller
  viewports always start unobstructed.

## Direction

- Dense, cinematic operational software rather than a generic card dashboard.
- Outfit Variable for product typography and system monospace for commands,
  identifiers, hashes, and paths.
- Factory Black and Carbon surfaces with Forge Gold as the single brand accent.
- Mint communicates canonical proof, coral communicates failure or unresolved
  risk, and Steel communicates optional, future, empty, or unavailable state.
- Semantic color is always paired with a written status and icon.
- Borders and restrained depth organize the workspace. Decorative glass and
  gradients never replace hierarchy.

## Surfaces

### Ask

Ask presents Codex and Claude as agent choices over ACP. Claude receives a
bounded snapshot summary, selected entity, and explicitly selected artifact
text in plan mode with built-in tools and settings sources disabled. It launches
outside the workspace, client MCP is empty, and permission requests are
rejected. Codex remains visible but blocked because the pinned adapter cannot
suppress local read/search tools; it states that reason in place rather than
appearing as an unexplained disabled control. The answer shows its
interpretation boundary and is cleared if scope changes.

The surface follows a familiar chat rhythm: quiet empty-state prompts sitting
with the invitation they answer above the composer, scrolling turns, stop and
new-chat controls, and a multiline composer. Two composer controls carry the
setup a reader actually changes:

- **Engine and model.** One popover holds the engine, the model, and any
  reasoning or thought-level selector the agent advertises over ACP
  `session/set_config_option`. Options are read from a disposable probe session
  that sends no prompt, so nothing is spawned merely by opening Ask, and the
  reply header names the model that actually answered. Only the `model`,
  `model_config`, and `thought_level` categories are settable. The `mode`
  category is deliberately excluded: session mode is what holds Claude in plan
  mode, and the pinned adapter advertises `bypassPermissions`, `acceptEdits`,
  and `dontAsk` there.
- **Question context.** A searchable picker over the passes, swimlanes, legs,
  tasks, runs, receipts, artifacts, issues, signals, and health checks in the
  current snapshot. Every question already carries the method reference and the
  whole snapshot; naming one entity adds its detail, and an artifact adds its
  hash-bound text.

Conversations are owned above the surface, so moving to another view no longer
discards the transcript, and prior conversations stay reachable through the
history control. Nothing is written to storage: transcripts survive navigation
but not a reload, which keeps provider answers off disk. Each message still runs
in a fresh disposable ACP session.

### Overview

Overview is the project-at-a-glance landing surface. It composes the method
frontier, current authorization, decomposition, work, documents, receipts,
health, signals, and issues from the same snapshot without inventing rollups or
historical trends.

### Journey

Journey renders the nine Converge passes and their required, optional, and
bypass lineage. Nodes can be dragged for local exploration. Pan, zoom, Fit, and
Arrange never alter repository state. Center Selected preserves the current
zoom and does not reset the viewport.

### Decompose

Decompose renders the CLI's typed seams, swimlanes, legs, and canonical
`depends_on` edges. Focus is the default readable projection and gives the seam
rationale, contracts, evolution boundary, and each leg's full responsibility,
inputs, outputs, proof, yield, and re-verification rule room to wrap. Map remains
an exploratory relationship view with expanded nodes; Arrange and local leg
dragging never alter the repository. Read provides the same information as a
semantic lane-and-leg sequence and is mandatory on narrow screens.

### Work

Work offers dependency graph and semantic list projections of the same
Task-Spec inventory. Frontier, backlog, and completed groups remain explicit.
Dispatchability, blockers, dependencies, sign-off, agent, and iteration budget
come only from the snapshot.

### Runs

Runs groups durable attempts by task. RED, retry, resumed, and settled records
remain separate. Null attempts and missing checkpoints are shown as unavailable,
not inferred.

### Docs

Docs is a searchable master-detail reader for observed documents, hash-bound
artifacts, and settlement receipts. Selecting a file immediately renders it in
the same surface, with previous/next navigation and an optional full-screen
reader. A digest is never presented as semantic correctness. Receipt integrity
and freshness are separate fields. Artifact content is fetched by relative
path, snapshot ID, and SHA-256 through a GET-only endpoint. Markdown is rendered
without raw HTML or remote images. PDFs become bounded, text-only page previews;
their visual layout and raw bytes remain omitted. The viewer rejects any
response that does not match the requested proof tuple.

### Activity

Activity unifies current snapshot signals and typed issues into one readable
feed. It is explicitly a bounded observation, not a durable audit history or an
inferred event timeline.

### Health

Health presents required and optional checks plus typed issues. A healthy
component does not erase a blocking issue in another domain.

## Selection and truth

Selection is always `{kind, id}`. The inspector resolves typed pass, swimlane,
leg, task, run, receipt, health, signal, issue, and artifact entities. Activity
includes only signals with an explicit matching entity reference. The frontend
never parses labels or prose to invent lineage. The CLI performs bounded,
schema-aware extraction of decomposition Markdown and marks ambiguous,
malformed, cyclic, or dangling structures unavailable.

Transport state remains outside the semantic snapshot:

- `loading` means the previous projection remains visible during refresh.
- `stale` means a last-good snapshot is visible after a refresh failure.
- `fixture` is labeled as replay data and never claimed as a live workspace.
- malformed v3 snapshots are rejected at the client boundary.

## Motion and accessibility

- The shell uses one restrained arrival transition.
- Proven edges may carry a quiet traveling highlight. Waiting edges remain
  still.
- The viewport auto-fits only on first load or explicit user request.
- Reduced-motion preference removes traveling highlights and nonessential
  transitions.
- Keyboard focus uses a visible Forge Gold outline.
- Status never depends on color alone.
- Artifact dialogs trap focus, close on Escape, and restore focus to the
  launcher.
- Small screens receive textual alternatives for graph exploration.
