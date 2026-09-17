# Brief-Spec Independent Review — DeepSeek V4 Flash

## Reviewer context

- **Provider and model:** deepseek / deepseek-v4-flash, as reported by runtime metadata (workstation model field). No model identity was invented.
- **Harness or interface:** Oh My Pi (OMP), terminal agent harness.
- **Date:** 2026-08-13 (retrieval and observation date; all observations below are from this date).
- **Repository URL:** https://github.com/luanmorenommaciel/brief-spec (canonical post-rename URL; local remote still records `https://github.com/luanmorenommaciel/briefspec.git`, which GitHub redirects).
- **Branch and commit inspected:** `main` at `4adf20412028aa858a982c2149c3622327efa11a` ("New Brief-Spec Release", 2026-08-13 11:05:31 -0300). Local checkout HEAD equals `origin/main` (verified by `git fetch` + `git rev-parse`). Working tree was clean for tracked files; `.briefspec/`, `.coverage`, and caches are gitignored.
- **Latest release observed:** `v0.2.0` ("BriefSpec 0.2.0 — first-class Claude Code experience", published 2026-07-31T20:40:31Z, **no release assets**). Only tags present: `v0.1.0`, `v0.2.0`. No `v0.5.0` tag exists.
- **Materials available:** full local checkout (all docs, source, tests, schemas, skills, workflows); git history (12 commits, 2026-07-31 → 2026-08-13); authenticated `gh` metadata (repo visibility, releases, tags, CI runs, jobs); anonymous HTTP probes of github.com and api.github.com; PyPI JSON API for all four distribution names; two full local test-suite runs plus the release verifier; OMP first-party docs (raw.githubusercontent.com); web search results.
- **Research providers used:** native `web_search` tool (AGENTS.md and Agent Skills landscape); direct fetches of first-party OMP documentation from the `can1357/oh-my-pi` repository. No Exa/Tavily/Firecrawl used.
- **Important inspection limitations:**
  - The repository is **private** (anonymous web and API both return 404; `gh` reports `isPrivate: true`, 0 stars, 0 forks). All permalinks in this review are only resolvable by the owner.
  - I did not install or launch any host CLI, did not re-run the live-host smokes, and did not execute the candidate wheels; live-host results are quoted as reported by the repository's own verification record.
  - The `v0.2.0` release contains no assets, so there are no published binaries to inspect.
  - One full-suite timing run was slowed by an unrelated pytest process from another project running concurrently; the definitive results come from the two runs that completed normally.

## Executive verdict

Brief-Spec is the best-engineered two-week-old project I have reviewed: a deterministic, dependency-free, evidence-disciplined presentation contract with transactional installation, auditable local classification, and reproducible multi-format delivery. The design ideas are genuinely differentiated — nothing else makes "same fields, same order, preserved evidence" a machine-checked contract across harnesses. But the project currently has **zero public surface**: the repository is private, nothing is published to PyPI, the documented public install command is unusable by anyone but the owner, hosted CI is blocked by the GitHub account billing limit, and the verification record — the product's own proof discipline — is already drifting from the committed tree it describes. One test in the suite is environment-sensitive and fails on this machine. The classification benchmark corpus is template-generated, and no human-subject evidence exists for the core reading-cost thesis. The single highest-value move is not more features: it is a public, green, committed-true `v0.5.0` release with one real-prompt evaluation and one small human pilot. Everything else should be deferred until the evidence boundary the product sells is itself publicly verifiable.

**Verdict:** `ADVANCE WITH CONDITIONS`.

## What Brief-Spec has become

Brief-Spec's strongest mental model, stated plainly: **a presentation contract, not a knowledge system.** Agents think and work however they like; the last mile of communication — what is now true, what requires the human, what proves the claim, what remains unknown — is compressed into a fixed, validated shape. Three artifacts carry this: the `outcome-brief` (terminal handoff with five honest statuses and ordered fields), the `session-checkpoint` (orient / teach / spoken renderings of one bounded state), and the `brief-spec` router (eight deterministic work-type profiles that decide which explanation order the reader gets). Around that core sits a delivery pipeline that treats Markdown, JSON, HTML, ZIP, PDF, and MP3 as projections of one canonical object, with cumulative verification levels (structural → resolved → rendered → delivered), external receipts, and hashes — so the presentation can be compressed without erasing provenance. Harness adapters normalize lifecycle events (session start, prompt, tool use, pre-compaction, stop) for eight hosts; installers are transactional, receipt-owned, and reversible; hooks fail open and repair at most once. The product's character is epistemic hygiene: it refuses to let formatting upgrade a claim's authority, and it documents exactly which of its own claims are local, live, hosted, or published.

## Strongest foundations to protect

1. **Evidence discipline as product, not prose.** The evidence schema (`kind`, `locator`, `basis` direct/derived/reported, `result`, `revision`, `observed_at`), status semantics (a `DONE` brief cannot carry required human action or unresolved gaps), and the explicit doctrine "contract validation, not truth validation" are the project's moral core. Evidence: `schemas/evidence.schema.json`, `schemas/outcome-brief.schema.json`, `docs/theory.md` §7–8, `skills/outcome-brief/SKILL.md`.
2. **Deterministic, local, auditable classification.** Regex rule engine with named `rule_ids`, four origins (explicit/host/inferred/fallback), categorical confidence, sticky default, pivot detection, 64 KiB bound, zero network, zero model calls. This is the right architecture for a presentation layer and must not be replaced by an LLM classifier. Evidence: `src/briefspec/work_types.py`, `docs/architecture.md`.
3. **Canonical-object delivery with deterministic bytes.** One object → byte-identical Markdown/JSON/HTML/ZIP across runs (fixed member order, timestamps, modes); manifests; receipts outside the archive; four cumulative verification levels; forged-hash rejection; path containment; command evidence never executed; offline URLs stay unresolved. Evidence: `src/briefspec/delivery.py`, `src/briefspec/bundle.py`, `src/briefspec/verification.py`, `docs/delivery.md`.
4. **Transactional, receipt-owned installation.** Hash-ownership markers, refusal to overwrite foreign files, restore-on-failure, multi-host atomic setup, legacy migration with `--fix`, drift doctor, and a network-free Copilot cloud bridge (self-contained `.pyz`). A real 54-path backup/restore round-trip is documented as byte-exact. Evidence: `src/briefspec/installers.py`, `docs/installation.md`, `docs/verification.md` ("Global and project installation evidence").
5. **Truth-boundary discipline in documentation.** The verification record separates source, local validation, live-host validation, hosted CI, and publication, and honestly holds Grok, hosted CI, and publication as not done. This is rare and valuable; the failure mode it protects against is precisely the one the project must keep avoiding. Evidence: `docs/verification.md` truth-boundary table, README "Install" section.

## Findings

Ordered by consequence. `[direct]` = observed in this inspection; `[reported]` = claimed by the repository's own records; `[external]` = cited current source; `[derived]` = inference; `[proposal]` = recommendation; `[unknown]` = needs evidence.

### F1 — Critical — The product is not publicly installable, and its stated install path is broken for everyone but the owner

- **Severity:** critical.
- **Evidence label:** `[direct]`.
- **Observation:** The repository is private (anonymous github.com and api.github.com both return 404; `gh repo view` reports `isPrivate: true`, 0 stars/forks). The README's primary public install command is `uv tool install git+https://github.com/luanmorenommaciel/briefspec.git@v0.2.0` — impossible for anyone outside the owner's account. All four PyPI names (`brief-spec`, `briefspec`, `brief-spec-renderer-pdf`, `brief-spec-renderer-audio`) return HTTP 404, so no published distribution exists anywhere. The only release, `v0.2.0`, has zero assets.
- **Why it matters:** Every claim in the positioning — "a shared contract across Codex, Claude Code, OMP, Grok, Kimi" — is unobservable by third parties. A cross-harness standard with no public artifact is a private tool. Adoption cannot begin; ecosystem feedback cannot arrive.
- **Recommended response:** Unblock GitHub Actions billing (the stated blocker in `docs/verification.md`), make the repository public, run the staged release workflow on a `v0.5.0` tag, publish identical bytes to PyPI via Trusted Publishing, and only then update README install commands to `brief-spec==0.5.0`.
- **What would verify it:** A green public CI run on the tag; `pip install brief-spec==0.5.0` working anonymously; release assets with SHA-256 sums and build provenance; README install commands pointing at PyPI.

### F2 — High — The verification record is already drifting from the tree it describes

- **Severity:** high.
- **Evidence label:** `[direct]`.
- **Observation:** `docs/verification.md` (updated 2026-08-12) calls the 0.5.0 candidate "This uncommitted working tree" and states the GitHub rename to `brief-spec` should happen "only after local and hosted gates pass." In fact the candidate is now committed at HEAD `4adf204` (clean tree), and the rename has already happened (canonical URL is now `brief-spec`) while hosted CI remains blocked — today's CI run `31708342030` on this exact commit failed all 18 jobs in 2–5 s with no log blobs (the billing-rejection signature).
- **Why it matters:** The product's differentiator is honest truth boundaries. A stale verification record is not a doc bug; it is the product's core value failing in its own repository. "Local candidate" vs "committed HEAD" matters for exactly the reasons the record itself teaches.
- **Recommended response:** Make the verification record machine-generated by the release pipeline (`verify-release.py` already performs 348 checks — have it emit the record with the exact tag revision, CI run IDs, and coverage), and treat any manual edit to it as a review item. Re-run and regenerate the record at every release commit.
- **What would verify it:** The record's revision field equals the tag's commit SHA; regenerating it after a release produces no diff; the record cites the green CI run number.

### F3 — Medium-high — The test suite is not hermetic: one test fails on this machine

- **Severity:** medium (blocking for "414 tests passed" as a universal claim).
- **Evidence label:** `[direct]`.
- **Observation:** Full suite: 414 tests collected; 413 pass, 1 fails — `test_doctor_all_can_treat_an_unavailable_host_as_optional` (expects `WARN`, gets `FAIL`). Root cause: this machine has a `copilot` executable on PATH (super.engineering install), so `doctor_runtime(..., optional_when_absent=True)` never enters its downgrade branch (`not receipt.is_file() and executable is None`), and the test's premise ("unavailable host") does not hold. Coverage measured 86.69% branch vs the 86.86% claimed (the difference is this branch). `scripts/verify-release.py` passes its 348 checks.
- **Why it matters:** The verification record's "local deterministic gates passed" is only true on machines without certain host binaries on PATH. CI would have caught this only on runners where `copilot` is absent. Environment-sensitivity in a suite that gates releases is a reliability risk for every future host the project adds (Goose, Cursor, …).
- **Recommended response:** Make host-presence checks injectable (monkeypatch `shutil.which` or scrub PATH in the fixture) so doctor tests are PATH-independent; add a CI job on a runner image with host CLIs installed to prove both behaviors.
- **What would verify it:** The failing test passes on this machine without code-behavior changes; the suite is green on a machine with all eight host binaries present.

### F4 — Medium — Classification quality is only measured against template-generated prompts

- **Severity:** medium.
- **Evidence label:** `[direct]`.
- **Observation:** The 160-prompt corpus in `tests/test_work_types.py` is built from parameterized templates ("Explore codebase module {index} and map its entry points and flow.") — 20 per type, with macro-F1 ≥ 0.95 / per-type ≥ 0.90 gates. This measures the rules against the rules' own vocabulary, not against real user phrasing.
- **Why it matters:** The classifier is the entry point of the whole reading experience. If real prompts (terse, mixed-type, misspelled, domain jargon) classify worse than templates, users get the wrong explanation order — and the project would not know.
- **Recommended response:** Build a sanitized real-prompt corpus (e.g., 100–200 prompts drawn from real sessions, labels agreed by the author, prompts stripped of project content), commit it with provenance, and gate releases on it alongside the template corpus. Publish macro-F1 and the confusion matrix.
- **What would verify it:** The committed real corpus passes the same F1 gates; a README section reports both corpus results with dates.

### F5 — Medium — The core thesis has no human-subject evidence

- **Severity:** medium (product risk).
- **Evidence label:** `[direct]` for the pilot's existence; `[reported]` for its claims.
- **Observation:** `docs/theory.md` explicitly disclaims validated interaction ("not a claim that the complete Brief-Spec interaction has already been validated in a controlled human-subject study") and lists falsifiable tests (time to identify outcome/action, evidence-open success, annoyance rate). `pilots/apex/` defines exactly those questions but contains only synthetic fixtures and a results template — no results.
- **Why it matters:** The entire value proposition is cognitive-load reduction. Every design decision (five statuses, field order, limits of 5/3/3, checkpoint thresholds) is a hypothesis. A competitor with the same formats but measured reading-time evidence would win the "standard" argument on data.
- **Recommended response:** Run one small controlled pilot (≥10 engineers; same synthetic handoff corpus in brief vs non-brief format; measure time-to-answer for status/action/proof, error rates, and perceived effort), publish anonymized results and effect sizes in the repo.
- **What would verify it:** A committed results file with n, protocol, median times, and error rates; a one-paragraph "what would falsify us" update in theory.md.

### F6 — Medium — Experimental host breadth exceeds verified depth, and enforcement coverage is uneven

- **Severity:** medium.
- **Evidence label:** `[direct]` (registry, docs) + `[external]` (OMP docs).
- **Observation:** Eight adapters exist; five are "verified", three experimental (Copilot, Cursor, Goose) plus a Copilot cloud bridge. OMP's own documentation states `session_stop` "never fires for task/subagent sessions" — so terminal-outcome enforcement cannot run in OMP subagent contexts, a boundary the adapter registry's boolean surface does not fully express. Grok's live gate is held on host tool instability (per `docs/verification.md`).
- **Why it matters:** Each experimental adapter is unverified public surface that can fail in ways doctor cannot see; enforcement claims that differ per host erode the "same contract everywhere" promise. Breadth now costs evidence later.
- **Recommended response:** Keep the registry but add an explicit `enforcement` capability per adapter (which hooks can actually block/repair in that host version), and demote the three experimental hosts in README from a support table to a "not yet verified" list until each has an authenticated live gate. Do not add further adapters before publication.
- **What would verify it:** `capabilities all --json` exposes per-host enforcement truthfully; README's support table and compatibility.md agree with it.

### F7 — Low — Compatibility breadth (dual names, dual schemas, dual env vars) is costly for a 0.x line with no users

- **Severity:** low.
- **Evidence label:** `[direct]`.
- **Observation:** The same distribution ships `brief-spec`/`briefspec` CLIs, `brief_spec`/`briefspec` imports, `BRIEF_SPEC_HOME`/`BRIEFSPEC_HOME`, canonical and legacy schemas, markers, receipts, state directories, and two renderer entry-point groups, with legacy paths warning on use. `docs/compatibility.md` documents the promise; `schemas/` contains six delivery-related files to support it.
- **Why it matters:** Every legacy path is permanent test and documentation surface. For a project with zero known users, carrying two of everything through the entire 0.x line is speculative investment in compatibility with an audience that has not materialized.
- **Recommended response:** Keep the `0.x` promise (it is already built and tested), but announce a defined 1.0 cutover that drops legacy aliases, and make that cutover a documented milestone rather than an open-ended burden. Do not add new dual paths (e.g., no legacy spellings for the typed region or delivery 2.0).
- **What would verify it:** A compatibility.md section stating the 1.0 cutover rule and the migration command; no new legacy aliases added in the next release.

### F8 — Low — Enforcement machinery is a large share of complexity for an opt-in feature with no user evidence

- **Severity:** low.
- **Evidence label:** `[derived]`.
- **Observation:** The one-repair, block-one-stop, `stop_hook_active` guard, cooldown/minimum-turn logic, and enforce/auto policies represent a substantial portion of `hooks.py`/`triggers.py`/`state.py`, and `docs/theory.md` itself concedes a stop hook cannot reliably infer task boundaries. No evidence exists that users want enforced formatting (vs suggested formatting).
- **Why it matters:** This is the riskiest UX surface (it can interrupt work — the one thing the product promises not to do) and the hardest to validate per host. If it annoys, it poisons the whole product.
- **Recommended response:** Ship `suggest` as the only default; treat `enforce` as experimental until the human pilot measures checkpoint dismissal/annoyance rates; consider demoting one-repair from the differentiator narrative.
- **What would verify it:** Pilot data on annoyance; adoption of `enforce` in config (only measurable after publication via user reports — no telemetry).

### F9 — Opportunity — The public docs and skills are already aligned with the de facto SKILL.md and AGENTS.md conventions

- **Severity:** opportunity.
- **Evidence label:** `[direct]` (repo) + `[external]` (agentskills.io; github.blog).
- **Observation:** The three skills are standard `SKILL.md`-frontmatter assets (name/description) under `skills/<name>/SKILL.md`, the layout OMP, Claude, Codex, and Copilot all discover natively; the Copilot cloud bridge installs `.github/instructions/*.instructions.md`, matching GitHub's instruction convention; OMP's first-party docs confirm the event names the adapter uses (`session_start`, `before_agent_start`, `tool_result`, `session.compacting`, `session_stop`).
- **Why it matters:** Brief-Spec's distribution mechanism already rides the two emerging cross-tool conventions (Agent Skills, Dec 2025 open standard with ~40+ clients by mid-2026; AGENTS.md supported by Copilot since Aug 2025). That is strategic tailwind it can exploit without building anything.
- **Recommended response:** Explicitly state this alignment in README/compatibility docs, and add the three skills to a public Agent Skills registry when the repo goes public.
- **What would verify it:** A doc section citing the SKILL.md spec and the supported discovery paths; skills installable from a public registry URL.

## Ten opportunities

1. **Public, verifiable v0.5.0 publication** (repo public + green CI + PyPI + release assets + provenance). User impact: 5. Strategic leverage: 5. Evidence confidence: 5. Effort: S (billing fix + run pipeline). Risk: low. Horizon: **next release.**
2. **Committed-true, machine-generated verification record** per release (revision + CI run IDs). User impact: 3. Strategic leverage: 4. Evidence confidence: 5. Effort: S. Risk: low. Horizon: **next release.**
3. **Hermetic test suite** (host-PATH-independent doctor tests; CI job with host CLIs installed). User impact: 2. Strategic leverage: 3. Evidence confidence: 5. Effort: S. Risk: low. Horizon: **next release.**
4. **Real-prompt labelled classification corpus** committed with provenance, gating releases alongside the template corpus. User impact: 4. Strategic leverage: 4. Evidence confidence: 4. Effort: M. Risk: low. Horizon: **later 0.x.**
5. **Small controlled human-subject reading pilot** (time-to-answer, error rates, perceived effort; results published in repo). User impact: 5. Strategic leverage: 5. Evidence confidence: 3 (results may falsify). Effort: M. Risk: medium (thesis risk — that is the point). Horizon: **later 0.x.**
6. **Per-host live-gate matrix made continuous and public** (disposable-repo smokes per host version, results table with dates and host versions in the repo). User impact: 4. Strategic leverage: 4. Evidence confidence: 4. Effort: M. Risk: medium (host instability). Horizon: **later 0.x.**
7. **Per-host enforcement-capability truth** (adapter-level flag for which hooks can block/repair in that host version; surfaced in `capabilities`). User impact: 3. Strategic leverage: 3. Evidence confidence: 4. Effort: S. Risk: low. Horizon: **later 0.x.**
8. **Public schema registry** (host the `$id` URLs — `brief-spec.dev/schemas/*` — with versioned JSON Schemas, so third parties can validate delivery objects). User impact: 3. Strategic leverage: 4. Evidence confidence: 4. Effort: M. Risk: low. Horizon: **1.0.**
9. **`brief-spec brief <file>` end-to-end command** (classify → wrap typed region → validate → export delivery in one step), making the pipeline usable by agents and scripts without the skill. User impact: 3. Strategic leverage: 3. Evidence confidence: 4. Effort: S. Risk: low. Horizon: **later 0.x.**
10. **Cross-harness semantic-equivalence benchmark** (one canonical object pushed through each host's hooks; assert identical status/fields JSON). User impact: 4. Strategic leverage: 5. Evidence confidence: 4. Effort: M. Risk: medium. Horizon: **later 0.x.**

## Three highest-conviction bets

1. **Public, green, published v0.5.0 (opportunity 1 + 2 + 3 as one release).** It dominates because every other opportunity's value is invisible until the artifact is public: a real corpus benchmark means nothing unpublished, a live matrix means nothing in a private repo, a pilot needs a URL to share. This is also the only bet that converts the project's own evidence discipline from narrative into infrastructure. Measurable outcome: zero failed CI jobs on the tag; `pip install brief-spec==0.5.0` works anonymously; verification record cites the exact commit and run. Must be true first: GitHub billing unblocked; PyPI Trusted Publishers registered; hermetic suite green.
2. **Evidence-grade evaluation of classification and explanation (opportunities 4 + 5).** The project's thesis — reading-cost reduction — is currently believed, not shown. A real-prompt F1 benchmark plus a 10-person timed reading pilot either validates the design or redirects it, and the theory doc already defines the falsifiable tests. Measurable outcome: published macro-F1 on real prompts (gate ≥ template-corpus result) and median time-to-answer reduction vs unstructured handoffs with error rates. Must be true first: permission to use sanitized real prompts; a pilot protocol; a committed results format.
3. **Continuous per-host live-gate matrix with semantic equivalence (opportunities 6 + 10).** The "cross-harness standard" claim lives or dies on demonstrated equivalence, not declared support. Turning one-off smokes into a repeatable, versioned matrix is the difference between a support table and a standard. Measurable outcome: each verified host has a dated gate result tied to host version, and a canonical-object equivalence check across hosts passes. Must be true first: stable disposable-repo harness automation (already prototyped in `scripts/run-live-e2e.py`); Grok tool-path stability or an explicit exclusion.

## One contrarian bet

**Prune the host matrix to three verified hosts (Codex, Claude Code, OMP) and remove Copilot cloud, Cursor, Goose, and the audio renderer from the 1.0 critical path — publish the schema and skills as the standard, not the adapter count.**

- **Strongest argument for:** A standard is made by depth on the hosts that matter plus a stable public contract, not by a long support table. Each experimental adapter is unverified surface that consumes evidence budget (the Grok hold already blocks release); the Copilot cloud bridge in particular is a large, novel, hard-to-validate component (ephemeral sandbox, PascalCase hook duality, `.pyz` in-repo execution) with no authenticated live gate. The SKILL.md ecosystem does the cross-tool distribution for free; the delivery schema does the cross-tool contract. Cutting breadth halves maintenance and lets every remaining release gate be honestly green.
- **Strongest argument against:** "Cross-harness" is the positioning; trimming to three hosts concedes the GitHub-native story (Copilot cloud is the most differentiated integration and the only network-free one), and the users who arrive may arrive via Copilot or Cursor. Removing audio drops a finished, tested capability (local macOS + OpenAI with consent) that is already built. Also, the choice is hard to reverse once 1.0 brands itself as "Codex/Claude/OMP."
- **Evidence needed to decide:** Which hosts early adopters actually run (only measurable after public publication — so the bet is: publish, then re-decide at 1.0 with usage signals); the real maintenance cost per adapter (test hours, hook drift frequency); whether an authenticated Copilot cloud gate can pass at all. Until then, keep experimental hosts behind an explicit "not verified" label rather than deleting them.

## What not to build

- **LLM-based classification or any network/model call in the router** — would destroy determinism, privacy, and auditability; the regex engine with rule IDs is a feature, not a limitation.
- **A second brain / knowledge graph / transcript ingestion** — already refused in theory.md §11; any promotion flow into Nexo/Obsidian must stay explicit and manual.
- **An MCP server or tool surface** — Brief-Spec is a presentation contract; MCP solves a different problem and would blur the "not another tool platform" boundary.
- **A hosted validation/telemetry service** — the fail-open, no-network hook design is a selling point; a cloud dependency would break the Copilot cloud bridge's network-free property and add a privacy surface.
- **New work types or a user-extensible type system** — eight types with fixed profiles are the schema; extensibility here fragments the reading experience it exists to standardize.
- **New renderers (DOCX, PPTX, EPUB) or new audio providers** — diminishing returns; the pipeline is proven with one offline and one consented provider.
- **Native plugin duplication** — the docs already warn against it; do not invest further in marketplace mechanics beyond the existing manifests.
- **Decision approval, encryption of briefs, or "verified by" attestation services** — human judgment is the stated endpoint; cryptographic theater adds complexity without changing trust.
- **New harness adapters (Windsurf, Cursor deeper, Devin, …) before publication** — see the contrarian bet; breadth now is debt.
- **Per-team status vocabularies or custom field sets** — would silently void the cross-team comparability the status enum provides.

## Proposed next-release steel thread

**Thesis:** A public, committed-true `v0.5.0` that any engineer can install anonymously and whose evidence claims are all machine-checkable.

- **User scenario:** An engineer reads the README, runs `uv tool install "brief-spec==0.5.0"` (or `pipx`), runs `brief-spec setup codex --scope user` and `brief-spec setup omp --scope user`, runs `brief-spec doctor all --probe --all-scopes`, asks Codex to review a pull request, receives a typed `review` explanation plus an Outcome Brief, exports HTML/PDF, and verifies the receipt.
- **Entry point:** PyPI distributions `brief-spec==0.5.0` (+ both renderers, version-aligned); the staged tag-driven workflow (`release.yml`) is the only path that produces them.
- **Classification behavior:** unchanged rule engine; the release adds the committed real-prompt corpus (target n ≥ 100, sanitized) with macro-F1 ≥ 0.95 and per-type ≥ 0.90 gates alongside the template corpus.
- **Explanation behavior:** the typed region `<!-- brief-spec:typed:v1 -->` wraps profile sections and the unchanged `briefspec:outcome:v1` brief; classification metadata (`classified_at`, `origin`, `confidence`, `rule_ids`) captured once; no render-time timestamps.
- **Canonical data changes:** none breaking — `brief-spec-delivery/2.0` stays; the only data change is the verification record becoming a release-generated artifact that carries the tag revision and CI run IDs.
- **Download or delivery changes:** none to the pipeline; publication adds PyPI + GitHub release assets with SHA-256 sums and build provenance attestations; `verify-published` waits for PyPI visibility and clean-installs the immutable bytes.
- **Harnesses involved:** Codex, Claude Code, OMP (verified live gates re-run on the tag); Kimi and Grok remain documented holds (Grok's tool-path instability is an explicit release blocker per the project's own record — so "hold" means the record says hold, not "green").
- **Security and privacy boundary:** hooks unchanged (fail-open, 1 MiB bound, no network, no raw prompt persistence, private file modes); the corpus is sanitized of project content; the OpenAI audio path stays outside this release's required gates (no credential on the machine, per the record); zipapp hooks remain repo-content executables — documented as a trust boundary, not a security boundary.
- **Automated tests:** hermetic suite (PATH-isolated doctor tests) on 3 OS × 4 Python versions; corpus F1 gates; `verify-release.py` 348 checks; clean-room wheel and sdist installs; renderer E2E jobs (PDF/Chromium, local audio).
- **Live acceptance test:** public CI green on the tag; anonymous PyPI install in a clean environment; disposable-repo live smokes for Codex/Claude/OMP with receipt and clean-worktree assertions (reusing `scripts/run-live-e2e.py`); all results cited by run ID in the generated verification record.
- **Success metric:** the tag's CI run is green; `brief-spec==0.5.0` installs anonymously within 24 h of tagging; the verification record's revision field equals the tag SHA and its CI evidence matches real run IDs; the repo is public.
- **Explicit exclusions:** no new work types, no new adapters, no enforcement-policy changes, no schema changes, no telemetry, no audio-gate requirement, no human pilot in this release (it is the next one).

## Evaluation plan

- **Classification quality:** macro-F1 and per-type F1 on the committed real-prompt corpus and the template corpus, with confusion matrix; a "no-regression vs previous release" gate; per-origin accuracy breakdown (explicit/host/inferred/fallback) so fallback rate is visible.
- **Explanation usefulness:** pilot self-report (perceived effort, 5-point) and answer-extraction correctness (can a reader fill status/action/proof from the brief alone without the transcript).
- **Time to identify status, action, and proof:** controlled timed tasks on matched brief vs non-brief handoffs; report median and interquartile range, not means alone.
- **Evidence-open success rate:** fraction of proof locators that resolve to the correct artifact/file/commit when opened; tracked per kind (file/command/test/url).
- **Wrong-status rate:** pilot errors distinguishing DONE/REVIEW/DECIDE/BLOCKED/FAILED; also a corpus-level check that status semantics constraints (e.g., DONE without gaps) hold in real handoffs.
- **Cross-harness semantic equivalence:** feed one canonical delivery object through each host's hook/validation path and diff the resulting JSON (status, fields, order, hashes); assert byte equality of exports across hosts.
- **Download completion:** bundle bytes identical across platforms and runs (already asserted locally; move to CI across the 3-OS matrix).
- **Delivery verification success:** receipt hash matches delivered bytes; `verify --level delivered` passes on re-run; offline URL evidence stays visibly unresolved rather than passing.
- **Installation and rollback reliability:** fresh install, upgrade, downgrade, and uninstall on 3 OS × 4 Python versions in clean environments; byte-restore check for rollback (the 54-path round-trip pattern, automated); foreign-file preservation.
- **User trust:** pilot item "did you re-verify any proof after reading the brief?" and a gap-honesty rate (fraction of handoffs with explicit gaps when the underlying work had none claimed); long-run proxy after publication: user-reported false-confidence incidents — no telemetry.

## Roadmap recommendation

**Now (next release — the steel thread):**
- Unblock GitHub Actions billing; make repo public; finalize rename documentation.
- Fix the hermetic test failure; add host-CLI-present CI job.
- Make the verification record machine-generated and committed-true.
- Tag `v0.5.0`, run the staged workflow end to end, publish to PyPI, verify anonymously.
- Reserve/claim all four PyPI names (publication does this; verify no squatting between now and then).

**Next (later 0.x):**
- Real-prompt corpus + published benchmark (gate).
- Human-subject pilot (n ≥ 10), results committed; update theory.md's falsifiable-claims section with results.
- Continuous live-gate matrix with per-host versions; enforcement-capability flags in `capabilities`.
- `brief-spec brief <file>` end-to-end command.

**Later (toward 1.0):**
- Public schema registry hosting the `$id` URLs; third-party validation documentation.
- Compatibility cutover decision: drop legacy aliases (`briefspec` CLI, legacy env/state/schemas), with a documented migration command and a deprecation window.
- Decide the host matrix by usage signals; possibly re-include Copilot cloud with an authenticated gate.
- Skills published to a public Agent Skills registry.

**Reject or defer:** LLM classification; MCP server; hosted services/telemetry; new work types; DOCX/PPTX renderers; per-team vocabularies; new adapters before 1.0; second-brain features.

**Dependencies and release gates:** billing fix → hermetic suite → record generator → tag → CI green → PyPI publish → repo public. The pilot and corpus do not gate v0.5.0 (evidence disciplines them as 0.6/0.7), but the real-corpus gate should land before any classification-rule changes. 1.0 gates on: a public schema registry, the compatibility cutover plan, and at least one published human-subject result.

## Risks and failure modes

- **Technical:** host hook-contract drift (each host can change event shapes or stop-hook semantics without notice — OMP's `session_stop` already never fires for subagent sessions); Grok's unstable read/list tool path (already holding release); Playwright/Chromium and Poppler/ffmpeg maintenance across OS versions; ZIP determinism fragile if a new renderer touches ordering; the `brief_spec`/`briefspec` dual-import trick (`__path__` aliasing) is elegant but brittle under future packaging changes.
- **Product:** the reading-cost thesis is unvalidated — if stable cards do not reduce time-to-answer or increase evidence inspection, the differentiator collapses into formatting; enforcement can interrupt work, the one thing the product promises not to do; status vocabulary may not express real states (theory.md's own falsification list).
- **Security and privacy:** hooks execute `python3` from host config and, in project scope, a `.pyz` checked into the repository — a malicious repo could ship a hostile hook/bridge (docs correctly call hooks "a UX enforcement mechanism, not a security boundary," but the README must keep saying so); skills are instructions, so a compromised `SKILL.md` is prompt-injection surface (the same supply-chain class documented for Agent Skills in early 2026); state hashes and 1 MiB bounds are sound, but host payloads themselves are out of scope by design.
- **Ecosystem:** Agent Skills and AGENTS.md are moving fast and both are now owned by large vendors (Anthropic; GitHub/Microsoft) — a vendor could ship a competing output contract with distribution advantage; MCP growth could swallow "delivery" if MCP adds result-schema conventions; the window where a small independent can define the handoff contract is open but may not stay open.
- **Maintenance:** single maintainer, ~6 k LOC core plus two renderer packages, 12 commits in 2 weeks; the dual-naming compatibility surface doubles doc/test burden; GitHub billing is currently the release gate and is outside the code's control.
- **Adoption:** private repo + broken public install command = zero addressable users today; `uv` requirement and Playwright/Poppler/ffmpeg prerequisites raise the entry bar; the product asks users to change how agents end every task — a behavior change with network effects.
- **Supply-chain:** full-SHA action pins and Dependabot are in place (good); PyPI names are currently unclaimed — typo-squatting or name-squatting before publication is possible; Trusted Publishing is correctly designed, but only matters once billing is unblocked.

## Open questions

1. When will GitHub Actions billing be unblocked, and is there a plan if it is not (e.g., self-hosted runner or a different CI provider for the release gate)?
2. Which hosts do early users actually run? (Unanswerable until publication; the 1.0 matrix decision depends on it.)
3. Does the reading pilot confirm or falsify the time-to-answer hypothesis? What is the minimum effect size the author would accept as validation?
4. Is Grok's tool-path instability fixable from Brief-Spec's side, or should Grok stay on hold indefinitely?
5. Should the Copilot cloud bridge remain in the 1.0 scope given no authenticated live gate exists?
6. Are the 5/3/3 field limits and the five-status vocabulary right, or are they artifacts of the author's own sessions?
7. Is the OpenAI audio provider worth keeping when no credential exists on the development machine and local `say` covers the demo?
8. Should `brief-spec.dev` / schema hosting be acquired before 1.0, and who pays for it?
9. What is the actual cost of the legacy `0.x` compatibility surface per release? (Measurable only after a few release cycles.)
10. Will `enforce` mode be used at all, or is `suggest` the real product?

## Evidence ledger

| Claim | Label | Locator | Observed | Proves | Does not prove |
| --- | --- | --- | --- | --- | --- |
| Repo private, 0 stars/forks, renamed to `brief-spec` | `[direct]` | `gh repo view luanmorenommaciel/briefspec` (`isPrivate:true`, url `…/brief-spec`), anonymous web/API 404 | 2026-08-13 | Public surface is zero; rename executed | Anything about intent or timeline of the rename |
| HEAD `4adf204` = origin/main; tree clean | `[direct]` | `git rev-parse origin/main`, `git status` in local checkout | 2026-08-13 | Candidate is committed; verification.md's "uncommitted" claim is stale | Whether earlier commits contain the same candidate |
| Latest release v0.2.0, no assets; tags v0.1.0/v0.2.0 only | `[direct]` | `gh release view v0.2.0`, `git ls-remote --tags` | 2026-08-13 | No published 0.5.0 anywhere | Asset-less release's content quality |
| All four PyPI names 404 | `[direct]` | `https://pypi.org/pypi/{brief-spec,briefspec,brief-spec-renderer-pdf,brief-spec-renderer-audio}/json` | 2026-08-13 | Nothing ever published to PyPI | Whether names are intentionally reserved |
| CI on HEAD failed 18/18 jobs in 2–5 s; no log blobs | `[direct]` | `gh run view 31708342030`, jobs API, log API (BlobNotFound) | 2026-08-13 | Jobs never executed; consistent with billing rejection | The exact billing message |
| 414 tests collected; 413 pass, 1 environment-sensitive failure; 86.69% branch | `[direct]` | `uv run pytest` (twice), `--collect-only` | 2026-08-13 | "414 passed" only holds without `copilot` on PATH | Any claim about other environments |
| `verify-release.py` passes 348 checks | `[direct]` | `uv run python scripts/verify-release.py` | 2026-08-13 | Source release surfaces are consistent | Published-artifact equivalence |
| Classifier is local, deterministic, rule-ID auditable | `[direct]` | `src/briefspec/work_types.py` | 2026-08-13 | Architecture of classification | Real-world classification quality |
| 160-prompt corpus is template-generated | `[direct]` | `tests/test_work_types.py::_corpus`, F1 gates | 2026-08-13 | Benchmark exists and passes | That templates represent real prompts |
| Deterministic delivery + verification levels implemented | `[direct]` | `src/briefspec/delivery.py`, `bundle.py`, `verification.py`, `schemas/brief-spec-delivery.schema.json` | 2026-08-13 | Pipeline exists and is tested | Live-host end-to-end behavior |
| Transactional installer with receipts/rollback | `[direct]` | `src/briefspec/installers.py` | 2026-08-13 | Ownership + rollback design | The 54-path byte-exact restore claim (that is `[reported]`) |
| Live smokes: Codex/Claude/OMP/Kimi pass, Grok hold; costs quoted | `[reported]` | `docs/verification.md` (candidate record) | 2026-08-13 (doc), not re-run by reviewer | Author observed these runs | Independent reproduction |
| Skills use standard SKILL.md layout; OMP event names match | `[direct]` + `[external]` | `skills/*/SKILL.md`; `raw.githubusercontent.com/can1357/oh-my-pi/main/docs/skills.md` + `extensions.md` | 2026-08-13 | Distribution rides the Agent Skills convention; adapter events are real | That hosts load them identically in every version |
| SKILL.md is a de facto cross-agent standard; AGENTS.md conventions | `[external]` | agentskills.io/specification; anthropic.com engineering post (Oct 2025); github.blog changelogs (2025-08-28, 2026-06-18) | retrieved 2026-08-13 via web_search | Ecosystem tailwind exists | Brief-Spec's share of it |
| OMP `session_stop` never fires for task/subagent sessions | `[external]` | `raw.githubusercontent.com/can1357/oh-my-pi/main/docs/extensions.md` | 2026-08-13 | Enforcement coverage is host-dependent | Whether this blocks Brief-Spec in practice |

## Final recommendation

**Verdict:** `ADVANCE WITH CONDITIONS`

**Rationale:** The design and engineering are ahead of the project's stage — deterministic local classification, evidence schema, transactional installers, and truth-boundary documentation are genuinely differentiated and defensible. But a "cross-harness standard" with a private repository, a broken public install command, zero published distributions, a billing-blocked CI, one environment-sensitive failing test, and a synthetic-only classification benchmark is not yet a standard; it is a well-built prototype with an excellent evidence habit. The conditions are concrete and bounded: publish publicly with green CI, make the verification record committed-true, and add one real-prompt evaluation plus one small human pilot. Meet those and the project has the strongest claim in its niche; miss them and the next release simply adds more unverifiable surface.

**The single most important next action:** Unblock GitHub Actions billing and ship one fully green, public `v0.5.0` release through the staged workflow (tag → CI → PyPI Trusted Publishing → release assets with provenance), then verify an anonymous install of `brief-spec==0.5.0` — because every other recommendation is downstream of a public, installable artifact.

**The single most important thing Brief-Spec should protect:** Its evidence discipline — the distinction between what is directly observed, locally validated, live-validated, hosted-validated, and published, enforced in both the product (evidence schema, verification levels, fail-open hooks) and its own documentation (truth-boundary record). That discipline is the actual moat; the formats are copyable, the honesty is not.
