# Brief-Spec Independent Review — Z-AI GLM-5.2 (via OpenRouter)

## Reviewer context

- **Provider and model:** Z-AI GLM-5.2, routed via OpenRouter (`openrouter/z-ai/glm-5.2`). Identity taken from runtime metadata; not invented.
- **Harness / interface:** Oh My Pi (OMP) task agent, accessed through the `super.engineering` harness.
- **Date:** 2026-08-13.
- **Repository URL:** `https://github.com/luanmorenommaciel/briefspec` (git remote, no hyphen). Documentation, README badges, CHANGELOG, and `pyproject.toml` URLs instead point at `https://github.com/luanmorenommaciel/brief-spec` (with hyphen).
- **Branch and commit inspected:** `main` @ `4adf20412028aa858a982c2149c3622327efa11a` ("New Brief-Spec Release").
- **Latest release observed:** Git tags `v0.1.0` and `v0.2.0` exist locally (`v0.2.0` → `b01e684`). **No publicly accessible GitHub release or tag was resolvable at retrieval time** (see limitations). `pyproject.toml` declares `version = "0.5.0"` and the working tree is clean, so 0.5.0 is committed but untagged.
- **Materials available:** A local checkout at the inspected commit (authoritative for this review); the GitHub web/API; PyPI; and the published competitor repositories cited below.
- **Research providers used:** native web search, direct HTTP/curl probes, the GitHub MCP server (authenticated as the repository owner `luanmorenommaciel`), and direct reads of competitor repositories.
- **Important inspection limitations:**
  1. The repository is **not publicly resolvable**. `https://github.com/luanmorenommaciel/briefspec` and `https://github.com/luanmorenommaciel/brief-spec` both return HTTP 404 to unauthenticated requests; the authenticated GitHub API (as the owner) returns 404 for `luanmorenommaciel/briefspec`, and the repo is absent from the owner's 10 public repositories. I could not definitively distinguish *private* from *absent* because the MCP token may lack private-repo scope. The **local checkout is therefore the authoritative source**.
  2. I did not execute the test suite, build, or install software (prohibited). The "414 tests / 86.86% branch coverage" figure is reported by the author in `docs/verification.md`; I corroborated its *plausibility* by reading the test files but did not re-run it.
  3. The live-host smoke evidence (Codex/Claude/OMP/Kimi pass, Grok hold) is author-reported, sanitized evidence under an ignored `.briefspec/live-e2e/` tree.
  4. Hosted CI for 0.5.0 has not run (blocked by billing); I cite the author's account of this.
  5. I did not read any existing review under `output/` (two were present; both unread).

## Executive verdict

Brief-Spec is a genuinely well-engineered presentation-and-verified-delivery contract for AI coding harnesses: a dependency-free Python control plane, a 7-field Outcome Brief with status-semantic validation, deterministic multi-format projection (Markdown/JSON/HTML/ZIP, optional PDF/audio), provenance + receipts + four cumulative verification levels, and transactional installers for five "verified" and three experimental harnesses. Its strongest property is rare for this category — a rigorous, self-aware **truth-boundary discipline** that refuses to let formatting become proof and that separates *local / hosted-CI / live-host / published* states.

The fatal problem is not engineering; it is that the artifact is **not adoptable**. The repository is not publicly resolvable, no name is published on PyPI, and the README's own install command (`uv tool install git+…@v0.2.0`) would 404 for any third party. The project's central invariant — "a local commit does not prove publication" — is currently violated by its own README badge claiming a "Public release 0.2.0." Meanwhile a crowded field (Delegation Contract with an arXiv paper, OpenACCP, Relay, Agent Handoff Protocol) is forming the "agent handoff standard" conversation without Brief-Spec in it. The engineering deserves to advance; it must clear the existence gate — public repo, unblocked hosted CI, a real PyPI/GitHub release, and a reconciled identity — before breadth is worth another calorie.

## What Brief-Spec has become

In plain language: Brief-Spec is a **presentation and verified-delivery layer**, not a second brain and not an agent. When an agent finishes substantive work, Brief-Spec gives the human handoff a stable, predictable shape — a typed wrapper, one of eight explanation profiles, and a bounded Outcome Brief (`Status → Outcome → Human action → Proof → Gaps → Next → Open`) — then renders that one canonical object into deterministic Markdown, JSON, HTML, ZIP (and optional PDF/MP3) with provenance, manifests, and externally-verifiable delivery receipts. A local, rule-based classifier (no model call, no network) picks the explanation profile and stays sticky until a clear pivot. Checkpoints add a re-orientation surface (Orient / Teach / Spoken) at safe lifecycle boundaries. The whole thing installs transactionally into a host, records hash-based ownership receipts, and uninstalls without touching foreign files. The mental model is sharp: **standardize the handoff and preserve provenance; never standardize the reasoning and never let presentation upgrade epistemic state.**

## Strongest foundations to protect

1. **Status-semantic Outcome Brief contract with a real validator.** The validator enforces field order, fixed status vocabulary, list caps, and the cross-field invariants (e.g. `DONE` cannot carry required human action or gaps; `DECIDE` requires both an action and an open decision). "Formatting is not proof" is encoded, not just stated. `[direct]` `src/briefspec/markdown.py@4adf204`, `skills/outcome-brief/SKILL.md@4adf204`, `tests/test_markdown_contracts.py@4adf204`.

2. **Determinism from one canonical object.** Canonical JSON is sorted/key-stable; canonical time is captured once; the same object yields byte-identical Markdown/JSON/HTML and a deterministic ZIP; a hash-consistent-but-non-canonical rendering is rejected. This is the foundation that makes "independent re-verification" credible. `[direct]` `src/briefspec/delivery.py:98-113` (`canonical_json_bytes`, `canonical_sha256`), `tests/test_delivery.py` (`test_bundle_is_deterministic_and_manifest_is_verified`, `test_bundle_rejects_hash_consistent_noncanonical_rendering`) `@4adf204`.

3. **Bounded-state privacy discipline.** It stores counters/timestamps/hashes, never raw prompts/transcripts/tool-results/credentials; transcript reading is tail-bounded (256 KiB) and refuses symlinks; state files are private and atomic; corrupt state is quarantined. This is the property that lets a lifecycle hook sit inside a host without becoming a liability. `[direct]` `docs/architecture.md:96-110`, `tests/test_state_and_hooks.py` (`test_prompt_content_is_not_persisted`), `tests/test_adapters.py` (`test_transcript_reader_refuses_symlinks`) `@4adf204`.

4. **Fail-open + repair-once control.** Internal errors return an empty decision rather than blocking the session; an invalid terminal handoff gets at most one corrective pass; native `stop_hook_active` is honored to prevent loops. A presentation layer must never make the underlying tool unusable. `[direct]` `docs/architecture.md:71-78`, `tests/test_state_and_hooks.py` (`test_one_repair_guard_blocks_once_then_fails_open`) `@4adf204`.

5. **Self-aware truth-boundary documentation.** `theory.md` explicitly labels its cognitive-science grounding as a *design hypothesis, not a validated human-subject study*; `verification.md` separates source / local / live-host / hosted-CI / publication into distinct rows. This intellectual honesty is unusual and is the project's most defensible long-term asset. `[direct]` `docs/theory.md:37-39`, `docs/verification.md:8-18` `@4adf204`.

## Findings

### F1 — The artifact is not publicly adoptable; the README's own claims are unverifiable
- **Severity:** critical
- **Evidence label:** `[direct]`
- **Observation:** The repository at both documented names returns HTTP 404 (public and authenticated-as-owner API); it is absent from the owner's 10 public repositories; all four PyPI project names (`brief-spec`, `brief-spec-renderer-pdf`, `brief-spec-renderer-audio`, `briefspec`) return 404. Yet `README.md:14` carries a "Public release 0.2.0" badge linking to `github.com/luanmorenommaciel/brief-spec/releases/tag/v0.2.0`, and `README.md:35` instructs `uv tool install git+https://github.com/luanmorenommaciel/briefspec.git@v0.2.0`.
- **Why it matters:** The adoption barrier is effectively infinite: no third party can install, run, or independently verify Brief-Spec today. Worse, the project's flagship invariant — *"a local commit does not prove publication"* (`README.md:461`) and *"planned work is not completed work"* — is contradicted by its own README badge. A trust-boundary product that mislabels its own publication state undermines the one thing it sells.
- **Recommended response:** Make the repository public under a single canonical name; publish a real `0.x` to PyPI and GitHub Releases; replace the "Public release 0.2.0" badge with one that resolves, or mark it "unpublished" until it does.
- **What would verify the recommendation:** A clean-room `pip install brief-spec==0.x` succeeds and `brief-spec --version` reports the published version from a network with no prior cache.

### F2 — Hosted CI is blocked; "verified" maturity rests on a single author's local machine
- **Severity:** critical
- **Evidence label:** `[direct]` / `[reported]`
- **Observation:** `docs/verification.md:16,20-24` states hosted CI for 0.5.0 is "Blocked by account billing/spending limit" and cites a rejected Actions run (31516322113) as "not test evidence." The CI workflow file (`.github/workflows/ci.yml@4adf204`) is comprehensive — a 3-OS × 4-Python matrix, plugin-host validators, Chromium/PDF and macOS/audio e2e, clean-room wheel/sdist installs — but has not executed for 0.5.0.
- **Why it matters:** All current "passed" claims (414 tests, byte-identical determinism, F1 gates) are author-local on macOS/Python 3.13. Without hosted CI, cross-platform regressions are invisible and external trust has no foundation. The release is explicitly gated on this (`verification.md:20`: no tag/release/PyPI while CI is blocked).
- **Recommended response:** Restore GitHub Actions billing; run the full matrix on the exact candidate revision; make a green hosted-CI run a hard gate before any tag.
- **What would verify the recommendation:** A publicly visible, green Actions run on `main` covering ubuntu/macos/windows × 3.11–3.14, plus the release/clean-room jobs.

### F3 — Identity split: two names, broken links, an unfinalized rename
- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** The git remote is `briefspec` (no hyphen); `README.md`, `CHANGELOG.md`, and `pyproject.toml` URLs use `brief-spec` (hyphen); `docs/verification.md:124` lists "Rename the GitHub repository to `brief-spec`" as an *open* prerequisite. The CHANGELOG compare links (`CHANGELOG.md:122-128`) point at `/brief-spec/compare/...`, which 404. The distribution name, CLI, and import are `brief-spec`/`brief_spec`, while the implementation package, legacy markers, schemas, and state dir remain `briefspec`.
- **Why it matters:** Two names across remote, docs, and packaging is a discovery and trust tax. Broken CHANGELOG links and a 404 install command are the first thing a prospective adopter hits. The legacy/canonical aliasing is *defensible as a compatibility design*, but the *external* naming must converge before publication.
- **Recommended response:** Finish the rename in one atomic move (repo, GitHub, PyPI projects, badges, all doc links); keep the `briefspec` CLI/import aliases as the compatibility surface only. State the migration cost explicitly: one rename, no contract break, aliases preserved through `0.x`.
- **What would verify the recommendation:** Every link in README/CHANGELOG resolves; `pip install brief-spec` and the legacy `briefspec` CLI both work from the published artifact.

### F4 — A crowded "agent handoff standard" field is forming without Brief-Spec
- **Severity:** high
- **Evidence label:** `[external]`
- **Observation:** Active, public efforts are converging on agent handoff/coordination contracts: the **Delegation Contract** (a working spec with a companion arXiv paper, arXiv:2606.17099, "Software Delegation Contracts: Measuring Reviewability in AI Coding-Agent Work") `[external]` https://www.delegationcontracts.org/ (reviewed 2026-05-12); **OpenACCP** (a Python multi-agent coordination protocol with ~20 JSON schemas: authority charters, handoffs, review reports, consume results) `[external]` https://github.com/0fuk/OpenACCP; **Relay** (a Go daemon with HMAC-SHA256-signed continuation contracts and breach detection) `[external]` https://dev.to/dbisina/building-a-signed-handoff-protocol-for-ai-coding-agents-37c6 (3w old); **Agent Handoff Protocol** `[external]` https://github.com/Lutren/agent-handoff-protocol; **Agent_Handoff** `[external]` https://github.com/artyomboyko/Agent_Handoff.
- **Why it matters:** Brief-Spec's differentiation — *presentation + verified-delivery + multi-modal reading (Orient/Teach/Spoken) + cumulative verification levels + cross-harness installers* — is real but **unclaimed in the discourse**. If a different standard accrues network effects first, Brief-Spec becomes a fifth, technically-superior-but-invisible option. The Delegation Contract already has academic legitimacy; OpenACCP already has a richer multi-agent schema surface.
- **Recommended response:** Publish a crisp positioning/comparison doc that names the neighbors and stakes Brief-Spec's distinct claim ("the presentation-and-verified-delivery layer, not the coordination/orchestration layer"), and show interop where it's cheap (a Brief-Spec delivery can carry a Delegation Contract as a `work_item`).
- **What would verify the recommendation:** A public comparison page; at least one example of Brief-Spec consuming/emitting a neighbor's artifact.

### F5 — The author's own flagship (`agentspec`) is adjacent and the relationship is undefined
- **Severity:** high
- **Evidence label:** `[external]` / `[derived]`
- **Observation:** The same owner ships `luanmorenommaciel/agentspec` — 233 stars, 115 forks, 38 issues, released `v3.5.0` on 2026-07-30 — a Claude Code plugin for spec-driven data engineering that itself contains a `spec-linter` (deterministic contract validation) and `spec-judge` (adversarial behavioral evaluation). `[external]` https://github.com/luanmorenommaciel/agentspec/releases/tag/v3.5.0. It is the author's demonstrated, adopted project.
- **Why it matters:** Brief-Spec competes for the same maintainer's attention and overlaps `agentspec`'s validation philosophy. Undefined, the two can cannibalize: `agentspec` could absorb Brief-Spec's Outcome Brief into its `build`/`ship` phases, or Brief-Spec could starve from neglect while `agentspec` grows. Strategically, the relationship must be a decision, not drift.
- **Recommended response:** Decide explicitly: integrate (Brief-Spec as `agentspec`'s terminal-handoff layer) or federate (keep separate, cross-link, share the validation vocabulary). State it in both READMEs.
- **What would verify the recommendation:** A documented decision + either a merged feature or a public cross-reference and shared contract reference.

### F6 — Classification is rule-based on a synthetic template corpus; F1 proves determinism, not generalization
- **Severity:** medium
- **Evidence label:** `[direct]`
- **Observation:** `src/briefspec/work_types.py@4adf204` classifies via compiled regex `_TYPE_RULES`/`_SUBJECT_RULES` with a 64 KiB bound, host-context precedence, and a `general` fallback. `tests/test_work_types.py:24-70` generates the "160-prompt corpus" from `_templates` (20 per type) and asserts macro/per-type F1 gates.
- **Why it matters:** The F1 gate is a *determinism/consistency* test against the classifier's own rules on templated data, not evidence that the eight types + fallback handle the ambiguity of *real, diverse* prompts well. A rule-based classifier's quality is bounded by how well the rules anticipate real phrasings — exactly what a synthetic corpus cannot show.
- **Recommended response:** Build a held-out evaluation on real-world prompts (sanitized, consented) with human gold labels; publish the dataset; report per-type precision/recall and the fallback rate. Keep the classifier deterministic and local — do not add a model.
- **What would verify the recommendation:** A public eval set + a confusion matrix showing acceptable fallback/precision on non-templated inputs.

### F7 — "Verified" maturity overclaims relative to live evidence
- **Severity:** medium
- **Evidence label:** `[direct]`
- **Observation:** `docs/compatibility.md:16-26` labels Codex/Claude/OMP/Grok/Kimi "Verified" and Copilot/Cursor/Goose "Experimental." Yet `compatibility.md:11-12` defines verified as "its own executable has loaded and exercised the installed integration," while the CI `plugin-hosts` job (`.github/workflows/ci.yml:47-76@4adf204`) validates plugin *metadata* and runs `codex plugin list` / `claude plugin validate` — it does **not** run an authenticated agent lifecycle that produces and validates a brief. Live evidence is four smoke passes + one Grok hold, author-reported.
- **Why it matters:** "Verified" is the project's most load-bearing trust word. Labeling five harnesses "Verified" when the evidence is structural install + metadata + author-local smokes overclaims the state and risks the exact "implemented ≠ live" error the project warns against.
- **Recommended response:** Split the label: "Install-verified" (CI clean-room) vs "Lifecycle-verified" (authenticated agent run in CI producing a validated brief). Promote a harness to "Lifecycle-verified" only after a CI lane runs a real agent.
- **What would verify the recommendation:** A CI lane that runs Codex and Claude agents on a disposable repo and asserts a valid brief + verified delivery, green on `main`.

### F8 — Documentation points ahead of publication (self-dogfooding gap)
- **Severity:** medium
- **Evidence label:** `[direct]`
- **Observation:** `README.md:13` badges "source candidate 0.5.0"; `docs/verification.md` is titled "v0.5.0 candidate verification record"; `README.md:30` tells users the "source candidate" is 0.5.0 in "this checkout." A third party arriving at the README is sent to a 404 repo and a candidate that is not installable.
- **Why it matters:** The README is the front door and it currently dead-ends. For a product whose value is *reducing re-entry cost*, its own front door has maximal re-entry cost.
- **Recommended response:** Until publication, make the README's *installable* path unambiguous (point to the published PyPI package once cut; until then, clearly mark the repo as unpublished and the candidate as source-only).
- **What would verify the recommendation:** A new reader can install Brief-Spec and run `doctor` within 5 minutes using only the README.

### F9 — Internal doc/repo-state drift
- **Severity:** low
- **Evidence label:** `[direct]`
- **Observation:** `docs/verification.md:13` calls the 0.5.0 candidate "This uncommitted working tree," but at the inspected commit the tree is **clean and committed** (`git status` empty; `pyproject.toml` version 0.5.0 at HEAD). The 0.3.0/0.4.0/0.5.0 work was squashed into few commits, the last being the large `4adf204`.
- **Why it matters:** A truth-boundary record that misstates committed-vs-uncommitted erodes the very discipline it documents. Small, but it's the kind of drift the project exists to prevent.
- **Recommended response:** Update `verification.md` to reflect that 0.5.0 is committed at the named revision but untagged/unpublished; keep the "no source revision claimed until the release workflow tags" caveat where it still applies.
- **What would verify the recommendation:** The verification record's "Current source candidate" row matches `git status`/`git describe` on the inspected revision.

### F10 — Optional breadth (PDF/audio, 8 harnesses) is unproven surface for a one-maintainer 0.x
- **Severity:** opportunity
- **Evidence label:** `[derived]`
- **Observation:** The project maintains 5 verified + 3 experimental harness adapters, 4 reading modes, and optional PDF (Playwright/Chromium/Poppler) + audio (macOS `say`/`ffmpeg` + OpenAI TTS) renderers — three packages, optional deps, and their own test surfaces — for a project with zero public users.
- **Why it matters:** Every additional harness/renderer is unverified-by-third-party surface and maintenance load. Spoken Brief + audio is distinctive, but no evidence shows anyone listens to briefs; the value/complexity ratio is unproven.
- **Recommended response:** Before 1.0, audit which projections *earn their keep*; consider gating PDF/audio clearly behind the optional packages (already done) and *not* investing further in them until a usage signal exists.
- **What would verify the recommendation:** A usage/telemetry-free signal (e.g., an opt-in adopter report) showing audio/PDF is actually consumed.

## Ten opportunities

1. **Publish the existence gate.** Make the repo public, finish the rename, cut a real `0.5.0` to PyPI + GitHub. Impact 5 · Leverage 5 · Confidence 5 · Effort M · Risk low · Horizon **next release**.
2. **Unblock and pass hosted CI as the authoritative gate.** Restore billing; green matrix on the exact revision. Impact 5 · Leverage 4 · Confidence 5 · Effort S · Risk low · Horizon **next release**.
3. **Reconcile identity end-to-end.** One canonical name externally; aliases as the compat surface. Impact 4 · Leverage 4 · Confidence 5 · Effort S · Risk low · Horizon **next release**.
4. **Prove classification on real, held-out prompts.** Public eval set + confusion matrix + fallback rate. Impact 4 · Leverage 4 · Confidence 3 · Effort M · Risk medium · Horizon **later 0.x**.
5. **Position + differentiate against the handoff-standard field.** Public comparison doc; cheap interop with Delegation Contract/OpenACCP. Impact 4 · Leverage 5 · Confidence 3 · Effort M · Risk medium · Horizon **later 0.x**.
6. **Secure ≥1 external third-party adopter.** Convert "standard" from claim to evidence. Impact 5 · Leverage 5 · Confidence 2 · Effort L · Risk medium · Horizon **later 0.x**.
7. **Add an authenticated live-lifecycle CI lane (Codex + Claude).** Real agent run → brief → validate → verify delivery; re-define "Verified." Impact 5 · Leverage 4 · Confidence 3 · Effort L · Risk medium · Horizon **later 0.x**.
8. **Make determinism independently re-verifiable.** Publish a tiny "install + verify a sample delivery" one-liner a stranger can run. Impact 3 · Leverage 4 · Confidence 4 · Effort S · Risk low · Horizon **next release**.
9. **Decide the `agentspec` relationship.** Integrate or federate; document in both READMEs. Impact 4 · Leverage 4 · Confidence 3 · Effort M · Risk medium · Horizon **later 0.x**.
10. **Audit the projection matrix before 1.0.** Decide which of 8 types × 4 modes × 6 formats earn their keep. Impact 3 · Leverage 3 · Confidence 3 · Effort M · Risk low · Horizon **1.0**.

## Three highest-conviction bets

### Bet 1 — Publish the existence gate (repo public + hosted CI green + real PyPI/GitHub 0.5.0)
- **Why it dominates:** Every other opportunity presupposes an adoptable artifact. Today there is none. This is the single move that converts the project from "excellent private engineering" to "a thing a stranger can use." It also forces the identity reconciliation (F3) and the CI gate (F2) as dependencies.
- **User problem addressed:** "I heard about Brief-Spec and want to try it" — currently impossible.
- **Measurable outcome:** A clean-machine `pip install brief-spec` succeeds; a public green CI run exists; `brief-spec doctor` runs for a third party.
- **Must be true before implementation:** GitHub billing is restorable; the repo can be made public; PyPI Trusted Publishers are registered (verification.md already lists this).

### Bet 2 — Prove cross-harness semantic equivalence with an authenticated live-lifecycle CI lane
- **Why it dominates:** The core thesis is "different agents in, one predictable handoff out." That equivalence is currently *asserted* (smoke tests) not *demonstrated in CI*. A CI lane running real Codex + Claude on the same task and asserting equivalent canonical objects (modulo `source.harness`/`source.model`) is the falsifiable proof of the thesis — and it directly upgrades the meaning of "Verified" (F7).
- **User problem addressed:** "Will two different harnesses really produce the same structured handoff?"
- **Measurable outcome:** Across N tasks, canonical objects are byte-equivalent modulo harness/model/source fields; the diff is published as CI evidence.
- **Must be true before implementation:** Authenticated CI secrets for ≥2 harnesses; disposable-repo fixtures (the project already has these patterns in `.briefspec/live-e2e`).

### Bet 3 — Stake and demonstrate the differentiation against the handoff-standard field, with one external adopter
- **Why it dominates:** Standards are won by network effects, not by quality alone. The field is forming now (F4); Brief-Spec's distinct niche (presentation + verified-delivery + multi-modal reading) is unclaimed. A positioning doc plus one real external consumer converts "another handoff format" into "the presentation/delivery layer that composes with the others."
- **User problem addressed:** "Why this and not Delegation Contract / OpenACCP?" — currently unanswerable from the repo.
- **Measurable outcome:** A public comparison page + ≥1 third-party repo that emits/consumes Brief-Spec deliveries and reports it.
- **Must be true before implementation:** The artifact is public and installable (Bet 1); the interop seam (a delivery carrying a foreign contract as a `work_item`) is cheap to define.

## One contrarian bet

**Cut the supported surface to exactly 2 harnesses + Markdown/JSON for 1.0, and stop adding breadth.**

- **Strongest argument for:** A one-maintainer, unpublished project cannot credibly support 8 harnesses and 6 output formats. Every unsupported-by-evidence adapter is risk and maintenance debt that dilutes the core. Focus plus external evidence beats coverage claims; "the standard for Codex + Claude handoffs, proven equivalent in CI, used by N teams" is a more credible 1.0 than "8-harness universal layer, mostly smoke-tested." The deepest foundations (determinism, validation, privacy) shine more brightly on a narrow, deeply-proven surface.
- **Strongest argument against:** The breadth *is* the pitch — "cross-harness" is in the product's first sentence. Narrowing abandons the differentiation and concedes the universal-standard ambition to OpenACCP/Delegation Contract, which are themselves breadth-first.
- **Evidence needed to decide:** Which 2 harnesses have the strongest *third-party* demand signal; whether any external adopter actually wants the broad multi-harness claim or would adopt a focused 2-harness standard faster. Absent that signal, focus is the lower-regret bet.

## What not to build

- **A second brain / knowledge graph / conversation ingestion.** Already explicitly rejected (`README.md:479-496`); keep it rejected. It would destroy the privacy story and the focus.
- **More harness adapters before any current one has a third-party adopter.** Breadth without adoption is liability.
- **A "Brief-Spec Hub"/registry/SaaS for sharing briefs.** Premature network-effects theater; introduces a trust/privacy boundary the project has deliberately avoided.
- **An ML/model-based classifier.** Determinism, local-only, and no-network are core properties (`work_types.py`, SKILL). A model classifier would regress all three for marginal accuracy.
- **Speculative audio/TTS quality tuning or more voices.** Speech is text-first; the value is unproven. Do not invest until a usage signal exists.
- **A formal W3C-PROV compliance/certification program before 1.0.** `theory.md:258` already disclaims full PROV compliance; a certification regime is over-engineering for the current stage.
- **Breaking `briefspec`↔`brief_spec` compatibility before 1.0.** The aliasing is a deliberate compat design; breaking it early trades a real migration cost for no strategic payoff.

## Proposed next-release steel thread

- **User scenario:** A third-party reviewer installs Brief-Spec from PyPI, runs it on Codex *and* Claude against the same bounded task, and confirms the two harnesses produce equivalent canonical deliveries — all without reading any other documentation.
- **Entry point:** `pip install brief-spec`, then `brief-spec setup codex,claude --scope project`.
- **Classification behavior:** `review + pull-request` → `review` profile, local rule-based, sticky, `general` fallback. No network.
- **Explanation behavior:** `review` profile sections (Scope, verdict, findings, risk, validation, recommendation) wrap the Outcome Brief.
- **Canonical data changes:** one `brief-spec-delivery/2.0` object per run; `source.harness` and `source.model` vary, all other fields equal → same `canonical_sha256` modulo `source`.
- **Download / delivery changes:** `export` Markdown/JSON/HTML, `bundle` ZIP, `deliver` receipt, `verify --level delivered` — all from the public PyPI package.
- **Harnesses involved:** Codex + Claude (authenticated, in CI).
- **Security and privacy boundary:** no transcript/credential persistence; 1 MiB hook-input bound; transcript tail 256 KiB; symlink refusal; receipt outside the ZIP; offline by default.
- **Automated tests:** existing suite + a new *cross-harness equivalence* test: same task → two deliveries → assert equal canonical object modulo `source.*`; plus a published-artifact `verify --level delivered` test.
- **Live acceptance test:** CI runs real Codex and Claude agents on a disposable repo (existing `.briefspec/live-e2e` pattern), each produces a brief, both validate, both verify-delivered, and the two canonical objects are equivalent.
- **Success metric:** byte-equivalent canonical objects across the two harnesses on ≥10 tasks; `pip install` works for a stranger; a public green CI run; the README's install command resolves.
- **Explicit exclusions:** PDF/audio, Grok/Kimi/Cursor/Goose/Copilot live lanes, the agentspec integration, and any schema change to the 1.0 contracts. (The rename *should* ship in this thread but is not the thread's proof.)

## Evaluation plan

- **Classification quality:** held-out real-prompt corpus (not templates), human gold labels; report macro-F1, per-type precision/recall, and the fallback-to-`general` rate. Gate: fallback rate below a stated threshold.
- **Explanation usefulness:** blind A/B (Brief-Spec handoff vs. freeform) on real sessions; measure time-to-identify status, required action, and proof; comprehension Q&A after reading.
- **Time to identify status, action, and proof:** median seconds from handoff open to correct identification of the three fields; compare against freeform baseline.
- **Evidence-open success rate:** on a clean machine with no repo access, fraction of `[direct]`/`resolved` proof locators that open without authentication.
- **Wrong-status rate:** audited sample; % where the brief's status over- or under-claims relative to ground truth (e.g., `DONE` on unverified work).
- **Cross-harness semantic equivalence:** same task across harnesses → same canonical object modulo `source.*`; report diff rate per field.
- **Download completion:** `pip install brief-spec` success + `verify --level delivered` pass on published artifacts from clean environments (multiple OS/Python).
- **Delivery verification success:** `verify --level delivered` pass rate on a sample of published deliveries.
- **Installation and rollback reliability:** install → doctor → uninstall cycle on clean user + project scopes; assert rollback restores prior bytes/modes exactly (the project already tests this — promote it to a published-artifact gate).
- **User trust:** ≥3 external adopters surveyed on self-reported reliance on Brief-Spec briefs for re-entry; qualitative trust statements.

## Roadmap recommendation

### Now (next release — the existence gate)
- Make the repository public; finish the rename to `brief-spec`; fix README/CHANGELOG links and the unverifiable "public release" badge (F1, F3, F8).
- Unblock and pass hosted CI on the exact revision; make green CI a hard gate (F2).
- Publish `0.5.0` to PyPI (core + optional renderers) and GitHub Releases via the existing staged workflow.
- Correct `verification.md` "uncommitted" language (F9).
- **Release gate:** public, installable, green CI, published artifacts.

### Next (later 0.x — prove the thesis)
- Authenticated live-lifecycle CI lane for Codex + Claude; prove cross-harness equivalence (Bet 2, F7).
- Real held-out classification eval + public dataset (F6).
- Positioning/comparison doc vs Delegation Contract / OpenACCP / Relay (F4).
- Secure ≥1 external adopter (Bet 3).
- Decide + document the `agentspec` relationship (F5).
- **Release gate:** demonstrated equivalence in CI; ≥1 external adopter.

### Later (1.0)
- Freeze the Outcome Brief / Session Checkpoint `1.0` and delivery `2.0` contracts; cross-harness equivalence as the 1.0 gate.
- Audit the projection matrix; keep what earns its keep (Opportunity 10).
- Optional: PDF/audio promoted from candidate only on a usage signal.
- **Release gate:** frozen contracts + equivalence evidence + ≥3 adopters.

### Reject or defer
- New harness adapters before adopters exist.
- ML classifier; second-brain/ingestion; hub/registry/SaaS; PROV certification; breaking alias compatibility.
- Audio/TTS polish until a usage signal exists.

**Dependencies:** Now-gates unblock everything. "Next" depends on a public artifact (Now). 1.0 depends on equivalence evidence (Next). Classification eval (F6) and positioning (F4) can run in parallel with the live-lifecycle lane.

## Risks and failure modes

- **Technical:** Grok Build's native read/list instability (verification.md:88) blocks the full matrix; determinism could regress under non-deterministic host payloads (mitigated by canonical hashing, but untested across all 8 hosts in CI); the PDF path imports a Chromium/Poppler supply chain; the audio path depends on `ffmpeg`/OpenAI availability.
- **Product:** Value (re-entry-cost reduction) is a design hypothesis, not a measured outcome (`theory.md:37-39`); breadth may dilute depth; the spoken/audio mode may be speculative surface with no users.
- **Security and privacy:** Hooks are explicitly "a UX enforcement mechanism, not a security boundary" (`architecture.md:78`); malformed/oversized payloads are bounded but host-specific; evidence locators could theoretically leak private URLs (mitigated by private-URL/offline handling, `delivery.md:55-56`); transcript reading is bounded but exists.
- **Ecosystem:** 4+ overlapping standards (F4) with no network effects for Brief-Spec; host lifecycle APIs drift (e.g., Grok 1.0.x ignoring passive-hook stdout, `compatibility.md:30-33`).
- **Maintenance:** One maintainer across 3 packages, 8 harnesses, optional renderers, and a broad test matrix — a bus-factor/burnout risk; the sibling `agentspec` (233★) competes for the same attention.
- **Adoption:** Not installable today; zero public users; the front-door README dead-ends (F1, F8).
- **Supply-chain:** Hosted CI blocked by billing; PyPI Trusted Publishing not yet registered (verification.md:126-128); Twine-accepted artifacts are unpublished; no SLSA/provenance beyond the GitHub `attestations` step in `release.yml`.

## Open questions

1. Was `v0.2.0` ever actually public, or is the "Public release" badge aspirational/stale? (Repo is 404 now.)
2. Is there a genuine third-party demand signal, or is this single-author dogfooding?
3. Which 2 harnesses have the strongest external pull (decides the contrarian bet)?
4. Does the cognitive-load / re-entry-cost hypothesis hold in a measured human study, or only as design intuition (`theory.md`)?
5. Does anyone actually consume the Spoken Brief / audio output, or is it speculative surface?
6. Will `agentspec` absorb Brief-Spec, compete, or federate — and is that a decision the maintainer has made?
7. Is the repo private (token-scope limitation) or genuinely absent under both names on GitHub?

## Evidence ledger

| # | Evidence label | Repository locator / external source | Observation date | What it proves | What it does not prove |
|---|---|---|---|---|---|
| E1 | `[direct]` | `curl https://github.com/luanmorenommaciel/briefspec` and `/brief-spec` → HTTP 404; GitHub API `repos/luanmorenommaciel/briefspec` → 404 authenticated-as-owner | 2026-08-13 | The repository is not publicly resolvable and not visible to the owner's token | Does not distinguish private (token-scope-limited) from absent |
| E2 | `[direct]` | `https://api.github.com/users/luanmorenommaciel/repos` → 10 public repos, none named `briefspec`/`brief-spec` | 2026-08-13 | Not a public repository of the owner | Does not prove non-existence of a private repo |
| E3 | `[direct]` | `pyproject.toml:7` = `version = "0.5.0"` at `git HEAD 4adf204`; `git status` clean | 2026-08-13 | 0.5.0 is committed on `main`, untagged | Does not prove release or publication |
| E4 | `[direct]` | `pypi.org/pypi/{brief-spec,brief-spec-renderer-pdf,brief-spec-renderer-audio,briefspec}/json` → HTTP 404 | 2026-08-13 | No Brief-Spec package is published on PyPI | — |
| E5 | `[direct]` | `docs/verification.md:8-24` truth-boundary table; `:16,20-24` hosted-CI blocked; `:82-88` live-host smoke (4 pass, Grok hold) | 2026-08-13 | The author separates local/hosted/live/published; hosted CI blocked; live evidence is partial | The author's reported states; not independently reproduced |
| E6 | `[direct]` | `README.md:14,35` (public-release badge + `@v0.2.0` install); `:461` ("a local commit does not prove publication") | 2026-08-13 | README claims a public release and an install command that 404; contradicts its own invariant | Does not prove v0.2.0 was never public historically |
| E7 | `[direct]` | `src/briefspec/markdown.py@4adf204`; `tests/test_markdown_contracts.py@4adf204` | 2026-08-13 | Validator enforces field order, status vocabulary, list caps, cross-field invariants | Does not prove the contract is used correctly by real agents |
| E8 | `[direct]` | `src/briefspec/delivery.py:98-113`; `tests/test_delivery.py` (`test_bundle_is_deterministic…`, `test_bundle_rejects_hash_consistent_noncanonical_rendering`) `@4adf204` | 2026-08-13 | Deterministic canonical JSON + byte-identical bundles + forgery rejection | Does not prove determinism across all 8 hosts in CI |
| E9 | `[direct]` | `tests/test_state_and_hooks.py` (`test_prompt_content_is_not_persisted`); `tests/test_adapters.py` (`test_transcript_reader_refuses_symlinks`) `@4adf204` | 2026-08-13 | Privacy/bounded-state invariants are tested | Does not prove no future regression across host drift |
| E10 | `[direct]` | `docs/theory.md:37-39`; `docs/verification.md:13` ("uncommitted" vs clean HEAD) | 2026-08-13 | Theory is honestly labeled a hypothesis; verification doc has stale committed-state language | — |
| E11 | `[direct]` | `docs/compatibility.md:16-26` (verified/experimental labels); `:11-12` (verified definition); `.github/workflows/ci.yml:47-76` (metadata-only plugin-hosts) | 2026-08-13 | "Verified" labels exceed the CI evidence (structural install + metadata, not live agent run) | Does not prove the harnesses don't work live |
| E12 | `[reported]` | `docs/verification.md:38` ("414 tests at 86.86% branch coverage") | 2026-08-13 | Author's local gate claim | Not independently re-run; corroborated by test-file structure only |
| E13 | `[external]` | https://www.delegationcontracts.org/ (reviewed 2026-05-12); arXiv:2606.17099 | 2026-08-13 | A competing handoff contract exists with academic backing | Does not prove market dominance or Brief-Spec inferiority |
| E14 | `[external]` | https://github.com/0fuk/OpenACCP (20 schemas, multi-agent coordination) | 2026-08-13 | A breadth-first competing protocol exists | Does not prove adoption |
| E15 | `[external]` | https://github.com/luanmorenommaciel/agentspec/releases/tag/v3.5.0 (233★, 115 forks, 2026-07-30) | 2026-08-13 | The author has an adopted, released, adjacent project | Does not prove cannibalization will occur |
| E16 | `[direct]` | `tests/test_work_types.py:24-70` (template-generated 160-prompt corpus, F1 gate) `@4adf204` | 2026-08-13 | Classification is deterministic on templated data | Does not prove generalization to real prompts |

> Note on permalinks: because the repository is not publicly resolvable (E1, E2), GitHub permalinks would not resolve. Locators above refer to the **inspected local checkout at commit `4adf204`**; `<path>@4adf204` denotes that path at that commit.

## Final recommendation

**ADVANCE WITH CONDITIONS**

- **Rationale:** The contract design, determinism, validation, privacy, and truth-boundary discipline are genuinely strong and worth advancing — this is above-average engineering for the category. But none of it is adoptable today: the repo is not public, nothing is on PyPI, hosted CI is blocked, the identity is split, and the README's own "public release" claim is unverifiable. The conditions are non-negotiable gates, not nice-to-haves.
- **Single most important next action:** Make the repository public and publish `brief-spec 0.5.0` to PyPI and GitHub so a third party can actually install, run, and verify it (unblock hosted CI as part of the same move).
- **Single most important thing Brief-Spec should protect:** its honest **truth-boundary discipline** — the refusal to let local, hosted, live, and published states blur into each other. It is the project's most defensible, differentiating property, and the first place it must be applied is to its own README.
