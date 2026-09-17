# Brief-Spec Independent Review — Grok 4.6

## Reviewer context

- Provider and model: xAI Grok 4.6 (`xai-grok-4.6`).
- Harness or interface: Grok Build TUI.
- Date: 2026-08-13.
- Repository URL: https://github.com/luanmorenommaciel/brief-spec
  - The review prompt named https://github.com/luanmorenommaciel/briefspec.
  - Authenticated `gh repo view` resolves that remote to the private repository `luanmorenommaciel/brief-spec`.
  - The local remote is `https://github.com/luanmorenommaciel/briefspec.git`.
- Branch and commit inspected: `main` at `4adf20412028aa858a982c2149c3622327efa11a` (“New Brief-Spec Release”, 2026-08-13T14:05:31Z).
- Latest release observed: GitHub release `v0.2.0` (“BriefSpec 0.2.0 — first-class Claude Code experience”), published 2026-07-31T20:40:31Z, pointing at commit `7ffe275b0c56358d7f0b13abe8a2363bfe61086a`. Tags `v0.1.0` and `v0.2.0` exist. No `v0.2.1`, `v0.3.0`, `v0.4.0`, or `v0.5.0` tag exists.
- Materials available:
  - Clean local checkout at `/Users/luanmorenomaciel/GitHub/briefspec`, branch `main`, up to date with `origin/main`, working tree empty.
  - Authenticated GitHub access via `gh` to the private repository (releases, tags, workflow runs, repository metadata).
  - Source, docs, schemas, skills, tests, workflows, renderer packages, and pilots in that checkout.
- Research providers used: Tavily (`tavily_search`), Exa (`web_search_exa`), native `web_search` / `web_fetch`, and GitHub CLI. GitHub MCP `list_releases` / `get_file_contents` returned 404 because the repository is private.
- Important inspection limitations:
  - The GitHub repository is **private** (`visibility: private`, `stargazerCount: 0`, `forkCount: 0`, `issues.totalCount: 0`). Public unauthenticated inspection is not possible.
  - I did not run the test suite, install packages, execute live hosts, or open ignored live-e2e artifacts. Local-gate numbers in `docs/verification.md` are **reported**, not re-executed.
  - I did not read any other files under `output/`.
  - I treated the inspected local `main` / GitHub `main` pair as authoritative for the **implemented** 0.5.0 candidate, and GitHub release `v0.2.0` as authoritative for the **published** product.
  - Local `main` and published `v0.2.0` are not equivalent: `git diff --stat v0.2.0..HEAD` reports 105 files changed, +9917 / −696.

Truth-boundary used throughout:

| State | What it is here |
| --- | --- |
| Proposed | CHANGELOG 0.3.0 / 0.4.0 / 0.5.0 text and unpublished candidates |
| Implemented | `main` @ `4adf204`, package version `0.5.0` |
| Locally validated | Reported in `docs/verification.md`; not re-run in this review |
| Live-host validated | Partial smoke reported; Grok and full matrix on hold |
| Hosted-CI validated | Not validated. HEAD CI run `31708342030` failed in seconds |
| Published | GitHub `v0.2.0` only. No PyPI `brief-spec` or `briefspec` package was found |

## Executive verdict

Brief-Spec has become a serious presentation-and-verification protocol for coding-agent handoffs, not a prompt pack. The Outcome Brief, status vocabulary, inspectable-proof rule, fail-open hooks, and “this is not a second brain” stance are unusually disciplined for a 0.x agent tool. The 0.5.0 candidate then layers type-aware explanations, a canonical delivery envelope, deterministic downloads, and eight harness adapters on top of that contract.

That ambition is now the risk. The public story is still `v0.2.0`. The implemented story is an unpublished mega-release that folds 0.3, 0.4, and 0.5 together. The repository is private, identity is split across `briefspec` / `brief-spec` / two GitHub usernames / two schema hosts, hosted CI is blocked by billing, and Grok is labeled “verified” while its live gate is on hold. The 160-prompt classification “corpus” is eight keyword templates repeated twenty times. Worst: 0.5.0 puts type-specific sections *before* Status / Outcome / Human action, which contradicts the product’s own cognitive theory.

Do not add harnesses, renderers, or protocol surface. Make one public identity, restore hosted CI, measure whether people find status and proof faster, and decide whether types belong in front of the brief. Until those conditions hold, treat 0.5.0 as dogfood, not as a standard.

## What Brief-Spec has become

Brief-Spec is a **last-mile reading contract** for coding agents. It does not try to make models reason the same way. It tries to make the human handoff occupy the same slots every time:

1. What kind of work this was.
2. What is now true.
3. What the human must do.
4. What can be inspected.
5. What is still unknown.

The durable product is not “another skill.” It is a **bounded Markdown contract** (`outcome-brief`, `session-checkpoint`) plus an optional **canonical object** that can be projected into JSON, HTML, ZIP, PDF, or audio without inventing a second summary. A small, dependency-free Python control plane classifies locally, validates field order and status semantics, installs into host hook files with receipts, and fails open when it cannot safely proceed.

The strongest mental model is therefore:

```text
authoritative work
  → typed explanation (optional, type-specific)
  → Outcome Brief or Session Checkpoint (required human surface)
  → canonical delivery object
  → verified downloads
  → human judgment
```

The first layer is new in 0.5.0 and still unproven. The middle layer is the product people would actually adopt. The last layers are infrastructure that only matter after the middle layer is trusted.

## Strongest foundations to protect

1. **Honest terminal statuses with semantic constraints, not decorative labels.**
   `[direct]` `src/briefspec/markdown.py` (`validate_outcome`) rejects `DONE` with required human action or unresolved gaps, requires action for `REVIEW` / `DECIDE` / `BLOCKED`, requires gaps and next actions for `BLOCKED` / `FAILED`, and requires an open item for `DECIDE`. The Outcome Brief skill states the same rules. This is the rare agent format that makes false completion structurally expensive.

2. **Inspectable proof as a first-class field, with basis labels that do not upgrade evidence.**
   `[direct]` Proof items must contain a locator (path, command, URL, issue, PR, or commit). Missing `[direct|derived|reported]/[pass|fail|info]` is a warning, not a silent pass. `docs/theory.md` is explicit that contract validation is not truth validation. Keep this distinction.

3. **Fail-open hooks, one repair, and no raw-prompt memory.**
   `[direct]` `hooks.py` catches exceptions and returns an empty allow decision. Repair is attempted at most once per turn and honors native `stop_hook_active`. `state.py` / tests assert prompts are not persisted. Hook input is capped at 1 MiB. Transcript reads are bounded to 256 KiB and refuse symlinks. This is the correct trust model for a presentation layer that sits on someone else’s agent.

4. **Transactional installation with ownership receipts and foreign-file refusal.**
   `[direct]` `installers.py` refuses to overwrite unmarked files, snapshots paths, rolls back partial writes, uninstalls only receipt-owned unmodified bytes, and keeps merged foreign hook entries. Multi-runtime `setup all` is one transaction. This is how a cross-host installer must behave or it will be uninstalled after the first conflict.

5. **An explicit non-goal: Brief-Spec is not a second brain.**
   `[direct]` README, `docs/theory.md` §11, and `SECURITY.md` all say the brief is never more authoritative than its source, and that Nexo/Obsidian ingestion must be explicit. In a market full of memory layers, this boundary is the product’s long-term credibility.

## Findings

### F1. Public identity is incoherent, and the repository cannot host a standard while private

- Severity: **critical**
- Evidence: `[direct]`
- Observation: Authenticated GitHub metadata shows `luanmorenommaciel/brief-spec` is private, with 0 stars, 0 forks, and 0 issues. README still advertises a “Public release 0.2.0” badge pointing at `https://github.com/luanmorenomaciel/briefspec/releases/tag/v0.2.0` (different username, one `m`). Clone / install URLs use `luanmorenommaciel/briefspec.git`. `pyproject.toml` and plugin metadata use `luanmorenommaciel/brief-spec`. Schema `$id`s split between `https://brief-spec.dev/...` and `https://briefspec.dev/...`. Tavily/Exa searches for `brief-spec.dev` and PyPI `brief-spec` / `briefspec` returned no first-party public package or site. `docs/verification.md` still describes the 0.5.0 source as “this uncommitted working tree,” but `main` is a clean commit of that candidate.
- Why it matters: A cross-harness standard needs a single name, a clonable URL, a version that means one thing, and public artifacts. Right now an outsider cannot find, install, cite, or implement against Brief-Spec without private access. Dual names also leak into markers (`briefspec:outcome:v1` vs `brief-spec:typed:v1`), CLIs, state directories, and schema IDs.
- Recommended response: Pick `brief-spec` as the public name. Make the GitHub repository public under that name, or stop calling `v0.2.0` a public release. Fix the README badge username. Publish one canonical clone URL. Keep `briefspec` as a documented 0.x alias only. Do not rename markers again in 0.x.
- What would verify: An unauthenticated `GET` of the README, release, and schemas succeeds; `uv tool install git+https://github.com/luanmorenommaciel/brief-spec.git@v0.2.0` works from a clean machine; every first-party URL in README/`pyproject.toml`/docs resolves to the same repository.

### F2. The 0.5.0 candidate is three unpublished releases stacked on a blocked publication path

- Severity: **critical**
- Evidence: `[direct]`
- Observation: CHANGELOG folds unpublished 0.3.0 (canonical delivery) and 0.4.0 (PDF/audio) into 0.5.0 (types + five more harnesses). Package version on `main` is `0.5.0`. Published GitHub release remains `v0.2.0`. `docs/verification.md` forbids tagging while hosted CI is blocked. HEAD Actions run `31708342030` (“New Brief-Spec Release”) concluded `failure`; jobs ended in 2–5 seconds with empty steps, matching the earlier billing/spending failure `31516322113`. Live Grok is Hold. OpenAI audio is untested. PyPI Trusted Publisher registration is still listed as an open prerequisite.
- Why it matters: Shipping 0.5.0 as “the next version” asks adopters of 0.2.0 to absorb type routing, a v2 envelope, two optional renderers, and five additional hosts in one jump, with no hosted proof. If 0.5.0 later needs a breaking fix, the compatibility story becomes unreadable.
- Recommended response: Do not tag 0.5.0 until hosted CI is green on this revision. Consider publishing a thinner public increment rather than the whole fold. If the fold stays, the release notes must state exactly which 0.2.0 behaviors remain byte-compatible.
- What would verify: A hosted Actions run on `4adf204` (or a successor) is green for the required matrix; a GitHub Release and PyPI upload contain identical digests; `docs/verification.md` is rewritten against that tagged revision, not an “uncommitted” tree.

### F3. Type-aware rendering puts explanation before Status, contradicting the product’s own theory

- Severity: **high**
- Evidence: `[direct]` + `[derived]`
- Observation: `docs/theory.md` argues the scannable contract is `Status → Outcome → Human action → Proof → Gaps → Next → Open`. The 0.5.0 router skill requires a typed wrapper whose first visible headings are the type profile sections, with the Outcome Brief nested after them. `render_html()` emits those typed `<section>`s first, then the brief fields. A review therefore leads with Scope / Verdict / Findings before the reader sees `Status:`. HTML also wraps Proof and Gaps in `<details>`, which hides the second-layer decision support the theory said should stay visible.
- Why it matters: If the thesis is “stop searching for the signal,” putting 3–6 new sections in front of the signal is a self-inflicted reload. Types may help writers. They currently tax readers.
- Recommended response: Keep type sections after, or clearly below, Status / Outcome / Human action in every human projection (Markdown, HTML, PDF, spoken). Alternatively, make the typed wrapper writer-only and keep the default download as the 1.0 brief. Do not open Proof behind `<details>` in the default HTML.
- What would verify: A timed scan study (see Evaluation plan) where users find status and action on typed vs untyped briefs. Default HTML snapshot shows Status in the first screenful at 1280×800 and 390×844.

### F4. Classification quality is not evidenced; the 160-prompt gate is circular

- Severity: **high**
- Evidence: `[direct]`
- Observation: `docs/verification.md` claims “the 160-prompt labelled corpus meets its macro and per-type F1 gates.” `tests/test_work_types.py` builds those 160 prompts from eight templates that already contain the regex keywords (`Review pull request`, `Debug failing bug`, `Explore codebase…entry points`, `Research the latest market…web sources`, `Handle production incident SEV1`). The classifier is a priority-ordered English regex table. Ambiguous text falls back to `general`. Implementation rules include `\b(?:implement|build|create|write|add|remove|refactor)\b` and `\b(?:change|update|modify|patch|migrate|configure|install)\b`, which will fire on ordinary coding chat.
- Why it matters: A release-blocking F1 number that the templates cannot fail is not a quality signal. Sticky misclassification will lock a session into the wrong explanation order until a “new task” pivot phrase appears.
- Recommended response: Replace the template corpus with a held-out set of real, anonymized prompts (or a published synthetic set that is not keyword-aligned). Report confusion pairs, not only macro F1. Add a non-English and “mixed intent” slice. Consider treating inferred types as hints in hook context rather than as an enforce-time wrapper requirement.
- What would verify: A versioned corpus file with prompt IDs, labels, and annotator notes; CI fails on a *different* held-out set; live-host logs show inferred vs explicit vs fallback rates.

### F5. “Verified” harness maturity overstates what live evidence supports

- Severity: **high**
- Evidence: `[direct]`
- Observation: `docs/compatibility.md` and `harnesses.py` mark Codex, Claude, OMP, Grok, and Kimi as `verified`. `docs/verification.md` reports four smoke passes and **Grok Hold**, plus “the full matrix remain open.” Adapter code is thin: only Codex, Claude, and Copilot have dedicated modules, and those three files are one-line wrappers around `normalize_common`. OMP, Grok, Kimi, Cursor, and Goose all share the common normalizer. Grok’s own note says passive hook stdout is ignored, so user-facing routing is the skill, not the hook. Subagent events are parsed and installed for some hosts, but `triggers.py` / `hooks.py` never update work-item state from `SUBAGENT_*`.
- Why it matters: “Verified” is being used as a product word. The project’s own compatibility doc says a harness is verified only after its executable has loaded and exercised the integration. Grok does not meet that bar. Advertising eight hosts, five of them “verified,” teaches people that Brief-Spec is done across the market when it is a two-to-four-host dogfood with honest gaps.
- Recommended response: Demote Grok to `preview` or `hold` until the native read/list path is stable and the required type/presentation matrix passes. Keep Copilot / Cursor / Goose experimental. Stop expanding the harness table.
- What would verify: Compatibility table matches the latest verification record commit-for-commit; `brief-spec capabilities all --json` exposes the same maturity strings the docs use.

### F6. Compatibility tax is already large, and 0.5.0 adds another naming plane instead of retiring one

- Severity: **medium**
- Evidence: `[direct]`
- Observation: The 0.x compatibility surface includes `briefspec` CLI and import, `BRIEFSPEC_HOME`, `.briefspec.toml`, `briefspec:*` markers, legacy schemas, legacy receipts, and the `briefspec.renderers` entry-point group. 0.5.0 adds `brief-spec`, `brief_spec` (a `__path__` alias to `briefspec`, not a second implementation), `BRIEF_SPEC_HOME`, `brief-spec:typed:v1`, `brief-spec-delivery/2.0`, and `brief-spec.dev` schema IDs while still referencing `briefspec.dev` from inside the v2 schema. Renderer packages are named `brief-spec-renderer-*` in metadata and live in directories still called `briefspec-renderer-*`.
- Why it matters: Compatibility is correct engineering. Two public identities is not. Every new adopter has to ask which string to grep, which env var to set, and which schema `$id` is canonical.
- Recommended response: Freeze the dual surface. Document a single “write this, accept that” table. Do not add a third marker family. Plan a 1.0 marker cut only with a mechanical migrator and a two-minor overlap.
- What would verify: A published compatibility matrix with one “write” column; `verify-release.py` fails if a new public name is introduced without an explicit allowlist.

### F7. Multi-agent `work_items` are a schema without an operational loop

- Severity: **medium**
- Evidence: `[direct]`
- Observation: Delivery 2.0 requires a `work_items` array and validates activity vocabulary. Installers can subscribe to `SubagentStart` / `SubagentStop`. Session state stores one work type and no child work IDs. `process_event` does not create, update, or close work items. `new_delivery()` defaults `work_items` to `[]`. The skill says “subagents contribute evidence; the main task owns the user-facing brief,” but nothing in the control plane records that contribution.
- Why it matters: The envelope looks ready for multi-agent provenance. In practice every export will say “no work items” unless a human or host fills them by hand. That invites false completeness in the 2.0 object.
- Recommended response: Either implement a minimal parent/child work-item ledger from subagent events, or make `work_items` optional in 2.0 until a host actually supplies them. Do not market multi-agent activity as shipped.
- What would verify: A live Codex or Grok run with one subagent produces a delivery whose `work_items` contain the child headline, activity, and result ref — or the schema stops requiring the field.

### F8. Optional renderers and the eight-host installer are maintenance before demand

- Severity: **medium**
- Evidence: `[direct]` + `[derived]`
- Observation: PDF depends on Playwright Chromium plus Poppler. Audio depends on macOS `say` + `ffmpeg`, or consented OpenAI TTS. CI defines Ubuntu PDF and macOS audio jobs that currently cannot run. There are no public users. Apex pilot results are an untracked template. The core package is still dependency-free; that part is right. The *release* is not: 0.5.0 publication is blocked on renderer CI and a five-host live matrix.
- Why it matters: Every unpublished renderer gate delays the only artifact users can adopt: a valid Outcome Brief in the hosts they already run.
- Recommended response: Keep renderers optional and out of the release-critical path. Publish core without requiring PDF/audio jobs. Do not add video, slides, or another TTS vendor.
- What would verify: A core-only release workflow that can go green without Playwright, ffmpeg, or OpenAI.

### F9. The verification record is already drifting from the tree it describes

- Severity: **medium**
- Evidence: `[direct]`
- Observation: `docs/verification.md` was updated 2026-08-12 and still says the candidate is uncommitted. HEAD is a 2026-08-13 commit. The cited failed CI URL uses `.../briefspec/actions/runs/31516322113`; the repository name is now `brief-spec`, and a newer failed run exists on HEAD. Local backup paths and machine-specific state directories are recorded as evidence locators.
- Why it matters: This project’s credibility is its refusal to blur local, live, and published evidence. A stale verification record is the first place that blur will be noticed.
- Recommended response: Treat `docs/verification.md` as a per-revision ledger. On every release-candidate commit, rewrite the truth-boundary table. Keep machine-local paths in an ignored sidecar, not in the published doc.
- What would verify: The verification record names the commit SHA, the hosted run URL that actually corresponds to that SHA, and no “uncommitted” language when the tree is clean.

### F10. Adjacent market is filling the “brief” and “skill” nouns without Brief-Spec being visible

- Severity: **opportunity**
- Evidence: `[external]`
- Observation: Current search (Exa/Tavily, 2026-08-13) surfaces several public “brief” systems: `openperf/brief` (agent-to-agent delegation), `jikanter/brief` (human-written `.brief.md` for agents), `ENEmyr/brief` (interactive decision docs), plus GitHub Spec Kit and the Agent Skills standard at `agentskills/agentskills` / agentskills.io. None of the first-page results were this repository. Agent Skills is now an open, cross-product `SKILL.md` format with progressive disclosure.
- Why it matters: Brief-Spec’s portable skills already look like Agent Skills. Its actual differentiator — validated terminal handoffs and verified delivery — is invisible while the repo is private and the name collides with unrelated “brief” protocols. If a public handoff standard emerges, it will not be this one by default.
- Recommended response: Publish the Outcome Brief as a small, implementable spec that any Agent Skill can emit, independent of the Python installer. Do not try to win the word “brief” by adding delegation or spec-driven-development features those other projects already own.
- What would verify: An unauthenticated spec page that a second implementation can satisfy with only Markdown + a JSON schema; at least one non-author harness emitting a valid brief without installing the Python package.

## Ten opportunities

1. **Lead every human projection with Status / Outcome / Human action.**
   User impact 5 · Strategic leverage 5 · Evidence confidence 5 · Effort S · Risk low · Horizon: next release.
   Reorder typed Markdown, HTML, and PDF so the 1.0 brief slots remain the first recognition surface.

2. **Publish one identity and open the repository.**
   User impact 5 · Strategic leverage 5 · Evidence confidence 5 · Effort M · Risk medium · Horizon: next release.
   Public `brief-spec` repo, fixed clone/badge URLs, reserved PyPI names, single schema host.

3. **Make Outcome Brief implementable without the Python control plane.**
   User impact 5 · Strategic leverage 5 · Evidence confidence 4 · Effort M · Risk low · Horizon: next release.
   A two-page spec + schema + golden Markdown fixtures that any Agent Skill host can emit.

4. **Replace the template classifier corpus with a real evaluation set.**
   User impact 3 · Strategic leverage 4 · Evidence confidence 5 · Effort M · Risk low · Horizon: next release.
   Versioned prompts, confusion matrix, inferred-vs-explicit live rates.

5. **Demote maturity labels to match live gates.**
   User impact 3 · Strategic leverage 4 · Evidence confidence 5 · Effort S · Risk low · Horizon: next release.
   Grok → hold/preview; keep experimental hosts out of the default `setup all --require` story.

6. **Measure the Apex questions on live tasks, not only synthetic fixtures.**
   User impact 5 · Strategic leverage 5 · Evidence confidence 3 · Effort M · Risk medium · Horizon: next release.
   15-second status/action scan, evidence-open rate, wrong-status rate, checkpoint annoyance.

7. **Core-only publication path that does not wait on PDF/audio.**
   User impact 3 · Strategic leverage 4 · Evidence confidence 4 · Effort S · Risk low · Horizon: next release.
   Hosted CI can release `brief-spec` without renderer jobs.

8. **Cross-harness semantic-equivalence fixture pack.**
   User impact 4 · Strategic leverage 5 · Evidence confidence 4 · Effort M · Risk low · Horizon: later 0.x.
   Same bounded brief, same canonical JSON (modulo `source.*`), on Codex and Claude first.

9. **Optional work-item ledger or optional field.**
   User impact 2 · Strategic leverage 3 · Evidence confidence 4 · Effort M · Risk medium · Horizon: later 0.x.
   Do not pretend multi-agent activity is captured until a host loop writes it.

10. **1.0 governance: schema stewardship, marker freeze, second implementation.**
    User impact 4 · Strategic leverage 5 · Evidence confidence 3 · Effort L · Risk high · Horizon: 1.0.
    A standard needs a second emitter that is not this repo.

## Three highest-conviction bets

### Bet 1 — Make the Outcome Brief the public standard; keep 0.5.0 machinery behind it

This dominates the opportunity list because every other feature is a projection of, or a router into, the seven-field brief. Users do not adopt “type-aware verified delivery.” They adopt “I can see what happened and what I owe.” A public, host-agnostic Outcome Brief spec can be emitted by a copied `SKILL.md` with no installer. The Python CLI then becomes the optional validator and bundler, which is the right adoption order.

- User problem: re-parsing every agent’s ending.
- Measurable outcome: in a 20-task live sample across two hosts, median time to identify status, required action, and one proof locator ≤ 15 seconds; wrong-status rate ≤ 10%.
- Must be true first: Status remains the first human field; at least two hosts actually emit valid briefs in live sessions; the spec is public.

### Bet 2 — Close the publishability gap before adding product surface

This dominates renderer, harness, and schema work because unpublished software cannot become a standard, and a private repo with colliding names cannot be cited. Restore billing, get one hosted run green, align README/clone/package/release URLs, and publish either a thin 0.3 or a gated 0.5.0 from identical bytes.

- User problem: “I cannot install the thing the docs describe.”
- Measurable outcome: unauthenticated install of the advertised release succeeds; hosted CI on that tag is green; `docs/verification.md` names that tag and SHA.
- Must be true first: GitHub Actions spending is restored; repository visibility decision is explicit; PyPI names are reserved.

### Bet 3 — Treat cross-host semantic equivalence as the standard test, not host count

This dominates “add Cursor / Goose / more events” because a standard is a preserved meaning, not a longer compatibility table. Prove that a review Outcome Brief produced under Codex and Claude validate the same fields, export the same canonical JSON (except `source`), and verify at `rendered` / `delivered`. Two hosts done completely beat eight hosts advertised.

- User problem: “I run two agents and still learn two ending formats.”
- Measurable outcome: ≥ 90% field-level semantic match on a 10-scenario fixture pack for Codex and Claude; delivery SHA differs only in declared source metadata.
- Must be true first: both hosts emit the 1.0 brief reliably; export is deterministic; live runs are retained as sanitized fixtures.

## One contrarian bet

**Do not publish type classification as part of the next public release. Ship the Outcome Brief + installer + validator. Keep types as an off-by-default experiment.**

- Strongest argument for: The 0.5.0 typed wrapper is the first Brief-Spec change that can *increase* reading cost. Classification is regex theater with a circular F1 gate. Enforce-mode already asks hosts to wrap a valid brief in a typed region whose headings precede Status. If the next public release trains people on that order, you will not get the order back. Other reviewers will want to “finish 0.5.0” because the code exists. Shipping it is path dependence, not product evidence.
- Strongest argument against: Types are the only 0.5.0 feature that changes the *explanation*, not just the envelope. Without them, Brief-Spec is a seven-field footer and may look like a linter for Markdown. The profiles are small, local, and honest about fallback. Turning them off after writing the v2 schema creates another compatibility plane.
- Evidence needed to decide: A 20-task within-subject comparison of typed-first vs brief-first endings on time-to-status, time-to-action, evidence-open rate, and “I had to re-read” scores. If typed-first wins, publish types. If it loses or ties, keep types out of the default public contract.

## What not to build

- A second brain, memory graph, or automatic Nexo/Obsidian ingest. The project already knows this. Do not blur it for “knowledge features.”
- Agent-to-agent delegation, task briefing, or spec-driven development workflows. `openperf/brief`, Spec Kit, and `pb-spec` already occupy those nouns. Brief-Spec should remain the *handoff after work*, not the *order to start work*.
- More experimental harnesses (Windsurf, Cline, Aider, OpenCode, custom orchestrators) before two hosts are live-equivalent.
- Additional renderers: slides, video, shareable web apps, hosted viewers. Each one becomes a release gate.
- A custom type marketplace or user-defined primary types. `types_document()` already sets `custom_primary_types: false`. Keep it false through 1.0.
- Cloud services, accounts, or telemetry that receive brief contents. The Copilot zipapp exists so cloud jobs stay network-free. Do not add a Brief-Spec backend.
- A model-hosted classifier or any network call inside `classify`. Local and bounded is the point.
- Breaking the 1.0 Outcome Brief / Session Checkpoint field order to “clean up” names in 0.x.
- Marketplace / plugin duplication across native Codex and Claude plugin stores on top of the portable installer, unless a live gate proves the native path is the only way those hosts load skills.

## Proposed next-release steel thread

**Thesis to prove:** A reviewer using Claude Code and Codex can finish a real review, recognize status/action/proof in one glance, and independently verify a download — without types, PDF, or new hosts being in the critical path.

- User scenario: An engineer asks two hosts to review the same small pull request in a disposable trusted repository that contains only `evidence.txt` and the change under review. They need to decide whether to merge.
- Entry point: Already-installed user-scope Brief-Spec on Claude Code and Codex. No new installer features. Default policies remain `suggest`.
- Classification behavior: Record whatever the local classifier infers, but **do not require** the typed wrapper for a valid terminal handoff. If a type is shown, it must not precede Status.
- Explanation behavior: Hosts write a normal review, then one Outcome Brief. Status should be `REVIEW` or `DECIDE` with explicit human action and at least one inspectable proof locator.
- Canonical data changes: None required. If a delivery object is emitted, `classification.origin` may be `inferred` or `fallback`; `explanation` may be a default general profile. Do not bump to a 3.0 schema.
- Download or delivery changes: `brief-spec export` to Markdown + JSON + HTML and `brief-spec bundle` / `verify --level rendered` / `deliver` / `verify --level delivered`. HTML must show Status above any type sections and must not hide Proof behind closed `<details>`.
- Harnesses involved: Codex and Claude Code only.
- Security and privacy boundary: Disposable repo, no credentials in fixtures, no raw transcripts retained, `BRIEF_SPEC_HOME` isolated, hooks fail open, no network renderers.
- Automated tests: existing outcome invariants; a new snapshot test that HTML/Markdown lead with Status; export determinism; Codex/Claude fixture equivalence modulo `source`.
- Live acceptance test: one sanitized review scenario per host, already approximated in `docs/verification.md`, plus a human 15-second scan on the two resulting briefs.
- Success metric: both hosts produce a validator-valid Outcome Brief; a second person identifies status, action, and one proof locator in ≤ 15 seconds on each; bundle verifies at `delivered`; hosted CI on the candidate revision is green.
- Explicit exclusions: Grok, Kimi, OMP, Copilot, Cursor, Goose; PDF; audio; typed-wrapper enforcement; repository rename as a blocker *after* identity URLs are consistent; PyPI Trusted Publisher if GitHub Release + wheel digest is enough for this increment.

## Evaluation plan

| Question | Metric | Method | Gate |
| --- | --- | --- | --- |
| Classification quality | Per-type F1, confusion pairs, origin mix | Held-out labeled prompts; live origin counters | Inferred F1 ≥ 0.70 on held-out set; template corpus is not the release gate |
| Explanation usefulness | Task-specific rubric: did the first three visible sections answer the type’s first question *without* hiding status | Blind rating of 20 endings | Median usefulness ≥ 4/5 *and* status still first |
| Time to identify status, action, proof | Median seconds, 3 raters | Apex-style timed scan on live briefs | ≤ 15 s median |
| Evidence-open success | Share of proof items whose locator opens to the claimed artifact | Manual + `verify --level resolved` | ≥ 90% |
| Wrong-status rate | Share of briefs whose status a second reviewer rejects | Dual annotation | ≤ 10% |
| Cross-harness semantic equivalence | Field-level match on status, action presence, proof locators, gaps | Same scenario on two hosts | ≥ 90% on Codex vs Claude |
| Download completion | Export/bundle commands exit 0 and write declared formats | CI + one live export | 100% on core formats |
| Delivery verification success | `verify --level delivered` on the copied ZIP | CI fixture + one live deliver | 100% on untampered bundles; 100% reject on mutated bytes |
| Installation and rollback reliability | Conflict, rollback, uninstall, nested-directory hook tests + one real user-scope repair | Existing installer tests + hosted clean-room job | All required installer tests pass on hosted CI |
| User trust | “I would rely on this status without re-reading the transcript” (1–5) plus evidence-open behavior | Post-task survey | Mean ≥ 4 only if evidence-open ≥ 90%; a high trust / low evidence-open score is a **fail** (false confidence) |

Do not use hosted-CI-blocked runs, doctor `--probe` success, or template-corpus F1 as substitutes for the rows above.

## Roadmap recommendation

### Now

1. Restore GitHub Actions spending and obtain one green hosted run on a named SHA.
2. Repair public identity: README badge username, clone URL, repository name decision, schema host.
3. Rewrite `docs/verification.md` against that SHA; stop saying “uncommitted.”
4. Demote Grok maturity to match the live hold.
5. Reorder human projections so Status / Outcome / Human action lead.
6. Turn off typed-wrapper enforcement for the next public increment.
7. Split renderer jobs out of the core release gate.

**Gate:** hosted CI green + identity URLs consistent + verification record matches the tree.

### Next

1. Public repository, or an explicit “source-available later” statement that stops using the word public.
2. Held-out classification corpus and live origin metrics.
3. Codex ↔ Claude semantic-equivalence pack and the 15-second human scan.
4. Public Outcome Brief spec page that does not require the installer.
5. Reserve PyPI names; publish only after the steel thread passes.

**Gate:** steel-thread success metric + unauthenticated install of the advertised release.

### Later (remaining 0.x)

1. Re-evaluate types with the A/B evidence from the contrarian bet.
2. Stabilize Grok, then Kimi/OMP, as individually gated hosts.
3. Optional work-item ledger if a host actually emits subagent structure.
4. PDF/audio as version-aligned extras after core is published.
5. Marker-alias documentation freeze.

**Gate:** per-host live matrix, not a combined “five hosts or nothing” rule.

### 1.0

1. Frozen Outcome Brief 1.0 and Checkpoint 1.0.
2. One canonical delivery schema with a published migrator from 0.x aliases.
3. Three live-verified hosts, two of them with public sanitized fixtures.
4. A second independent emitter.
5. Measured reading-cost improvement vs unstructured endings.

**Gate:** second implementation + human study + public schemas.

### Reject or defer

- New harnesses.
- New renderers.
- Custom primary types.
- Hosted viewer / SaaS.
- Delegation / spec-kit / second-brain features.
- Network classification.
- Breaking 1.0 field names before 1.0.

Dependencies: identity and CI (Now) unlock publication (Next). Publication and measurement unlock types-as-default (Later). Later host work must not block Now.

## Risks and failure modes

- **Technical:** Regex classification will systematically prefer `implementation` and `operations` on ordinary verbs (`install`, `release`, `update`). Sticky sessions will then demand the wrong section order. Dual packages that share `__path__` can confuse packaging tools and import-time version checks.
- **Product:** Typed-first HTML/Markdown can make Brief-Spec feel like more boilerplate. Users will disable skills. The project then concludes “handoffs do not work” when the wrapper is what failed.
- **Security and privacy:** Hooks execute local code at lifecycle boundaries. A compromised wheel or a malicious project install can run at stop time. Fail-open is correct for availability and wrong if people treat hooks as a security control (`docs/architecture.md` already says they are not). OpenAI audio, if enabled, is the first credentialed network path; keep it consented and out of core. HTML CSP is strong (`default-src 'none'`); do not loosen it for “richer” downloads.
- **Ecosystem:** Private repo + colliding “brief” noun means the Agent Skills ecosystem will standardize something else. If Brief-Spec later goes public, it may look like a late clone of whichever handoff format shipped first.
- **Maintenance:** Eight hosts × user/project × native/portable × canonical/legacy names is a combinatorial installer. `installers.py` is already 1,110 lines. Every new host multiplies rollback cases.
- **Adoption:** The install story requires Python 3.11+, `uv`, host hook trust, and a version pin. The 0.2.0 vs 0.5.0 split means the README cannot tell a beginner which command is true. Private GitHub makes the advertised `uv tool install git+...` unusable to strangers.
- **Supply-chain:** Release workflow uses pinned Actions SHAs and Trusted Publishing intent — good. Hosted CI not running means those controls are unexercised on 0.5.0. `dist/` in the tree still contains 0.1.0 / 0.2.0 / 0.2.1 artifacts while the source is 0.5.0; that invites installing the wrong wheel from a clone.

## Open questions

1. Should the GitHub repository be public before 0.5.0, or is privacy intentional until the candidate is tagged?
2. Is the next public number 0.3.0 (thin) or 0.5.0 (fold)? This is a product decision, not a git decision.
3. Do any non-author users currently run 0.2.0? There are no issues and no stars; if the answer is “only the author,” compatibility cost is lower than the docs imply.
4. Does Grok Build 1.0.x’s ignored passive-hook stdout make native Grok support structurally different from Codex/Claude, and should the product treat Grok as skill-only?
5. Will a second team implement the Outcome Brief without the Python package? If no, this is a personal operating system, not a standard.
6. Is 15 seconds the right scan budget, or should the gate be “first screenful at mobile width”?
7. Should inferred classification ever be allowed to *block* a stop, or only to add context?
8. Are `brief-spec.dev` and `briefspec.dev` owned? Schema `$id`s currently assert them.
9. What is the acceptable false-confidence rate if briefs become so tidy that people stop opening proof?
10. Should `dist/` historical wheels remain in git, or is that an accidental distribution channel?

## Evidence ledger

| Claim | Label | Locator | Observed | Proves | Does not prove |
| --- | --- | --- | --- | --- | --- |
| Inspected commit is `4adf204` on clean `main` | `[direct]` | Local `git rev-parse` / `git status`; `gh api repos/luanmorenommaciel/brief-spec/commits/4adf204` | 2026-08-13 | Local and GitHub `main` match | That this commit will be tagged |
| Latest published release is `v0.2.0` at `7ffe275` | `[direct]` | `gh release view v0.2.0 --repo luanmorenommaciel/brief-spec`; `git rev-parse v0.2.0^{}` | 2026-08-13 | Published ≠ implemented 0.5.0 | Quality of 0.2.0 in the field |
| Repository is private, 0 stars / forks / issues | `[direct]` | `gh repo view luanmorenommaciel/briefspec --json` | 2026-08-13 | No public community signal | Future visibility plans |
| README badge uses a different GitHub username | `[direct]` | `README.md` line 14 | 2026-08-13 | Public URL is wrong | That the other username’s repo exists |
| Package version on `main` is 0.5.0 | `[direct]` | `pyproject.toml` line 7; `src/briefspec/__init__.py` | 2026-08-13 | Implemented identity | Publication |
| 0.3/0.4/0.5 are unpublished and folded | `[direct]` | `CHANGELOG.md` 0.3.0–0.5.0 sections | 2026-08-13 | Release-process intent | That folding is the right product cut |
| Hosted CI on HEAD failed immediately | `[direct]` | Actions run `31708342030`, conclusion `failure`, jobs ~2–5s | 2026-08-13 | Hosted-CI not validated for this SHA | That tests would fail if they ran |
| Earlier CI failure attributed to billing | `[direct]` | `docs/verification.md` lines 20–24, run `31516322113` | 2026-08-13 | Project’s own explanation | Current billing account state |
| Verification record says “uncommitted” | `[direct]` | `docs/verification.md` line 13 | 2026-08-13 | Record is stale vs clean `main` | That local gates did not pass when written |
| Live Grok gate is Hold; four other smokes reported pass | `[direct]` | `docs/verification.md` live-host table | 2026-08-13 | Author-reported smoke status | Full type/presentation matrix; I did not re-run hosts |
| Classifier “160-prompt corpus” is eight templates × 20 | `[direct]` | `tests/test_work_types.py` `_corpus()` / `test_labelled_160_prompt_corpus_meets_release_thresholds` | 2026-08-13 | F1 gate is circular | Real-world classification quality |
| Typed wrapper and HTML put type sections first | `[direct]` | `skills/brief-spec/SKILL.md`; `src/briefspec/delivery.py` `render_html` | 2026-08-13 | Reading-order inversion exists in source | That users are slower; that is `[derived]` pending a study |
| Only three dedicated adapters, all thin | `[direct]` | `src/briefspec/adapters/{claude,codex,copilot}.py`; `registry.py` | 2026-08-13 | Most hosts share `normalize_common` | That shared normalization is incorrect |
| Subagent events are not turned into work items | `[direct]` | `triggers.py` `update_counters`; `hooks.py` `process_event`; `new_delivery` default `work_items=[]` | 2026-08-13 | Multi-agent ledger is unused | That hosts never emit useful subagent payloads |
| Core package has no runtime dependencies | `[direct]` | `pyproject.toml` `dependencies = []` | 2026-08-13 | Control plane can stay offline | Renderer extra dependency cost |
| Installer refuses foreign overwrites and rolls back | `[direct]` | `installers.py`; `tests/test_installer_failure_paths.py` | 2026-08-13 | Intended safety exists in tests | Live-host install on every advertised runtime |
| No PyPI project found for `brief-spec` / `briefspec` | `[external]` | Tavily search, 2026-08-13 | 2026-08-13 | No obvious public package page | Name reservation / yanked packages |
| Agent Skills is an open cross-product SKILL.md standard | `[external]` | https://github.com/agentskills/agentskills ; https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills (updated 2025-12-18 as open standard) | 2026-08-13 | Portable skills are a public ecosystem Brief-Spec can join | That Brief-Spec skills are spec-certified |
| Other public “brief” protocols exist | `[external]` | Exa results for `openperf/brief`, `jikanter/brief`, `ENEmyr/brief`, GitHub Spec Kit | 2026-08-13 | Name collision and adjacent categories | Market demand for Brief-Spec |
| Outcome Brief status semantics are enforced | `[direct]` | `src/briefspec/markdown.py` `validate_outcome`; `tests/test_markdown_contracts.py` | 2026-08-13 | Contract is executable | That models choose the honest status |
| HTML CSP is restrictive | `[direct]` | `delivery.py` `render_html` meta CSP | 2026-08-13 | Default HTML is offline-by-construction | Browser e2e on this SHA (reported, not re-run) |
| I did not execute tests or live hosts | `[unknown]` | This review’s method | 2026-08-13 | Scope of independent inspection | Pass/fail of 414 tests on this machine |

## Final recommendation

**ADVANCE WITH CONDITIONS**

The Outcome Brief, evidence rules, fail-open installer, and refusal to become a second brain are worth advancing. The 0.5.0 mega-candidate is not. Advance the *contract*. Condition the *release* on a public identity, a green hosted run, a reading-order fix, honest maturity labels, and a measurement of the only thesis that matters: people find status, action, and proof faster.

- Single most important next action: Restore hosted CI and publish one coherent public identity for the repository, clone URL, and advertised release — then run the Codex/Claude steel thread with Status first.
- Single most important thing Brief-Spec should protect: The Outcome Brief’s honest status / inspectable proof / explicit gaps contract, and the rule that a tidy rendering is never more authoritative than the work it describes.
