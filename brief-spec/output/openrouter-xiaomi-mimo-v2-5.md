# Brief-Spec Independent Review — openrouter/xiaomi/mimo-v2.5

## Reviewer context

- **Provider and model:** openrouter/xiaomi/mimo-v2.5 (normalized: `openrouter-xiaomi-mimo-v2-5`)
- **Harness or interface:** Brief-Spec standalone session (no host harness; the review task was executed via super.engineering with the brief-spec skill active)
- **Date:** 2026-08-13
- **Repository URL:** https://github.com/luanmorenommaciel/briefspec
- **Branch and commit inspected:** `main` at `4adf204` ("New Brief-Spec Release")
- **Latest release observed:** `v0.2.0` (GitHub Release); source candidate `v0.5.0` present but not published
- **Materials available:** Local checkout at `/Users/luanmorenomaciel/GitHub/briefspec`, clean working tree, full source tree including `src/`, `tests/`, `schemas/`, `skills/`, `packages/`, `scripts/`, `docs/`, `.github/workflows/`, `.briefspec/` evidence directories, and `output/` review directory
- **Research providers used:** None. This review is based solely on repository inspection. No web search, no external documentation retrieval, no market research.
- **Important inspection limitations:** (1) No external user research or interviews were conducted. (2) No live-host testing was performed during this review. (3) No web search for competitor landscape or market demand was performed. (4) The GitHub API was not used to enumerate open issues or discussions; this review is limited to local inspection. (5) The reviewer is not the project author; some design decisions may reflect context available only to the author.

## Executive verdict

Brief-Spec is a genuinely original, rigorously designed project. It solves a real problem — the cognitive cost of re-entering agent sessions that lack a predictable handoff structure — with a well-grounded theory of change rooted in cognitive-load and interruption research. The evidence-contract model (direct/derived/reported, pass/fail/info) is the strongest conceptual contribution and the single feature most likely to become a cross-harness standard. The type-classification system with eight deterministic profiles is ambitious and well-tested.

However, the project carries meaningful risk. The published release is `v0.2.0` while the source candidate is `v0.5.0`, with a three-version gap of unpublished work. The installation surface is complex — multiple package names, dual import paths, legacy aliases, receipt-owned state, transactional multi-host setup — and this complexity is growing faster than the user base it serves. The harness adapter count (11 surfaces) outruns verified adoption. The verification document reveals that four of five core hosts pass, but Grok is unstable, CI is blocked by billing, and no PyPI publication has occurred.

The project's strongest direction is to harden the Outcome Brief and evidence contract as a publishable, cross-harness standard, rather than expanding the adapter matrix or the delivery envelope surface.

## What Brief-Spec has become

Brief-Spec is a **type-aware, evidence-backed handoff contract** for AI coding agents. Its core product is the insight that agent sessions end with a human who needs to answer three questions — what is now true, what requires me, and what proves the claim — and that a stable, ordered schema for these answers reduces the cognitive cost of re-entry across heterogeneous agent outputs.

The product has three layers:
1. **Three bounded Markdown contracts** — Outcome Brief, Session Checkpoint (Orient/Teach/Spoken), and the typed wrapper — that define the information structure.
2. **A deterministic type router** with eight work-type profiles that shape explanation order based on local classification.
3. **A verified delivery pipeline** — Markdown → JSON → HTML → ZIP → PDF/audio — with structural, resolved, rendered, and delivered verification levels.

The mental model is: "Same fields. Same order. Preserved evidence. Less mental reload."

## Strongest foundations to protect

### 1. The evidence-contract model (direct/derived/reported, pass/fail/info)

`[direct]` — `skills/outcome-brief/SKILL.md` lines 33-36; `schemas/brief-spec-delivery.schema.json` properties.evidence; `docs/theory.md` §7. This is the most original and generalizable property. It prevents summaries from silently upgrading claims, which is a failure mode every agent-human handoff suffers from.

### 2. Fixed field order as a cognitive contract

`[direct]` — `docs/theory.md` §1-4; `src/briefspec/markdown.py` validation; `src/briefspec/delivery.py` field labels. The validator enforces field order, not just presence. This is the project's strongest design discipline — it makes the position itself a retrieval cue.

### 3. One-repair-then-fail-open lifecycle policy

`[direct]` — `src/briefspec/hooks.py` `process_event`; `docs/architecture.md` "Repair guard"; `docs/theory.md` §9. The system requests at most one corrective pass, then allows an invalid stop. This prevents Brief-Spec from becoming an obstacle to the host it serves.

### 4. Deterministic, dependency-free core

`[direct]` — `pyproject.toml` dependencies=[]; `src/briefspec/` zero external imports; `docs/verification.md`. The core runs without network, without model calls, without optional renderers. This is critical for trust and auditability.

### 5. Honest truth-boundary documentation

`[direct]` — `docs/verification.md` entire document; README.md "Truth boundary" section. The project explicitly separates published from candidate, local from hosted, proven from claimed. This is unusually mature for a project at this stage.

## Findings

### Finding 1: The three-version publication gap creates confusion

- **Severity:** high
- **Evidence:** `[direct]`
- **Observation:** The public release is `v0.2.0`. The source candidate is `v0.5.0`. Versions `0.3.0` and `0.4.0` were folded into `0.5.0` and never published. The README badges show both versions. The verification document documents the `0.5.0` candidate but states publication is blocked by CI billing.
- **Why it matters:** Users who install from the tagged URL (`@v0.2.0`) get a version missing three major feature sets (typed delivery envelope, harness registry, type classification). Users who dogfood the candidate get unverified behavior. The gap makes it impossible to know which version's behavior to trust, and it undermines the project's own truth-boundary discipline.
- **Recommended response:** Publish `v0.5.0` or publish a minimal `v0.3.0` that bridges the gap. The staged release workflow exists but CI billing blocks it. The highest-leverage fix is resolving the CI billing issue or establishing a manual release path.
- **Verification:** The PyPI page shows only `v0.2.0`. The GitHub releases page shows `v0.2.0` as the latest. The `verification.md` confirms "No published 0.5.0 artifacts."

### Finding 2: Harness adapter count outruns verified adoption

- **Severity:** high
- **Evidence:** `[direct]`
- **Observation:** The harness table lists 11 surfaces (Codex, Claude, OMP, Grok, Kimi, Copilot CLI, Cursor Agent, Goose, VS Code Copilot, Copilot cloud, GitHub.com Chat). Five are "verified" but Grok's live gate is unstable. Four are "experimental." GitHub.com Chat has no integration.
- **Why it matters:** Each adapter surface adds installation code, test coverage, documentation, and user expectation. The installation surface (`src/briefspec/installers.py` at 38.6KB) is already the largest module. Adding more adapters before stabilizing the core contract and publishing the current candidate dilutes focus.
- **Recommended response:** Freeze the adapter count until `v0.5.0` is published and the five core adapters have stable live-host evidence. Mark experimental adapters as "community-contributed" with explicit maintenance expectations.
- **Verification:** Each adapter's live-host smoke evidence would be visible in `.briefspec/live-e2e/` after a successful run. Currently Grok is unstable, and Cursor/Copilot/Goose have no authenticated live evidence.

### Finding 3: The installation surface is complex and growing

- **Severity:** high
- **Evidence:** `[direct]`
- **Observation:** Installation involves: two CLI names (`brief-spec` + `briefspec`), two import paths (`brief_spec` + `briefspec`), two state directories (`brief-spec` + `briefspec` legacy), two receipt directories, two hook entry points, two schema prefix families, multiple scope models (user/project/auto), transactional multi-host setup, legacy alias compatibility, native plugin installation as alternative, and a receipt-owned rollback system. The `installers.py` module is 38.6KB.
- **Why it matters:** This complexity is the primary adoption barrier. A new user must understand scope, receipts, legacy aliases, and per-harness installation targets before seeing any value. The complexity exists because of a naming migration (`briefspec` → `brief-spec`) that is still in progress.
- **Recommended response:** Publish `v0.5.0`, then begin deprecation warnings for legacy interfaces. Consolidate to one state directory, one CLI name, and one import path. The receipt system is sound but the dual-namespace doubles the surface area.
- **Verification:** A new-user installation test from a clean Python environment, timed from clone to first validated Outcome Brief.

### Finding 4: The theory document is strong but the empirical validation gap is not closed

- **Severity:** medium
- **Evidence:** `[direct]`
- **Observation:** `docs/theory.md` is a well-researched 438-line document citing Sweller, Cowan, Monk, Bailey, Czerwinski, W3C accessibility guidance, and PROV. It explicitly states: "This is a design hypothesis informed by cognitive science and usability research. It is not a claim that the complete Brief-Spec interaction has already been validated in a controlled human-subject study." The proof claims in Outcome Briefs are structural, not behavioral.
- **Why it matters:** The theory is the project's intellectual foundation, but the gap between "informed by research" and "validated in context" matters for credibility when promoting Brief-Spec as a standard. Competitors or evaluators will note this.
- **Recommended response:** Add a lightweight behavioral evaluation: time-to-identify-status, time-to-identify-next-action, and comprehension accuracy for Brief-Spec output vs. raw agent output, with 10-20 participants. This does not require a formal IRB.
- **Verification:** A published evaluation report with methodology, sample size, and effect sizes.

### Finding 5: The typed wrapper adds cognitive cost without proven benefit

- **Severity:** medium
- **Evidence:** `[direct]`
- **Observation:** The `<!-- brief-spec:typed:v1 type={work_type} subject={subject} confidence={confidence} origin={origin} classified_at={classified_at} profile=1.0 -->` wrapper adds metadata around the Outcome Brief. The eight work-type profiles change explanation section order. The classifier uses regex patterns and local rules, not a model.
- **Why it matters:** The wrapper is valuable for machine parsing and provenance. But the value of type-specific explanation profiles (changing section order based on work type) has not been measured. A "review" profile places "Scope" first while a "general" profile places "Answer" first. Whether this changes user comprehension or trust is unknown.
- **Recommended response:** Treat type profiles as an experiment, not a contract. Keep the wrapper for provenance. Measure whether type-specific ordering changes comprehension before stabilizing the profile system as `1.0`.
- **Verification:** A controlled comparison of the same Outcome Brief rendered with matched vs. mismatched type profiles.

### Finding 6: The delivery envelope schema is ambitious but under-adopted

- **Severity:** medium
- **Evidence:** `[direct]`
- **Observation:** `brief-spec-delivery/2.0` adds `classification`, `explanation.sections`, `provenance`, `artifacts`, and `work_items` to the core brief. The schema is 5.7KB. The `explanation.sections` array with ordered content blocks is a significant expansion of the original Outcome Brief's flat fields.
- **Why it matters:** The delivery envelope is the machine-readable surface. Its adoption depends on consumers — CI pipelines, dashboards, or downstream agents. Without a published version or documented consumers, the schema is an aspiration.
- **Recommended response:** Publish the `2.0` schema as a standalone artifact. Document exactly one consumer (e.g., `brief-spec verify` in CI) with a concrete integration example.
- **Verification:** A CI workflow that validates a `brief-spec-delivery/2.0` object and produces a pass/fail status.

### Finding 7: Verification is thorough but the live-host evidence pipeline is fragile

- **Severity:** medium
- **Evidence:** `[direct]`
- **Observation:** The verification document is 120+ lines covering structural, resolved, rendered, and delivered levels. Local tests pass at 86.86% branch coverage across 414 tests. However, the hosted CI is blocked by billing, live-host evidence is in `.briefspec/` (gitignored), and Grok's live gate is unstable due to `read_file`/`list_dir` output errors and resident-session hangs.
- **Why it matters:** The verification story is the project's strongest operational claim. If it depends on local evidence that cannot be reproduced in CI, the claim weakens.
- **Recommended response:** Establish a CI path (even if manual) that produces verifiable live-host evidence for the five core adapters. Document the Grok instability as a known limitation with a tracking mechanism.
- **Verification:** A CI run that produces a `verification-summary.md` with pass/fail for each adapter gate.

### Finding 8: The Copilot cloud bridge is an interesting but high-risk surface

- **Severity:** medium
- **Evidence:** `[direct]`
- **Observation:** Project-scoped Copilot installation builds a deterministic `briefspec.pyz` zipapp, writes instruction files, and creates hook configurations. The bridge is network-free and stdlib-only. The adapter handles both native Copilot fields and VS Code-compatible envelopes.
- **Why it matters:** The cloud agent surface is the most complex installation path. It requires checked-in files, a self-contained zipapp, and specific hook configuration. The complexity is justified only if Copilot cloud coding adoption is real and growing.
- **Recommended response:** Treat the Copilot cloud bridge as an experiment until authenticated live-host evidence is available. Do not expand its surface until the basic installation path for the five core adapters is stable.
- **Verification:** An authenticated Copilot cloud job that produces a valid Outcome Brief with delivery receipt.

### Finding 9: The project lacks a CHANGELOG entry for the current state

- **Severity:** low
- **Evidence:** `[direct]`
- **Observation:** `CHANGELOG.md` has `[Unreleased]` as an empty section, then `[0.5.0] - Unreleased candidate`. The `0.5.0` entry is comprehensive but the version is unreleased. The `0.2.1` entry documents fixes that were never published.
- **Why it matters:** Users cannot determine what changed between `v0.2.0` and the current source without reading the full CHANGELOG. The "Unreleased candidate" label is honest but makes the changelog harder to use.
- **Recommended response:** When `v0.5.0` is published, retroactively fill in the released date. Until then, the current approach is acceptable given the truth-boundary discipline.
- **Verification:** CHANGELOG entries with dates matching GitHub releases.

### Finding 10: No documented user or customer evidence

- **Severity:** medium
- **Evidence:** `[derived]`
- **Observation:** The project has extensive technical documentation but no user research, no case studies, no quotes, no usage metrics, no adoption data. The theory document cites academic research but not Brief-Spec-specific user feedback.
- **Why it matters:** The project is built on a strong hypothesis (stable schema → faster recognition → more attention for judgment). But the hypothesis has not been tested with actual users of Brief-Spec. This limits the project's ability to prioritize features and defend design choices.
- **Recommended response:** Conduct 5-10 structured user interviews with people who have used Brief-Spec in a real coding session. Measure time-to-identify-status and time-to-identify-next-action. Publish the results.
- **Verification:** A published user research report with methodology, sample, and findings.

## Ten opportunities

### 1. Publish v0.5.0 to PyPI
- User impact: 5, Strategic leverage: 5, Evidence confidence: 5, Effort: S, Risk: low, Horizon: next release
- The CI billing issue is the single blocker. A published v0.5.0 closes the version gap, enables pip-install adoption, and makes the typed delivery envelope machine-readable.

### 2. Consolidate the naming namespace
- User impact: 4, Strategic leverage: 4, Evidence confidence: 5, Effort: M, Risk: medium, Horizon: later 0.x
- After v0.5.0, begin deprecating `briefspec` CLI alias, `briefspec` import, `BRIEF_SPEC_HOME`, and legacy state directories. This reduces the installation surface by ~40%.

### 3. Add lightweight user behavioral evaluation
- User impact: 4, Strategic leverage: 4, Evidence confidence: 3, Effort: M, Risk: low, Horizon: next release
- Time-to-identify-status, time-to-identify-next-action, comprehension accuracy. 10-20 participants. Published methodology.

### 4. Freeze adapter count until core is published
- User impact: 3, Strategic leverage: 4, Evidence confidence: 4, Effort: S, Risk: low, Horizon: next release
- Stop adding experimental adapters. Focus on hardening the five core adapters and the delivery contract.

### 5. Publish the delivery schema as a standalone artifact
- User impact: 3, Strategic leverage: 4, Evidence confidence: 4, Effort: S, Risk: low, Horizon: next release
- Make `brief-spec-delivery.schema.json` independently installable and versionable. Document one concrete CI consumer.

### 6. Add a "quick start" path that skips installation complexity
- User impact: 4, Strategic leverage: 3, Evidence confidence: 4, Effort: M, Risk: low, Horizon: next release
- A single `brief-spec init` command that detects the current harness and installs the minimum viable integration.

### 7. Create a public adoption dashboard
- User impact: 3, Strategic leverage: 3, Evidence confidence: 3, Effort: S, Risk: low, Horizon: later 0.x
- PyPI downloads, GitHub stars, open issues, verified adapters. Transparent metrics build trust.

### 8. Develop a brief-spec-lint tool for CI
- User impact: 3, Strategic leverage: 4, Evidence confidence: 3, Effort: M, Risk: low, Horizon: later 0.x
- A standalone validator that CI pipelines can run on agent output to enforce the Outcome Brief contract.

### 9. Build a type-profile evaluation suite
- User impact: 3, Strategic leverage: 3, Evidence confidence: 2, Effort: L, Risk: medium, Horizon: later 0.x
- Test whether type-specific explanation ordering changes comprehension or trust. Inform whether the eight profiles are worth maintaining.

### 10. Explore a lightweight Rust/Go verification binary
- User impact: 2, Strategic leverage: 3, Evidence confidence: 2, Effort: XL, Risk: high, Horizon: post-1.0
- A compiled binary for `brief-spec verify` that could be distributed without Python. High leverage for non-Python ecosystems but significant maintenance cost.

## Three highest-conviction bets

### Bet 1: Publish v0.5.0 and close the version gap

This dominates because it is the single action that unblocks every downstream improvement. Without a published release, the typed delivery envelope, the type classification system, and the harness registry are invisible to the ecosystem. The user problem is "I cannot install the current Brief-Spec." The measurable outcome is `pip install brief-spec==0.5.0` succeeding and `brief-spec --version` returning `0.5.0`. What must be true: CI billing is resolved or a manual release path is established.

### Bet 2: Conduct lightweight user behavioral evaluation

This dominates because it provides the evidence needed to defend every design choice. Without user data, the eight type profiles, the field order, and the evidence-contract model remain hypotheses. The user problem is "I don't know if Brief-Spec actually helps." The measurable outcome is a published report with time-to-identify-status and time-to-identify-next-action measurements. What must be true: 10-20 participants who have used an AI coding agent are available.

### Bet 3: Consolidate the naming namespace

This dominates because it reduces the primary adoption barrier. The dual-namespace (`briefspec`/`brief-spec`) adds confusion at every touchpoint — CLI, import, state directory, receipts, schemas. The user problem is "Which version name do I use?" The measurable outcome is a single CLI name, a single import path, and a single state directory. What must be true: v0.5.0 is published and a deprecation timeline is established.

## One contrarian bet

### The type-classification system should be removed or drastically simplified

**The strongest argument for it:** Eight deterministic work-type profiles with type-specific explanation ordering is a novel feature that differentiates Brief-Spec from a simple Markdown template. It enables agents to shape their explanation to the task type, which could improve comprehension. The classifier is local, deterministic, and well-tested (160-prompt corpus, macro and per-type F1 gates).

**The strongest argument against it:** The type-classification system is the most complex feature with the least evidence of user value. It adds: a 15.7KB `work_types.py` module, eight profile definitions, a classifier with regex patterns, a `classify` CLI command, a typed wrapper in Markdown, schema fields for classification and explanation, and validation logic. But whether changing the explanation section order based on work type actually changes user comprehension or trust has never been tested. The classifier can also misclassify, introducing a failure mode that a simpler system would not have. A project at this stage should prove that its most complex feature matters before investing further in it.

**The evidence needed to decide:** A controlled comparison where the same Outcome Brief is rendered with matched vs. mismatched type profiles, measuring time-to-identify-status and comprehension accuracy.

## What not to build

1. **Do not add more adapter surfaces** until the five core adapters have stable live-host evidence and v0.5.0 is published. Each new adapter is a maintenance commitment.

2. **Do not build a "brief-spec runtime" or execution engine.** The project should remain a presentation contract and verification tool, not an agent orchestration layer.

3. **Do not add network-dependent features** to the core package. The dependency-free core is a critical trust property. Keep all network features in optional renderer packages.

4. **Do not build a "brief-spec dashboard" or web UI.** The CLI and Markdown contracts are the product. A dashboard adds maintenance burden without proving user value.

5. **Do not attempt PROV compliance.** The project's narrower evidence model (direct/derived/reported) is more practical and easier to audit than the full W3C PROV family.

6. **Do not add a plugin registry or marketplace.** The native plugin installation paths (Codex, Claude, Copilot) are sufficient. A separate marketplace adds infrastructure without clear user demand.

7. **Do not build "brief-spec for non-coding agents."** The project's value is specific to coding harnesses with lifecycle hooks. Extending to general-purpose agents dilutes the focus.

## Proposed next-release steel thread

### User scenario

A developer using Codex finishes a code-review task. The brief-spec hook fires, classifies the task as `review + pull-request`, and injects the review explanation profile as session context. At the agent-stop boundary, the hook requests an Outcome Brief. The agent produces a valid brief. The hook validates it and returns an empty decision (allow). The developer reads the Outcome Brief in the terminal and can immediately identify the verdict, findings, and next action.

### Entry point

`brief-spec setup codex --scope user` installs the hook. The hook fires on `agent_stop` events.

### Classification behavior

The classifier runs on the bounded task text (first 64KB). It detects `review` from the user's explicit request and `pull-request` from the subject. Confidence is `high`, origin is `explicit`.

### Explanation behavior

The `review` profile is loaded. The explanation sections are: Scope, Verdict, Findings, Risk, Validation, Recommendation. The agent's explanation is shaped to this order.

### Canonical data changes

The `brief-spec-delivery/2.0` envelope is produced with `classification.work_type=review`, `classification.subject=pull-request`, `explanation.sections` matching the review profile, and `brief` containing the validated Outcome Brief.

### Download or delivery changes

No download changes. The existing Markdown, JSON, HTML, and ZIP exports work unchanged. The delivery envelope is the new canonical surface.

### Harnesses involved

Codex (primary). Claude Code and OMP (secondary, same flow).

### Security and privacy boundary

No network calls. No raw prompts or transcripts persisted. Session state is SHA-256 hashed. The delivery envelope contains only the bounded brief, classification, explanation, provenance, and artifacts.

### Automated tests

- Unit: classifier produces correct type for review+pull-request input.
- Unit: review profile sections are loaded in correct order.
- Unit: delivery envelope with review classification validates against schema.
- Integration: Codex hook fires on agent_stop, produces valid Outcome Brief.
- Integration: `brief-spec validate outcome` passes on the produced brief.

### Live acceptance test

Run the Codex smoke scenario from `scripts/run-live-e2e.py` with the `review + pull-request` task type. Verify: hook fires, classification is correct, Outcome Brief validates, delivery bundle is produced, receipt is written.

### Success metric

- The Codex live smoke produces a valid `brief-spec-delivery/2.0` envelope with correct classification and explanation sections.
- `brief-spec validate outcome` returns PASS.
- The delivery bundle contains Markdown, JSON, HTML, and ZIP exports.

### Explicit exclusions

- No new adapter surfaces.
- No network-dependent features.
- No type-profile behavioral evaluation (that is a separate workstream).
- No namespace consolidation (that is a separate workstream).

## Evaluation plan

### Classification quality
- Macro F1 ≥ 0.90 on the 160-prompt corpus (existing gate).
- Per-type F1 ≥ 0.85 for all eight types (existing gate).
- Misclassification rate < 5% on a held-out test set.

### Explanation usefulness
- Time-to-identify-status: ≤ 5 seconds for 90% of Outcome Briefs.
- Time-to-identify-next-action: ≤ 10 seconds for 90% of Outcome Briefs.
- Comprehension accuracy: ≥ 90% on a 5-question quiz about the brief content.

### Time to identify status, action, and proof
- Measured via timed user study with 10-20 participants.
- Compared against raw agent output (no Brief-Spec) as baseline.

### Evidence-open success rate
- ≥ 95% of Outcome Briefs contain at least one evidence reference with a valid locator.

### Wrong-status rate
- ≤ 2% of Outcome Briefs have a status that contradicts the evidence (e.g., DONE with unresolved gaps).

### Cross-harness semantic equivalence
- The same task run on Codex and Claude produces Outcome Briefs with the same status, outcome, and evidence basis (not identical text, but semantically equivalent).

### Download completion
- 100% of `brief-spec export` commands produce valid Markdown, JSON, and HTML.
- ZIP bundles are byte-deterministic for the same canonical input.

### Delivery verification success
- `brief-spec verify` returns PASS for all structural, resolved, and rendered checks on the standard test delivery.

### Installation and rollback reliability
- `brief-spec setup all` is idempotent across 3 consecutive runs.
- `brief-spec uninstall all` removes all receipt-owned files and leaves foreign files untouched.
- `brief-spec doctor --fix` repairs a deliberately corrupted installation.

### User trust
- Measured via a 5-point Likert scale: "I trust the Outcome Brief to accurately represent the agent's work."
- Target: mean ≥ 4.0 across 10-20 participants.

## Roadmap recommendation

### Now
- Resolve CI billing and publish v0.5.0 to PyPI. (Dependency: CI billing resolution)
- Conduct lightweight user behavioral evaluation. (Dependency: 10-20 participants)
- Add `brief-spec validate` CI workflow example to documentation.

### Next
- Begin deprecation warnings for legacy `briefspec` interfaces.
- Publish the delivery schema as a standalone artifact.
- Add a `brief-spec init` quick-start command.
- Create a public adoption dashboard.

### Later
- Consolidate to single CLI name, import path, and state directory.
- Develop `brief-spec-lint` for CI pipelines.
- Build type-profile evaluation suite.
- Explore compiled verification binary (Rust/Go).

### Reject or defer
- More adapter surfaces until core is published.
- Brief-spec runtime or orchestration engine.
- Network-dependent features in the core.
- Web dashboard or UI.
- PROV compliance.
- Plugin marketplace.
- Non-coding agent support.

## Risks and failure modes

### Technical risks
- **CI billing block persists** → v0.5.0 remains unpublished → adoption stalls → the project remains a local experiment.
- **Grok instability** → live-host evidence remains incomplete → the "verified" claim weakens.
- **Type classifier misclassification** → wrong explanation profile → user confusion → trust erosion.

### Product risks
- **No user evidence** → design choices remain unvalidated → the project builds features users don't need.
- **Installation complexity** → users try Brief-Spec and abandon it → adoption never reaches critical mass.
- **Feature creep** → the delivery envelope grows too complex → the core value (stable handoff schema) is buried.

### Security and privacy risks
- **Session state leakage** → raw prompts or transcripts persist → privacy violation.
- **Supply chain attack** → compromised PyPI package → malicious hook execution.
- **Path traversal in evidence resolution** → files outside workspace are accessed.

### Ecosystem risks
- **Host API changes** → adapters break → users lose functionality silently.
- **Competing standards** → a host platform ships its own handoff contract → Brief-Spec becomes redundant.
- **Model provider lock-in** → Brief-Spec's value depends on specific model behaviors that change.

### Maintenance risks
- **Adapter maintenance burden** → each new adapter requires ongoing testing and documentation → resources are spread thin.
- **Schema versioning** → the 2.0 envelope is incompatible with 1.0 consumers → migration cost.
- **Legacy compatibility** → the dual-namespace requires ongoing maintenance → the codebase grows.

### Adoption risks
- **No PyPI publication** → users cannot `pip install` → adoption is limited to source checkouts.
- **No documentation in host ecosystems** → users don't discover Brief-Spec → adoption is organic and slow.
- **No community** → no contributors, no plugins, no ecosystem → the project is a solo effort.

### Supply-chain risks
- **Python ecosystem changes** → hatchling build system may need updates.
- **Dependency on Playwright for PDF** → optional renderer depends on a large binary.
- **Dependency on ffmpeg for audio** → optional renderer depends on a system binary.

## Open questions

1. Does changing explanation section order based on work type actually change user comprehension or trust?
2. What is the minimum viable installation path that would cause a new user to adopt Brief-Spec?
3. Is the Outcome Brief schema stable enough to freeze at 1.0, or does it need more iteration?
4. Should the delivery envelope 2.0 be published as a standalone artifact before or after v0.5.0?
5. How many users are actually running Brief-Spec in a real coding session?
6. Is the evidence-contract model (direct/derived/reported) understood by non-expert users?
7. Should the project target a specific host (e.g., Claude Code) as the primary adoption path?
8. What is the cost of maintaining 11 adapter surfaces vs. the benefit of broad compatibility?
9. Should the typed wrapper be optional (user opt-in) rather than automatic?
10. Is the one-repair-then-fail-open policy the right tradeoff between helpfulness and non-obstruction?

## Evidence ledger

| Claim | Evidence label | Repository locator | Observation date | What it proves | What it does not prove |
|---|---|---|---|---|---|
| Public release is v0.2.0 | [direct] | README.md badges; GitHub releases | 2026-08-13 | Users installing from the tagged URL get v0.2.0 | Whether v0.2.0 is functional for modern harnesses |
| Source candidate is v0.5.0 | [direct] | pyproject.toml version; CHANGELOG.md | 2026-08-13 | The working tree contains v0.5.0 code | Whether v0.5.0 passes all live-host gates |
| CI is blocked by billing | [direct] | docs/verification.md "External prerequisites" | 2026-08-13 | Hosted CI cannot run | The specific billing issue or resolution timeline |
| 414 tests pass at 86.86% branch coverage | [direct] | docs/verification.md "Direct local evidence" | 2026-08-12 | The test suite covers the codebase adequately | Whether the tests cover real-world usage |
| Five core adapters verified | [direct] | docs/compatibility.md; docs/verification.md live-e2e table | 2026-08-12 | Codex, Claude, OMP, Kimi pass smoke; Grok is unstable | Whether the adapters work with current host versions |
| Grok live gate is unstable | [direct] | docs/verification.md live-e2e table | 2026-08-12 | read_file/list_dir output errors and resident-session hangs | The root cause or fix timeline |
| Zero runtime dependencies | [direct] | pyproject.toml dependencies=[] | 2026-08-13 | The core package has no external Python dependencies | Whether optional renderers have appropriate dependencies |
| Theory cites cognitive science | [direct] | docs/theory.md references | 2026-08-13 | The design is informed by published research | Whether the design is validated in context |
| 160-prompt corpus meets F1 gates | [direct] | docs/verification.md; tests/test_work_types.py | 2026-08-12 | The classifier performs adequately on the test corpus | Whether the corpus represents real usage |
| Installation surface is complex | [derived] | src/briefspec/installers.py (38.6KB); dual CLI names | 2026-08-13 | The installation code is large and multi-faceted | Whether users find it confusing (no user data) |

## Final recommendation

**ADVANCE WITH CONDITIONS**

Brief-Spec has strong foundations — the evidence-contract model, the fixed field order, the deterministic core, and the honest truth-boundary documentation are genuinely valuable. The project has earned the right to publish.

**Rationale:** The codebase is well-structured, the test suite is thorough, and the design theory is sound. The primary blocker is not technical — it is the CI billing issue that prevents v0.5.0 from being published. The secondary blocker is the absence of user evidence to validate the design hypotheses.

**The single most important next action:** Publish v0.5.0 to PyPI. This unblocks every downstream improvement and makes the typed delivery envelope machine-readable for the first time.

**The single most important thing Brief-Spec should protect:** The evidence-contract model (direct/derived/reported, pass/fail/info). This is the project's most original and generalizable contribution. It prevents summaries from silently upgrading claims, which is a failure mode every agent-human handoff suffers from. Protect it from feature creep, namespace confusion, and scope expansion.
