# Brief-Spec Independent Review — deepseek-deepseek-v4-pro

## Reviewer context

- **Provider and model:** `deepseek/deepseek-v4-pro` (runtime metadata; normalized slug `deepseek-deepseek-v4-pro`). Harness: Oh My Pi (OMP).
- **Date:** 2026-08-13 (retrieval 2026-08-13T14:18Z).
- **Repository URL:** https://github.com/luanmorenommaciel/briefspec (canonical, no hyphen). Note: package metadata and several manifests point at `github.com/luanmorenommaciel/brief-spec` (hyphenated), which does not exist.
- **Branch and commit inspected:** `main` @ `4adf20412028aa858a982c2149c3622327efa11a` ("New Brief-Spec Release", 2026-08-13 11:05:31 -0300). Local checkout equals `origin/main`; working tree clean. `git status --porcelain` returned only the branch header.
- **Latest release observed:** GitHub release `v0.2.0` (2026-07-31). Tags: `v0.1.0`, `v0.2.0` only. PyPI: nothing published under `brief-spec` (HTTP 404 confirmed directly). The checked-out `0.5.0` is a candidate; publication is gated.
- **Materials available:** full source checkout (130 tracked files, ~10.5k lines across src/tests/renderers), README, CHANGELOG, all 8 docs, skills, 9 JSON schemas, 3 plugin manifests, 2 workflows, tests, scripts, pilots, integration assets, gitignored local release/live-e2e artifacts (directory names only), GitHub state via authenticated `gh` (repo metadata, releases, issues, PRs, CI run list).
- **Research providers used:** none (no Exa/Tavily/Firecrawl/web search performed; no market claims made in this review). GitHub state checked via `gh` CLI and `git ls-remote`.
- **Inspection limitations:** the repository is **private**; unauthenticated GitHub web/API access 404s, so issues/discussions content was unavailable beyond `gh issue list` (zero issues exist). Live-host smoke evidence was inspected as sanitized artifacts and the author's verification record, not re-executed. I ran the project test suite, classifier probes, and a determinism experiment myself; I did not run any live harness gate.
- **Independent verification performed:** `pytest` (413 passed / 1 failed — machine-state-dependent failure, see Finding 4); deterministic export/bundle byte-identity; live classifier probes on three task texts; `gh run list` for CI status; PyPI and DNS existence checks.

## Executive verdict

Brief-Spec is the most epistemically disciplined presentation layer for AI-coding-agent handoffs I have inspected: five honest terminal statuses with validator-enforced semantics, evidence basis labels, fail-open hooks with a one-repair guard, bounded non-transcript state, and a deterministic single-source delivery pipeline (Markdown/JSON/HTML/ZIP + external receipt) that I independently confirmed byte-identical across runs. The engineering quality is exceptional for a 13-day-old project, and the "truth boundary" culture is the product's real moat.

But the product currently has no users and no evidence that its core hypothesis—stable schemas reduce re-entry cost—holds for real humans. The repository is private, has zero issues and zero stars, the only pilot results template is empty, and the one live host that matters most for launch (Grok Build) is unstable. Publication is blocked on hosted CI billing and on that host, while package metadata points at a GitHub repository name that does not exist and a schema `$id` domain with no DNS. The test suite's headline "414 passed" is machine-state-dependent; on this machine it is 413.

Verdict: **ADVANCE WITH CONDITIONS**. Protect the honesty and determinism culture. Publish 0.5.0 only after canonicalizing URLs, making the doctor tests hermetic, restoring CI, and decoupling the Grok gate; then run a measured human re-entry study before investing in anything further.

## What Brief-Spec has become

Brief-Spec is a **portable presentation contract for agent-to-human handoffs**. It standardizes the *shape* of the last mile—not the agent's reasoning. Three skills define three contracts: a local deterministic router that classifies a task into one of eight work types and selects a fixed explanation profile (Answer/Rationale/Next for general; Scope/Verdict/Findings/Risk for review; etc.); a terminal Outcome Brief (Status → Outcome → Human action → Proof → Gaps → Next → Open, with status semantics enforced by a validator); and a Session Checkpoint with three renderings of the same bounded state (orient, teach, spoken). A dependency-free Python control plane turns these into one canonical `brief-spec-delivery/2.0` object and deterministically projects it into Markdown, JSON, self-contained offline HTML, ZIP bundles with manifests, plus optional PDF and MP3 renderers—all verifiable at four cumulative levels (structural → resolved → rendered → delivered) against an external receipt. Installers put skills and a stdlib-only zipapp into Codex, Claude Code, OMP, Grok Build, Kimi Code (verified) and Copilot/Cursor/Goose (experimental), with transactional rollback, receipts, a doctor, and drift detection.

The mental model in one sentence: **different agents in, one predictable, evidence-preserving handoff out**—a lens, deliberately not a second brain, not a knowledge store, not an agent framework. Compress presentation, never provenance.

## Strongest foundations to protect

1. **Truth-boundary discipline.** Proposed / implemented / locally validated / live-host validated / hosted-CI validated / published are tracked as separate states in `docs/verification.md`; a passing syntax check is explicitly not live evidence; a local commit is explicitly not publication. Statuses (`DONE`, `REVIEW`, `DECIDE`, `BLOCKED`, `FAILED`) have validator-enforced semantics (e.g., `DONE` cannot carry required human action or unresolved gaps). [direct] `docs/verification.md#56D0`, `skills/outcome-brief/SKILL.md#F140`, `src/briefspec/markdown.py` (validators). This honesty culture is rarer than the code and is the moat; any feature that blurs it must be rejected.

2. **Deterministic single-source delivery.** One canonical object → all renderings; canonical time captured once; fixed ZIP timestamps/modes/ordering; receipts kept outside the ZIP so the hash attests to delivered bytes without self-reference. I independently confirmed: two `export` runs produced byte-identical directories and two `bundle` runs produced identical SHA-256 ZIPs; `structural` and `rendered` verification ran against the bundle. [direct] `src/briefspec/delivery.py`, `src/briefspec/bundle.py`, `docs/delivery.md#CAF4`, my local experiment (2026-08-13).

3. **Zero-runtime-dependency core with a deterministic zipapp.** The core package has `dependencies = []`; hooks make no network calls; the Copilot cloud bridge is a stdlib-only zipapp built with fixed 1980-01-01 timestamps and sorted entries, executable from a cloned repo without downloads. This makes installation and supply-chain trust trivial and is the right base for a cross-harness standard. [direct] `pyproject.toml#CFAA`, `src/briefspec/bundle.py:26-61`, `integrations/copilot/cloud/README.md#1834`.

4. **Honest capability matrix.** `docs/compatibility.md` and the README table distinguish Verified vs Experimental per harness, per capability (hooks, pre-compact, subagents, model metadata), and document non-claims explicitly (Goose: no lifecycle automation; Grok: passive hook stdout ignored by the host; Copilot cloud: ephemeral job-bound checkpoints). `brief-spec doctor --probe` validates the installed bundle with a synthetic event and does not claim an external service ran anything. This refusal to overclaim is exactly what will earn user trust in a space full of vaporware. [direct] `docs/compatibility.md#45DD`, README "Harness support" table, `src/briefspec/diagnostics.py`.

5. **Fail-open lifecycle control with bounded state.** Hooks bound input to 1 MiB, persist only counters/timestamps/event hashes (never prompts, transcripts, tool results), write atomically with 0600 permissions, hash session directories, quarantine corrupt state, attempt at most one repair per turn, and fail open on internal errors. Transcript tails are read at most 256 KiB and symlinks are refused. [direct] `docs/architecture.md#4654` (State and privacy), `src/briefspec/state.py`, `src/briefspec/hooks.py`, `src/briefspec/adapters/base.py`. A presentation layer that cannot brick your session is a design achievement; protect the fail-open invariant above all feature work.

## Findings

### Finding 1 — No evidence the core hypothesis is true for real users
- **Severity:** high.
- **Evidence label:** [direct] repository state; [derived] conclusion.
- **Observation:** Private repo, created 2026-07-31, 12 commits, 0 stars, 0 forks, 0 issues, all 6 PRs are Dependabot. `pilots/apex/README.md` poses five good questions (time-to-identify < 15 s, proof coverage, interruption cost, spoken comprehension, one-repair) but ships only a `results-template.json`; no recorded results anywhere. The 160-prompt classification corpus is template-generated inside the test file (20 templates × 8 types), not real prompts. `docs/theory.md` §12 correctly lists falsification conditions but nothing has measured them.
- **Why it matters:** Every other investment—more harnesses, renderers, schema 3.0—assumes the stable-schema → less-reload theory works on humans. If checkpoints feel like boilerplate and users skip the brief, the product is a tax. Zero user evidence means zero validated demand, and no current research supports claiming market interest ([unknown]).
- **Recommended response:** Make the next release a measurement vehicle: publish 0.5.0, recruit ≥5 engineers (friends-of-project is fine), run timed re-entry scenarios on real sessions, record the eight falsification metrics from `docs/theory.md` §12.
- **What would verify:** Mean time-to-identify status/action/proof ≤ 15 s in ≥80% of trials; wrong-status rate ~0 on a 20-session audit; annoyance/dismissal rate reported qualitatively.

### Finding 2 — Publication metadata points at resources that do not exist
- **Severity:** high.
- **Evidence label:** [direct] observed in repo; [direct] network checks.
- **Observation:** `pyproject.toml` `[project.urls]` (Homepage/Repository/Issues), `.codex-plugin/plugin.json` (homepage, repository, websiteURL), `plugin.json`, and the documented marketplace commands (`codex plugin marketplace add luanmorenommaciel/brief-spec --ref v0.5.0`, etc. in `docs/installation.md`) all reference `github.com/luanmorenommaciel/brief-spec` (hyphenated). That repository does not exist (GitHub API 404; the real repo is `briefspec`). The delivery schema `$id` is `https://brief-spec.dev/schemas/…` and `brief-spec.dev` has **no DNS records** (verified with `dig`). `docs/verification.md` lists "Rename the GitHub repository to brief-spec only after local and hosted gates pass" as an open prerequisite—so the rename is gated *behind* the same blocked CI that the rename is needed to unblock metadata for.
- **Why it matters:** On publication day, every plugin-marketplace install command fails. A canonical `$id` pointing at an unregistered domain breaks schema-tooling resolution expectations.
- **Recommended response:** Invert the dependency: rename the repo (or revert all URLs to the existing `briefspec` name) **before** publishing, independent of CI state; register or remove the `brief-spec.dev` domain decision explicitly.
- **What would verify:** `gh repo view luanmorenommaciel/brief-spec` succeeds after rename; marketplace add commands return success; schema `$id` resolves.

### Finding 3 — Release is gated on a third-party host's instability and a blocked CI account
- **Severity:** high.
- **Evidence label:** [direct] `gh run list`, `docs/verification.md`, gitignored artifact directory names.
- **Observation:** Main-branch CI has failed since 2026-08-11 (run 31516322113 cited in `docs/verification.md`; the release commit's own CI run 31708342030 failed in 7 s — jobs rejected before execution, consistent with the billing/spending-limit explanation). Dependabot-branch CI succeeded on 2026-08-10, so the blockage is recent. Grok Build's live gate is `Hold`: `.briefspec/live-e2e/` contains `0.5.0-smoke-grok-review-v2` through `-v13` — eleven retries of one scenario — and `docs/verification.md` documents host-side `read_file`/`list_dir` errors and hangs.
- **Why it matters:** The 0.5.0 candidate is frozen behind two external conditions the author cannot fix. Delay breeds rot: harness APIs drift weekly, and the excellent local evidence ages. There is no deadline; a frozen release is how disciplined projects die.
- **Recommended response:** Reclassify Grok Build to "experimental (documented hold)" for this release and make the release gate: CI green on the exact revision + 4/5 live host smokes (Codex, Claude, OMP, Kimi already pass) + deterministic gates. Re-attempt Grok per release, not as a release blocker.
- **What would verify:** 0.5.0 published with a compatibility matrix that honestly shows Grok as experimental; no silent re-promotion of Grok without a passing gate.

### Finding 4 — Test suite is not hermetic; headline "414 passed" is machine-state-dependent
- **Severity:** medium.
- **Evidence label:** [direct] my independent run; [direct] test source.
- **Observation:** I ran the suite on this machine: **413 passed, 1 failed**. The failure is `test_doctor_all_can_treat_an_unavailable_host_as_optional`, which expects a `WARN` because it assumes the Copilot CLI is absent—but `copilot` is now installed on this machine (I verified it on PATH), so the doctor correctly reports `FAIL` for a present-but-uninstalled host and the test's premise breaks. `docs/verification.md` claims "The current source passed 414 tests" and also still describes the candidate as "an uncommitted working tree" although 0.5.0 is committed at `4adf204`.
- **Why it matters:** A test that reads real executables from PATH will fail on any machine whose tool inventory changes—including the author's own, as observed. CI credibility and the release gate depend on deterministic results.
- **Recommended response:** Monkeypatch executable detection in that test (and audit `test_installers.py`/`test_harness_registry.py` for the same pattern); refresh `docs/verification.md` wording after the commit.
- **What would verify:** Suite passes identically with and without `copilot`/`goose`/`cursor` on PATH (simulated by PATH isolation).

### Finding 5 — Deterministic keyword classification is honest but fragile; observed failing on this very task
- **Severity:** medium.
- **Evidence label:** [direct] live probe.
- **Observation:** `classify_task` scores regex rule groups per type; ties fall back to `general` (low confidence). I fed the actual review task text: result `general / fallback / low`, subject `feature` (it matched "feature wishlist"). Rules for review, planning, and exploration each fired once → tie → fallback. The subject rules run independently of the type, so a fallback-typed task can still get a confidently wrong-feeling subject. A clean "Review this pull request…" phrase classifies `review/high` correctly; "Why is the test failing?" → `debugging/high` correctly.
- **Why it matters:** The classification is the product's front door: it decides the explanation order the user sees. Real human prompts rarely match the canonical phrasing of the synthetic corpus. A fallback to `general` is safe-by-design, but every fallback is a missed promise, and the observed subject mislabel erodes trust in the `classification` block that ships in the canonical delivery object.
- **Recommended response:** Keep deterministic/no-network as the default (do not silently introduce model calls). Add: (a) subject inference gated on non-fallback type; (b) a real-prompt labeled corpus (v1: 100+ prompts harvested from real sessions and PR reviews) replacing the template corpus as the quality gate; (c) report rule ties as an explicit `ambiguous` classification field rather than an opaque fallback.
- **What would verify:** Macro F1 and per-type F1 on the real-prompt corpus meet the current thresholds; zero subjects that contradict the resolved work type on that corpus.

### Finding 6 — Evidence locator grammar cannot resolve common citation forms
- **Severity:** medium.
- **Evidence label:** [direct] live experiment.
- **Observation:** My bundle used a proof locator of `tests/test_work_types.py::test_labelled_160_prompt_corpus_meets_release_thresholds` (pytest style). `verify --level rendered` reported `FAIL reference 1: file not found: tests/...`—the `::` form is not in the accepted grammar (`path:line[:column]`). The skills instruct agents to cite "inspectable locators" and pytest-style citations are the most natural form an agent produces after running a test.
- **Why it matters:** The evidence-open success rate (fraction of proof references that resolve) is one of the strongest verifiable claims the project makes. If the most natural locator form fails resolution, `resolved`/`rendered` verification will reject or weaken genuinely good briefs—or agents will learn to strip the test name, losing information.
- **Recommended response:** Extend the locator grammar: `path::test_id`, `path#fragment`, line ranges; downgrade unparseable-but-plausible forms to `WARN` with a fix hint instead of `FAIL`.
- **What would verify:** A locator-corpus test with ≥10 real citation forms resolving at `resolved` level; the original `::` form resolves.

### Finding 7 — Legacy dual-naming is a compounding compatibility tax with no sunset plan
- **Severity:** medium.
- **Evidence label:** [direct] repo structure.
- **Observation:** Two CLIs (`brief-spec`, `briefspec`), two import names (`brief_spec` forwards to `briefspec`), two state env vars, two renderer entry-point groups, legacy markers (`briefspec:outcome:v1` inside the new `brief-spec:typed:v1` wrapper), and 9 schema files including three duplicate pairs (`bundle-manifest` vs `brief-spec-bundle-manifest`, `delivery-receipt` vs `brief-spec-delivery-receipt`, `briefspec-delivery` vs `brief-spec-delivery`). All are "readable through 0.x" per CHANGELOG.
- **Why it matters:** Every future feature, test, and validator multiplies across both namespaces; the nested marker structure (typed wrapper around legacy brief) is the hardest part of the Markdown contract to hand-audit. The promised compatibility window has no end date, so the tax is perpetual until explicitly sunset.
- **Recommended response:** Declare now that `briefspec` legacy names are removed at 1.0 and remove nothing earlier; merge duplicate schema pairs by making one a `$ref`/alias of the other; add a `CHANGELOG` "Removed in 1.0" section.
- **What would verify:** `grep` shows exactly one canonical schema pair per concept; the 1.0 milestone text in the repo states the removal.

### Finding 8 — Multi-agent work items exist in the schema but have no enforced semantics or live evidence
- **Severity:** opportunity.
- **Evidence label:** [direct] schema and harness registry.
- **Observation:** `brief-spec-delivery/2.0` has `work_items` with `work_id`, states (`RUNNING`/`COMPLETED`/`FAILED`…), and roles; subagent events are wired only for Grok and Kimi (`_events_for_runtime`); the skill says "the main task owns the user-facing brief"—prose, not enforcement. No live gate exercised subagents.
- **Why it matters:** Multi-agent sessions are where re-entry pain is worst and where a presentation standard has the most leverage. Unenforced `work_items` risks becoming decorative JSON.
- **Recommended response:** Define the invariant (each completed subagent contributes a validated Outcome Brief as evidence; parent merges into `work_items`; `DONE` at parent level requires all children terminal) and enforce it in the validator.
- **What would verify:** Validator rejects a parent `DONE` with a `RUNNING` child; a two-agent live scenario passes on Codex (which supports subagents).

### Finding 9 — No product-level evaluation harness exists; verification is entirely technical
- **Severity:** opportunity.
- **Evidence label:** [direct].
- **Observation:** All evaluation so far verifies *the tool* (schemas, determinism, installers, renderers). Nothing measures *the user outcome* (comprehension time, resumption success, false confidence). The Apex pilot's question list is exactly right and entirely unexecuted.
- **Why it matters:** Technical verification cannot detect the project's primary failure mode: a well-formatted brief that people don't trust or don't read.
- **Recommended response:** Ship `scripts/run-pilot.py` output templates with the published release and a 10-minute recorded protocol; treat pilot results as a release artifact.
- **What would verify:** A checked-in (anonymized) results file from ≥3 sessions.

### Finding 10 — Single-operator bus factor and an elaborate, mostly manual release process
- **Severity:** low (risk note).
- **Evidence label:** [direct].
- **Observation:** One author; the release path involves ~25 KB `scripts/verify-release.py`, `snapshot-installation.py`, `build-release-manifest.py`, `check-pypi-artifacts.py`, `run-browser-e2e.py`, `run-live-e2e.py`, plus ~20 gitignored `.briefspec/` artifact directories. All impressive, all single-operator.
- **Why it matters:** The strongest asset is process discipline, and it is currently one person's tacit knowledge.
- **Recommended response:** Encode the publish checklist as a documented runbook (already mostly in `docs/verification.md`—promote to a numbered runbook); seek one second maintainer for the release path only.
- **What would verify:** A second person executes a release dry-run without author intervention.

## Ten opportunities

Scored: User impact / Strategic leverage / Evidence confidence (1–5), Effort (S/M/L/XL), Risk (low/medium/high), Horizon.

1. **Publish 0.5.0 through a corrected gate** (rename-or-revert URLs, hermetic tests, CI unblocked, PyPI trusted publishing, GitHub release finalization). 5 / 5 / 4 / M / low / **next release**. Unlocks every user-facing outcome; without it nothing else matters.
2. **Human-measured re-entry study** (timed status/action/proof identification, wrong-status audit, resumption success, annoyance) on real sessions. 5 / 5 / 2 / M / low / **next release**. Converts the core hypothesis from theory to evidence.
3. **Real-prompt classification corpus** replacing the synthetic 160-prompt template corpus as the F1 gate, plus a public per-type quality dashboard. 3 / 4 / 3 / S / low / **next release**.
4. **Evidence locator grammar 2.0** (`path::test`, `#fragment`, ranges; WARN-with-hint for near-misses). 4 / 2 / 5 / S / low / **next release**. Observed defect, immediate evidence-open-rate improvement.
5. **Cross-harness canonical-equivalence diff automation**: extend `run-live-e2e.py` to compare the *canonical delivery JSON* (not just pass/fail) across hosts on identical fixtures; publish an equivalence matrix per release. 4 / 5 / 3 / M / medium / **later 0.x**. This is the machine-provable "standard" claim.
6. **Decouple the Grok gate**: reclassify Grok to experimental (documented hold) and make 4/5 live smokes the release bar; retry per release. 3 / 4 / 4 / S / low / **next release**. Removes the frozen-release failure mode.
7. **Multi-agent work-item enforcement** (child briefs as evidence; parent `DONE` requires terminal children; validator enforcement). 3 / 4 / 2 / M / medium / **later 0.x**.
8. **Opt-in assisted classification** (local model or explicit-consent network call; deterministic rules stay default and are always the fallback). 3 / 3 / 2 / M / medium / **later 0.x or 1.0**. Only after the real-prompt corpus quantifies the gap.
9. **Marketplace launch** for Codex/Claude Code/Copilot CLI plugins after the rename, using the existing manifests and CI validators. 4 / 4 / 3 / S / low / **later 0.x**.
10. **Legacy sunset plan** (single entry-point group, schema alias consolidation, `briefspec` removal at 1.0, stated in CHANGELOG). 2 / 3 / 4 / M / low / **1.0**.

## Three highest-conviction bets

### Bet 1 — The re-entry study is the next product thesis
- **Why it dominates:** Every other opportunity—more harnesses, better classification, marketplace growth—assumes the stable-schema → faster-re-entry hypothesis is true for humans. It is currently unfalsified theory with a great bibliography and zero data. The cheapest possible experiment decides whether the product exists.
- **User problem addressed:** engineers paying attention-tax on every agent response; teams running several harnesses with incompatible handoff shapes.
- **Measurable outcome:** ≥80% of timed re-entries identify status, human action, and a proof locator within 15 seconds; ~0 wrong-status classifications over ≥20 audited sessions; annoyance/dismissal rate low enough to keep default `suggest` policy.
- **Must be true before implementation:** 0.5.0 published and installable; ≥5 willing participants with real (not synthetic) sessions; a fixed 10-minute protocol (the Apex pilot questions already define it).

### Bet 2 — Machine-provable cross-harness semantic equivalence
- **Why it dominates:** The defensible moat of a "cross-harness standard" is not adapter count; it is the ability to prove the *same* canonical object is produced by different hosts. Currently the live gate checks per-host pass/fail; the canonical JSON produced in Codex vs OMP vs Kimi is never diffed at field level. Automating that diff converts an anecdote into a release artifact and is the one thing a standards body (or enterprise buyer) can actually audit.
- **User problem addressed:** a user switching between Codex and Claude Code today trusts that a "REVIEW brief" means the same thing everywhere; the equivalence matrix would make that trust checkable.
- **Measurable outcome:** a per-release matrix where identical fixtures produce field-identical `classification`, `brief`, and `explanation.sections` across ≥4 harnesses, with any divergence triaged and documented.
- **Must be true before implementation:** stable `run-live-e2e.py` baseline; the same fixture prompts producing canonical JSON worth comparing (the current runner already collects exports per host).

### Bet 3 — Evidence locator grammar 2.0
- **Why it dominates:** It is an observed defect (Finding 6), near-zero risk, and it directly moves the one user-facing metric the project already claims—evidence-open success rate. Small, boring, high-confidence wins compound trust faster than new surfaces.
- **User problem addressed:** "where is the proof" becomes "open the link" instead of "the verifier says file not found".
- **Measurable outcome:** ≥95% of proof locators in real-session briefs resolve at `resolved` level; zero regressions in the existing structural suite.
- **Must be true before implementation:** a harvested sample of real locator forms from ≥10 real sessions (which doubles as Bet 1's byproduct).

## One contrarian bet

**Concentrate on one flagship harness and the portable skill layer; stop expanding native adapter breadth.**

- **Strongest argument for:** The product's durable value is the reading contract (skills + validator + delivery pipeline), which works in *any* harness that can read a skill. Native lifecycle adapters are the brittle part: each host's hook API is version-dependent, one (Grok) already blocks release, and every new adapter multiplies the legacy/compat tax from Finding 7. The "cross-harness standard" is won by the contract, not by N integrations; deep excellence in one flagship host (Claude Code, the largest addressable audience with first-class hooks) plus network-free skills everywhere beats shallow breadth. Other reviewers will likely recommend the opposite—more harness coverage—making this genuinely contrarian.
- **Strongest argument against:** The product's stated identity is cross-harness; hooks/repair/lifecycle automation are what distinguish it from a plain prompt template, and the honest capability matrix is already a differentiator. Narrowing to one host would look like retreat precisely when multi-agent/harness sprawl (the pain the product addresses) is accelerating, and the author already has working verified adapters for five hosts—the marginal cost of keeping them is documentation, not creation.
- **Evidence needed to decide:** (a) attributable value: how much of the observed benefit in the Bet-1 study comes from skill-driven explanation vs hook-driven enforcement; (b) maintenance load: adapter-breaking changes per host per quarter (the 0.5.0 Grok/Kimi churn is a data point); (c) usage distribution of actual users by harness once published. Decision rule: if hook-driven repair/checkpoint automation delivers <30% of measured value and adapter churn stays high, concentrate; otherwise keep breadth and fund it with maintenance budget.

## What not to build

- **A hosted service, sync, or telemetry layer.** It would violate the network-free trust model that is the security posture's foundation ([direct] `SECURITY.md`). Any "cloud dashboard" converts a private, offline tool into a data controller—a different product.
- **A second brain / knowledge ingestion.** Already explicitly rejected in `docs/theory.md` §11 with the right argument (a compressed rendering must not become canonical memory). Do not revisit, even under "but users asked for Obsidian sync" pressure.
- **Decision approval or agent reasoning.** Brief-Spec presents; it must never approve, rank, or decide. Any "should I merge" scoring blurs the presentation/authority line.
- **Default LLM-based classification.** A network or hidden model call at classification time would break the bounded-privacy invariant and the determinism guarantee. Opt-in, explicitly consented, with deterministic fallback—only after the real-prompt corpus quantifies the gap (Opportunity 8)—is the ceiling, not the default.
- **More harness adapters before value evidence.** Cursor/Goose promotion and any 9th harness are scope-expansion without a validated product. Reject until Bet 1 data exists.
- **An IDE extension or custom editor.** The self-contained HTML export already covers the reading surface; an IDE is a second product with its own maintenance economy.
- **Schema 3.0.** The 2.0 envelope is adequate; the envelope's problems are locator grammar and work-item semantics, both fixable within 2.0.
- **Transcript storage or session analytics** beyond the existing bounded counters. Every byte stored is a privacy liability and a feature-request magnet.

## Proposed next-release steel thread

**Thesis to prove:** a published Brief-Spec 0.5.0 measurably reduces re-entry cost on real sessions.

- **User scenario:** Engineer opens a Codex session from yesterday with 40 tool calls and an interrupted refactor. Within 15 seconds they identify the status (`REVIEW`), the required human action, and one openable proof locator; they act without re-reading the transcript.
- **Entry point:** `uv tool install "brief-spec==0.5.0"` (PyPI) → `brief-spec setup codex` → the hook records `session_start` and classifies the first substantive prompt.
- **Classification behavior:** deterministic local rules; explicit host/user type honored first; ties → `general` with rule IDs reported; subject inferred only for non-fallback types (Finding 5 fix).
- **Explanation behavior:** exactly one of the eight profiles supplies the section order; terminal work appends the unchanged `briefspec:outcome:v1` block inside the `brief-spec:typed:v1` wrapper; the profile never overrides evidence labels.
- **Canonical data changes:** none to the envelope (2.0 stays); add extended locator grammar (Finding 6) and subject-gating (Finding 5). No new required fields.
- **Download or delivery changes:** Markdown/JSON/HTML/ZIP + external receipt unchanged; `verify --level resolved` now resolves `path::test` forms; determinism contract unchanged (byte-identical outputs, already independently confirmed).
- **Harnesses involved:** Codex and Claude Code live (both already pass); OMP and Kimi live (already pass); Grok Build documented as experimental hold (Finding 3) — not a release blocker.
- **Security and privacy boundary:** no network calls in the default runtime; state remains counters/timestamps/hashes only; transcript tail bounded and symlink-refusing; OpenAI audio remains explicit-consent and out of this thread's scope.
- **Automated tests:** hermetic doctor test (Finding 4); locator grammar corpus tests; real-prompt classification corpus v1 with per-type F1 gates; determinism byte-identity tests; schema round-trip matrix (already present, retained).
- **Live acceptance test:** one *real* multi-hour session per verified harness (not the synthetic `evidence.txt` fixtures); a second engineer performs the timed 15-second re-entry; results recorded in the pilot template and attached to the release notes.
- **Success metric:** ≥80% of re-entries meet the 15-second bar; 0 wrong-status briefs in the 20-session audit; 0/1 failing CI jobs on the tagged revision.
- **Explicit exclusions:** no new harnesses; no LLM classification; no schema 3.0; no hosted service; no multi-agent enforcement (deferred); no PDF/audio changes.

## Evaluation plan

- **Classification quality:** labeled real-prompt corpus (v1: ≥100 prompts from real sessions/PR reviews, 20+ per type); macro F1 and per-type F1; tie-rate and fallback-rate as regressions; ambiguity reported as an explicit field. Gate: current thresholds (macro and per-type F1) on the *real* corpus before promoting any classifier change.
- **Explanation usefulness:** per-profile human ratings (5-point) on "would you act on this without re-reading the transcript"; measure per type; log which sections users actually read (screen recording, opt-in).
- **Time to identify status, action, and proof:** timed task with a fixed protocol (the Apex pilot questions); record distribution, not just mean; target ≤15 s at p80.
- **Evidence-open success rate:** fraction of `Proof` locators resolving at `resolved` level across audited sessions; target ≥95% after locator grammar 2.0.
- **Wrong-status rate:** independent audit of ≥20 briefs against ground truth (what actually happened in the session); target 0; every nonzero is a finding, not a metric to tune away.
- **Cross-harness semantic equivalence:** automated canonical-JSON field diff across hosts on identical fixtures (Bet 2); target: field-identical `brief` + `classification` across ≥4 hosts; divergences filed as bugs.
- **Download completion:** export/bundle success rate and byte-determinism checks in CI (already deterministic; keep as regression).
- **Delivery verification success:** `verify --level delivered` against receipt on every live-gate run; target 100%.
- **Installation and rollback reliability:** clean-room matrix (3 OS × 4 Python versions in CI) + snapshot/restore byte-equality (already exists; keep as gate); measure install→doctor→uninstall cycle time.
- **User trust:** short post-session questionnaire (trust in brief vs transcript, willingness to keep the tool installed); correlate with evidence-open success; treat trust erosion (false confidence) as a stop-the-line signal per `docs/theory.md` §12.

## Roadmap recommendation

**Now** (unblock publication, no new product surface):
1. Rename repo to `brief-spec` or revert all URLs to `briefspec`; register or remove `brief-spec.dev` (Finding 2).
2. Make doctor tests hermetic (Finding 4); refresh `docs/verification.md` to match committed reality.
3. Restore hosted CI billing; require green CI on the exact tagged revision (Finding 3).
4. Extend evidence locator grammar (Finding 6) + subject-gating (Finding 5).
5. Reclassify Grok to experimental hold; set release bar at 4/5 live smokes (Finding 3).
6. Ship real-prompt corpus v1 as the classification gate (Finding 5).
7. Publish 0.5.0: PyPI (trusted publishing), GitHub release, marketplace manifests.

Dependencies: (4)(5) only need code; (7) needs (1)–(6) plus green CI; (1) blocks every marketplace command.

**Next** (validate, then widen):
8. Run the human re-entry study (Bet 1) and publish anonymized results.
9. Build cross-harness equivalence diffing (Bet 2); publish per-release equivalence matrix.
10. Marketplace launch follow-through once URLs resolve (Opportunity 9).

Dependencies: (8)(9) need (7); (10) needs (1)+(7).

**Later** (0.x/1.0):
11. Multi-agent work-item enforcement (Finding 8) once a two-agent live scenario is cheap to run.
12. Opt-in assisted classification only if the real corpus shows deterministic rules below gate (Opportunity 8).
13. Legacy sunset execution at 1.0 (Finding 7); single entry-point group; schema alias consolidation.

**Reject or defer:** hosted service, second brain, decision approval, default LLM classification, new harnesses, IDE extension, schema 3.0, transcript storage.

Release gates, stated: publish requires (a) CI green on tagged revision, (b) 4/5 live host smokes on that revision, (c) deterministic gates + hermetic suite, (d) all URLs resolving. Any post-1.0 surface requires Bet-1 data.

## Risks and failure modes

- **Technical:** host hook API drift (already observed: Grok 1.0.x stdout semantics, Kimi project-hook absence) silently breaking lifecycle automation; per-event hook latency accumulating on hosts that spawn Python per event; zipapp staleness vs installed wheel drift.
- **Product:** the core hypothesis may be false—stable cards may not beat well-written freeform prose, or may induce false confidence (people skip evidence because the card feels authoritative); boilerplate fatigue if every turn emits a brief; classification fallback rate high enough that the "type-aware" promise is mostly `general`.
- **Security and privacy:** hooks execute arbitrary local Python at lifecycle boundaries (documented; acceptable only with host trust controls); the OpenAI audio path transmits brief content off-machine (mitigated by explicit consent, but an enterprise data-loss story waiting to happen); the checked-in cloud `briefspec.pyz` is a repository-supplied executable in CI/cloud contexts—its receipt-owned hash must stay verified at run time.
- **Ecosystem:** harness vendors change or remove hook/pre-compaction surfaces without notice; "Copilot support" spans five surfaces with different boundaries (VS Code preview gating, cloud sandbox) — the documented matrix can rot quietly between releases; private-repo launch means no discoverability until public.
- **Maintenance:** single author, bus factor 1, especially the release process; legacy dual-naming doubles every feature's surface until 1.0; nine schema files invite divergence.
- **Adoption:** zero community evidence; the tool requires installing a Python CLI per machine and per repo (setup cost before any value); agents must cooperate with the skill—noncompliant harnesses produce unvalidated output; no network effects or virality mechanism beyond word of mouth.
- **Supply chain:** core is stdlib-only (excellent), but the PDF renderer pulls `playwright` + a Chromium download at `doctor --fix`; PyPI trusted publishing is configured but never exercised; release finalization gates GitHub release on PyPI success (good) but has no rollback story for a half-published state (draft release exists — mitigates).

## Open questions

1. Does the stable-schema reading advantage survive contact with real sessions and real users? (Bet 1; [unknown].)
2. What is the actual distribution of harness usage among target users — is breadth (8 adapters) or depth (1 flagship) the right strategy? (Contrarian bet; [unknown].)
3. Is the Grok instability a Grok Build bug, an adapter bug, or an environment issue — and does Grok matter enough to block releases? (Finding 3; [unknown].)
4. What is the acceptable false-confidence rate? Even one user acting on a compressed brief without opening evidence may outweigh all time savings. [unknown]
5. Should classification ever use a model, and if so, which local/consent model and what latency budget? [unknown]
6. Does the `brief-spec.dev` domain plan (schema `$id`) still make sense, or should `$id` use a versioned GitHub URL? [unknown]
7. Will PyPI trusted publishing and the GitHub `pypi` environment actually succeed on first real run? (Configured, never executed.) [unknown]
8. How much of the measured value comes from hook-driven enforcement vs skill-driven explanation? (Decides the contrarian bet.) [unknown]
9. Can a second maintainer be recruited for the release path before the author's process knowledge decays? [unknown]
10. What do real agents actually cite as proof locators — does the grammar fix cover 95% of forms? (Bet 3 prerequisite.) [unknown]
11. Should `work_items` carry subagent evidence with their own receipts, and who signs a merged multi-agent delivery? [unknown]

## Evidence ledger

| Claim | Label | Locator / source | Date | Proves | Does not prove |
|---|---|---|---|---|---|
| Repo exists at `luanmorenommaciel/briefspec`; private; 0 stars/forks/issues; created 2026-07-31; default branch main | [direct] | `gh api repos/luanmorenommaciel/briefspec`; `git remote -v` | 2026-08-13 | Identity and (lack of) public state | Community/market interest beyond GitHub counters |
| Inspected commit `4adf204` on clean tree at origin/main | [direct] | `git log -1`, `git status --porcelain -b` | 2026-08-13 | Exact revision reviewed | Equality with any unpublished worktree state |
| Latest public release `v0.2.0`; no `brief-spec` on PyPI | [direct] | `gh release list`; `git ls-remote --tags`; `pypi.org/pypi/brief-spec/json` → 404 | 2026-08-13 | Publication truth boundary as of review | PyPI state under the legacy `briefspec` name (not independently checked) |
| Suite results are machine-dependent: 413/414 here; doc claims 414 | [direct] | my `pytest` run; `tests/test_bundle_cli_doctor.py:145`; `docs/verification.md` | 2026-08-13 | One real failure, root-caused to `copilot` on PATH | That the failure occurs in CI (CI is blocked) |
| Deterministic exports/bundles | [direct] | my dual `export`/`bundle` + SHA-256 comparison | 2026-08-13 | Byte-identity claim holds locally | Identical behavior across OS/Python matrix (CI blocked) |
| Classifier ties → `general`; this review task classified `general/fallback/low`, subject `feature` | [direct] | my `classify -` probes; `src/briefspec/work_types.py:286-373` | 2026-08-13 | Fragility for non-canonical phrasing; subject/type independence | Real-world frequency (needs the real corpus) |
| `path::test` locators fail `rendered` verification | [direct] | my bundle verify run | 2026-08-13 | Grammar gap | Prevalence in real briefs |
| Main CI failing since 2026-08-11; release commit's CI failed in 7 s | [direct] | `gh run list` (31516322113, 31708342030) | 2026-08-13 | Hosted-CI gate unmet | Root cause (billing claim comes from `docs/verification.md`, [reported]) |
| Grok gate unstable; ≥11 smoke retries | [direct] | `.briefspec/live-e2e/0.5.0-smoke-grok-review-v2…v13` names; `docs/verification.md` | 2026-08-13 | Repeated instability on one scenario | Attribution (host bug vs adapter bug) |
| Codex/Claude/OMP/Kimi live smokes pass; Claude cost USD 0.3245685 | [direct] | `docs/verification.md` table; `.briefspec/live-e2e/` summaries | 2026-08-13 (doc updated 2026-08-12) | Author-claimed live evidence with sanitized artifacts | Independent reproduction (not re-run by me) |
| `brief-spec.dev` has no DNS | [direct] | `dig brief-spec.dev A/NS` | 2026-08-13 | Schema `$id` domain unregistered | Intent or future plans |
| Metadata URLs point to nonexistent `luanmorenommaciel/brief-spec` | [direct] | `pyproject.toml`, `.codex-plugin/plugin.json`, `plugin.json`, `docs/installation.md`; GitHub API 404 | 2026-08-13 | Publication-readiness defect | Whether a rename is imminent |
| Core has zero runtime deps; zipapp deterministic (fixed timestamps, sorted) | [direct] | `pyproject.toml`, `src/briefspec/bundle.py:26-61` | 2026-08-13 | Supply-chain minimalism of the core | Security of optional renderer deps (playwright, Chromium) |
| 160-prompt corpus is template-generated in-test | [direct] | `tests/test_work_types.py:24-70` | 2026-08-13 | Corpus is synthetic | Generalization to real prompts |
| No recorded pilot results; template only | [direct] | `pilots/apex/README.md` | 2026-08-13 | Human validation absent | That pilots were never run (only that results aren't checked in) |
| One author; 12 commits; 6 Dependabot PRs only | [direct] | `git log --oneline`, `gh pr list` | 2026-08-13 | Bus factor 1; no community contributions | Ability to recruit maintainers |
| Hook/state privacy invariants (1 MiB input, 256 KiB transcript tail, hashed dirs, 0600 atomic writes, fail-open, one repair) | [direct] | `src/briefspec/hooks.py`, `state.py`, `adapters/base.py`, `docs/architecture.md` | 2026-08-13 | Implemented mechanisms | Runtime enforcement under all host payloads (fails open by design) |

## Final recommendation

**ADVANCE WITH CONDITIONS**

**Rationale:** The engineering is genuinely strong and the honesty/determinism culture is a real moat worth protecting, but the product has no user evidence, publication metadata points at nonexistent resources, and the release is frozen behind two external blockers. Advancing means fixing the gate, publishing, and measuring—not building more.

**Single most important next action:** Rename the repository (or revert all URLs), make the doctor tests hermetic, and publish 0.5.0 to PyPI and GitHub with Grok honestly reclassified as an experimental hold.

**Single most important thing to protect:** The truth-boundary culture—evidence labels, verified-vs-published distinctions, fail-open hooks, and refusal to let compression upgrade claims. Every future feature must be judged against whether it strengthens or erodes that boundary.
