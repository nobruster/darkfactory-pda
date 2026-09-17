# Brief-Spec Independent Review — Claude Opus 5 (1M context)

## Reviewer context

- **Provider and model:** Anthropic, Claude Opus 5. Exact runtime model ID reported by the harness: `claude-opus-5[1m]`. Normalized slug used for this file: `anthropic-claude-opus-5`.
- **Harness / interface:** Claude Code CLI (Claude Agent SDK), non-interactive session, running on macOS (Darwin 25.3.0). Brief-Spec itself was active in this session as an installed lifecycle integration, which produced incidental runtime evidence used below.
- **Date of review:** 2026-08-13 (all retrievals same day unless stated).
- **Repository URL:** `https://github.com/luanmorenommaciel/briefspec` as given in the task. GitHub reports the canonical `full_name` as **`luanmorenommaciel/brief-spec`** — the repository has already been renamed and the old path is a redirect. Repository **visibility is `private`**.
- **Branch and commit inspected:** `main` at `4adf20412028aa858a982c2149c3622327efa11a` ("New Brief-Spec Release"). Local checkout `HEAD` is byte-identical to `origin/main` (`git diff --stat origin/main HEAD` empty), and the tracked working tree is **clean** (`git status --short` produced no output). Untracked-but-ignored material is present (`.briefspec/`, `.venv/`, `.coverage`, `.sc/`); I read from it but changed nothing.
- **Latest visible release:** `v0.2.0`, published 2026-07-31T20:40:31Z. Tags present: `v0.1.0`, `v0.2.0`. **No `v0.5.0` tag or release exists**, while source, docs, and manifests are all at `0.5.0`.
- **Materials available:** full local checkout (130 tracked files, ~16k lines across docs/src/tests/scripts), the ignored local evidence tree `.briefspec/` (live-host smoke runs, six candidate distributions, release manifest), and the GitHub API (releases, tags, issues, PRs, Actions runs, repo metadata) via `gh`.
- **Source treated as authoritative:** the local checkout, because it is identical to `origin/main` at the inspected commit. Where the checkout and the *published release* differ, I treat them as different truth states and say which one I mean.
- **Research providers used:** native Claude Code `WebSearch` and `WebFetch` (Anthropic-provided search), plus `gh` (GitHub REST API), `curl` against `pypi.org`, and `nslookup`. **Exa, Tavily, and Firecrawl were not used.**
- **Inspection limitations:**
  - I did **not** execute the test suite, `ruff`, `uv build`, or any installer, because the task authorizes exactly one write (this file) and those commands write to `.coverage`, `.pytest_cache/`, `dist/`, or host configuration. Every claim about test *results* is therefore repository-reported, not reproduced by me. Claims about test *content* are direct reads.
  - I ran the classifier as a pure in-process import with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, which writes nothing. Those results are direct runtime observations.
  - Renderer behavior (PDF, MP3), Playwright, Poppler, and `ffmpeg` paths were read but not executed.
  - I did not read `output/tencent-hy3.md`, which appeared in `output/` during this run.
  - The repository is private, so GitHub permalinks in this document resolve only for authorized accounts.

## Executive verdict

Brief-Spec is a genuinely good engineering artifact wrapped around one unproven claim and one dangerous one.

The strong part is the delivery layer: one canonical object, byte-deterministic Markdown/JSON/HTML/ZIP projections, manifests, external receipts, four cumulative verification levels that refuse to promote unresolved evidence, transactional installers with hash receipts and rollback, and a design document that states honestly which research does and does not support the product. That layer is more disciplined than most 1.0 developer tools.

The unproven claim is the reading benefit. `pilots/apex/` contains a well-designed measurement plan and an empty results template. After five versions of work, there is no human evidence that any of this reduces time-to-status, time-to-action, or wrong-status rate.

The dangerous claim is classification. The 0.5.0 headline feature is a regex classifier whose release gate is circular: the "160-prompt labelled corpus" is 8 sentence templates × 20 numeric substitutions, written from the classifier's own keyword list. I ran it on this very review request; it returned `implementation`, subject `pull-request`, confidence **high** — the type and subject were extracted from the prompt's *prohibitions* ("Do not implement…", "…open a pull request"). A product whose core invariant is "never infer success" ships a component that confidently infers intent from negated text, and stamps that guess into the canonical object with no binding back to the classifier.

Fix classification honesty, get human evidence, and make the schemas actually obtainable. Then this is a standard candidate.

## What Brief-Spec has become

Strip the vocabulary away and Brief-Spec is two products that currently share one package.

**Product one is a handoff contract.** Any agent, on any host, ends substantive work with the same seven fields in the same order — Status, Outcome, Human action, Proof, Gaps, Next, Open — inside invisible Markdown markers, with a validator that enforces order *and* status semantics. `DONE` cannot carry required human action or unresolved gaps. `DECIDE` must name the open decision. `BLOCKED` must name both a gap and a next step. `DONE` in the canonical JSON additionally requires at least one `direct` or `derived` proof item whose result is `pass`. The value is not brevity; it is that position becomes a cue, so you stop re-learning where each agent hid the caveat.

**Product two is verified delivery.** Parse that bounded region once into a canonical `brief-spec-delivery/2.0` object, then render every download from it. Canonical time is captured once (`--created-at`, then `SOURCE_DATE_EPOCH`, then source mtime, then now) and reused everywhere; ZIP member order, timestamps, modes, and compression are fixed; so identical input yields identical bundle bytes. `manifest.json` records size and SHA-256 per member. The receipt lives *outside* the archive so its hash can attest to the delivered bytes without becoming self-referential. Verification is four cumulative levels — `structural`, `resolved`, `resolved`+, `delivered` — and `resolved` never executes command evidence, marks offline and private URLs as unresolved rather than passing, and refuses paths that escape the workspace. `deliver` refuses to emit a delivered receipt for a bundle that cannot first prove rendered integrity (`bundle.py:277-286`).

The honest one-sentence version: **Brief-Spec is a provenance-preserving projection layer for agent output.** The eight work types, three checkpoint modes, eight harness adapters, and audio pipeline are surfaces on top of that. The layer underneath is the asset. External research sharpens this: Agent Skills, MCP, and Agent Plugins 1.0 have standardized *portability* across roughly 40 tools in eight months and explicitly leave trust, provenance, attestation, and verification out of scope. That is precisely the hole Brief-Spec is standing in — and it does not yet say so.

## Strongest foundations to protect

**1. Determinism as a first-class property, not a nice-to-have.**
Canonical time is resolved once and reused by every renderer (`delivery.py:115-130`); ZIP entries are written with fixed `date_time`, `external_attr`, and compression, sorted by archive name (`bundle.py:231-239`); `canonical_json_bytes` fixes indent, key order, and separators (`delivery.py:98-108`). `_verify_bundle` then re-renders each core format from the embedded `brief.json` and byte-compares (`verification.py:152-158`), so a hand-edited `brief.md` inside a bundle fails even if its manifest hash was updated. This is the property that makes independent download verification meaningful, and almost nothing else in this category has it.

**2. A truth vocabulary that is enforced, not decorative.**
`markdown.py:199-219` and `delivery.py:569-577` implement the status semantics as code, including the rule that `DONE` requires direct-or-derived passing proof. `_validate_evidence` (`markdown.py:153-170`) rejects any proof item without an inspectable locator and warns when the `[basis/result]` tag is missing. Evidence carries `basis` (direct/derived/reported) *and* `result` (pass/fail/info) as separate axes, which is the distinction most summarizers collapse.

**3. `docs/theory.md` — the most unusual asset in the repository.**
It cites Sweller, Chandler & Sweller, Cowan, Altmann & Trafton, Monk, Bailey & Konstan, Czerwinski, W3C PROV and SSML, and then explicitly refuses to over-claim: "This is a design hypothesis… It is not a claim that the complete Brief-Spec interaction has already been validated in a controlled human-subject study" (`docs/theory.md:37-39`); "It does **not** convert 'four' into a universal interface budget" (`:136-137`); §12 lists what would falsify the design. A design document that names its own falsification conditions is rare and is a credibility asset with reviewers, standards bodies, and enterprise buyers.

**4. Installation that behaves like a package manager, not a script.**
`install_runtimes` preflights every runtime as a dry run, snapshots every managed path, and restores all of them on any failure (`installers.py:946-975`). Hook files are *merged*, not replaced, and Brief-Spec's own entries are identified and removed by matching `brief-spec.pyz`/`briefspec.pyz` in the command string (`installers.py:432-449`). Uninstall removes a receipt-owned file only when its hash still matches, preserves files referenced by another receipt, and warns instead of deleting (`installers.py:1054-1062`). The Copilot cloud bridge is a deterministic stdlib-only zipapp with 1980-epoch timestamps (`bundle.py:26-65`) so a cloud job needs no network.

**5. Truth boundaries as an explicit, versioned artifact.**
`docs/verification.md` separates public release, source candidate, local deterministic gates, live-host, hosted CI, local artifacts, and PyPI into a table with per-row status, and records the *failing* Actions run rather than hiding it. `README.md:580-588` ("Honest limits") and the invariant list at `:456-475` do the same. The Grok row says "Hold" and explains why. Most projects would have written "verified" across that table. Protect this habit; findings F5 shows it has started to slip.

## Findings

Ordered by consequence.

### F1 — The classification release gate is circular; classification quality is unmeasured

- **Severity:** critical
- **Evidence label:** `[direct]`
- **Observation:** `docs/verification.md:41-42` states "The 160-prompt labelled corpus meets its macro and per-type F1 gates." The corpus is `tests/test_work_types.py:24-39`: eight sentence templates, each formatted with `index` in `range(1, 21)`. So the 160 prompts are 8 distinct sentences repeated 20 times with a changed integer. The templates are written from the classifier's own regex vocabulary — the exploration template is "Explore codebase module {index} and map its entry points and flow," and the exploration rules are `\b(?:explore|map|trace|orient|understand)\b` and `codebase|repository|repo …(?:works?|structured|flow|entry point)` (`work_types.py:198-206`). The gate is macro-F1 ≥ 0.95 and per-type F1 ≥ 0.90 (`tests/test_work_types.py:68-69`).
- **Why it matters:** This measures whether a regex matches the words the regex was written for, then multiplies the apparent sample size by 20. It cannot fail, and it cannot detect any real-world failure mode. Because the number "160-prompt labelled corpus … F1 gates" appears in the release evidence document, the circularity is laundered into something that reads like a quality measurement. Every downstream artifact — the typed marker, `classification` in the canonical object, the HTML eyebrow, the hook's injected guidance — inherits an unmeasured decision.
- **Recommended response:** Rename the existing test to what it is (`test_keyword_rules_match_their_own_vocabulary`) and stop citing it as classification quality anywhere. Build a real evaluation set of 300–500 *verbatim* prompts drawn from actual sessions and adversarial cases (multi-intent, negated, terse, non-native-English, non-English), labelled by two humans with disagreements recorded. Publish macro-F1, per-type F1, the confusion matrix, **and abstention rate**, and gate releases on a floor set from that set, not from templates.
- **What would verify:** A committed corpus file whose prompts are not derived from `_TYPE_RULES`, plus a CI job that reports the confusion matrix, and a demonstration that at least one plausible-but-wrong classification is now caught by the gate.

### F2 — The classifier reads prohibitions as intent and reports high confidence

- **Severity:** critical
- **Evidence label:** `[direct]`
- **Observation:** Three runtime observations from this session, produced by importing `briefspec.work_types` directly (no writes):
  1. The task prompt for *this review* — a request to review and explicitly **not** to implement — classifies as `implementation`, subject `pull-request`, confidence **`high`**, origin `inferred`, rules `['implementation.explicit', 'implementation.change', 'implementation.test', 'subject.pull-request']`. The matched words come from the prohibition block: "Do not **implement** your recommendations. Do not **modify** product code, documentation, **tests**, schemas, or **configuration**. Do not commit, push, tag, publish, fork, open a **pull request**…"
  2. `"Do not open a pull request. Just explain the config format."` → `review` / `pull-request` / `medium`.
  3. The same task, as actually classified by the live Brief-Spec hook in this session, was reported to me as `general + pull-request (low, fallback)` — a different wrong answer, because at full prompt length several rule families tie and `classify_task` falls back (`work_types.py:334-340`). The subject `pull-request` still comes from the prohibition.
  Separately, `confidence` is `high` whenever two or more rules in one family match (`work_types.py:344-348`), and the implementation family alone contains `implement|build|create|write|add|remove|refactor`, `change|update|modify|patch|migrate|configure|install`, and bare `fix` — so two hits is nearly free. Subject selection is first-match-wins over a fixed-priority list (`work_types.py:215-231`, `:355-359`), which is why `pull-request` always wins.
- **Why it matters:** This is the one failure mode Brief-Spec's own invariant list forbids. `README.md:464` — "Unknown or unverified state is a gap, not a reason to infer success." A `confidence=high` label on a guess derived from negated text is exactly an inferred success. It is also user-visible: the hook injects "Brief-Spec classified this task as X + Y" into the model's context and instructs it to keep that type stable, so a wrong classification actively shapes the response the human reads, and the wrong subject is stamped into the delivery's HTML header and canonical JSON.
- **Recommended response:** Three changes, in order. (a) **Abstain by default:** require a minimum margin over the runner-up family, not just a unique maximum, and emit `general/low/fallback` otherwise — a wrong-but-confident type is worse than no type. (b) **Calibrate:** never emit `high` from inferred rules alone; reserve `high` for `explicit` and `host` origins, cap `inferred` at `medium`. (c) **Handle negation and scope:** classify only the imperative/request span, and drop matches inside a negation window (`do not …`, `don't …`, `avoid …`, `never …`) or at minimum treat any negated match as a signal *against* that family. Also stop letting a fixed subject priority list override rule proximity.
- **What would verify:** An adversarial slice of the F1 corpus containing prohibition-heavy prompts, with the acceptance criterion that they classify as `general/fallback/low` or correctly, never as a confident wrong type; plus re-running the three cases above and observing the change.

### F3 — Zero human evidence for the product's central claim

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** `pilots/apex/` defines exactly the right study: five questions, a cohort of 5–10 sessions, and numeric success criteria — status and action identifiable in ≤15s, proof locatable in ≤30s, comprehension ≥4/5, checkpoint helpfulness ≥4/5 (`pilots/apex/config.toml`). `results-template.json` is a template with every field `null`, and the README says a human "can then record timing and comprehension observations in an untracked copy." `scripts/run-pilot.py` (38 lines) validates that the fixture files satisfy the Markdown contract — it measures format compliance, not humans. No results file exists in the repository or in the ignored `.briefspec/` tree. `docs/theory.md:37-39` concedes the point.
- **Why it matters:** Every design decision — the seven fields, that order, five proof items, three next actions, three checkpoint modes, the 80–240 word spoken script, the 12-minute/8-turn thresholds — is justified by a reading-cost argument that has never been tested on a reader. Five versions of engineering have gone into the delivery machinery; the study that would tell you whether the premise holds costs perhaps two days and five colleagues. If the premise is weak, the correct roadmap is very different from the current one.
- **Recommended response:** Run Apex as specified before writing another feature. Five to ten engineers, two conditions minimum (raw agent output vs Brief-Spec handoff) over the same underlying work, measuring time-to-status, time-to-action, time-to-proof, **wrong-status rate** (did the reader believe something was done that was not?), and evidence-open rate. Publish the numbers including the bad ones, in a `docs/pilot-apex-results.md` with the same truth-boundary discipline as `verification.md`.
- **What would verify:** A committed results file with per-session raw numbers, the cohort size, the protocol, and an explicit statement of what the sample size cannot support.

### F4 — Classification metadata in the canonical object is unauthenticated model-copied text

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** The typed wrapper is a comment the model writes: `<!-- brief-spec:typed:v1 type=… subject=… confidence=… origin=… classified_at=… profile=1.0 -->`. `parse_typed` (`markdown.py:271-328`) lifts `confidence` and `origin` straight out of that comment into the `classification` dict and hard-codes `"rule_ids": []`. The stop hook's `typed_valid` check compares only `work_type` and `subject` against session state (`hooks.py:178-182`) — `confidence` and `origin` are never checked. `validate_delivery` only checks enum membership (`delivery.py:505-513`). Confirmed downstream: the live Claude smoke run's canonical classification is `{"confidence": "high", "origin": "inferred", "rule_ids": [], …}` (`.briefspec/live-e2e/0.5.0-smoke-claude-review/claude/review-teach/result.json`).
- **Why it matters:** Any agent can emit `origin=explicit confidence=high` on a pure guess and every Brief-Spec validator will accept it, at every verification level, in the one artifact whose entire premise is that a presentation object never becomes more authoritative than its source. It is the same class of error the project polices everywhere else: a self-reported label presented as a provenance field. The empty `rule_ids` also means the audit trail of *why* a type was chosen is destroyed at exactly the boundary where the object becomes portable.
- **Recommended response:** Make the hook the sole author of classification. Have it write a small session-scoped classification record (type, subject, confidence, origin, `rule_ids`, `classified_at`, and a keyed digest over them); require the typed marker to carry only an opaque reference to that record; have `load_delivery` resolve and substitute the authoritative values, and downgrade to `origin=reported, confidence=low` when the record is unavailable. Preserve `rule_ids` into the canonical object. Add `basis` semantics to `classification` so a model-asserted type is visibly `reported`.
- **What would verify:** A test that takes a handoff whose typed marker claims `origin=explicit confidence=high` while the session record says `fallback/low`, and asserts the canonical delivery carries `fallback/low` (or `reported`) and that `brief-spec validate --strict` warns.

### F5 — The truth boundary has drifted from its own record

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** Three specific drifts at the inspected commit.
  1. `docs/verification.md:124` lists as an *open external prerequisite*: "Rename the GitHub repository to `brief-spec` only after local and hosted gates pass." The GitHub API reports `full_name: luanmorenommaciel/brief-spec` — the rename has already happened, and `pyproject.toml:36-38`, all four plugin/marketplace manifests, and `docs/installation.md:140-157` already point at the new name. Hosted gates have not passed (F7).
  2. `docs/verification.md:13` describes the 0.5.0 candidate as "This uncommitted working tree" and `:71-73` explains that "Because this is an uncommitted source candidate, its local manifest intentionally does not claim a source revision." The candidate is committed and pushed: `4adf204` on `main`, 2026-08-13T14:05:31Z. A source revision now exists.
  3. `CHANGELOG.md:122-128` compare links point at `github.com/luanmorenommaciel/brief-spec/compare/v0.2.0...v0.5.0`; `v0.5.0` does not exist as a tag, so those links are dead.
- **Why it matters:** The truth-boundary table is Brief-Spec's most differentiating claim and its main credibility asset. A stale boundary table is worse than none, because readers have been trained to trust it. It also demonstrates the general problem: these boundaries are maintained by hand in prose, so they drift silently.
- **Recommended response:** Make the boundary machine-checked. Extend `scripts/verify-release.py` with a `--truth-boundary` mode that asserts, against `git` and the GitHub API: the claimed candidate state matches whether the tree is committed; every version referenced in docs has a corresponding tag or is explicitly marked unpublished; every "open prerequisite" that has in fact been completed fails the check; and every CHANGELOG compare link resolves. Wire it into the release job. Then refresh `docs/verification.md` for the committed state.
- **What would verify:** A CI job that fails on the current commit for reasons 1–3, and passes after the record is corrected.

### F6 — The distribution path is closed; a second party cannot obtain or run this

- **Severity:** high
- **Evidence label:** `[direct]`, `[external]`
- **Observation:** The repository is `"visibility": "private"` with 0 stars, 0 forks, 0 external issues, discussions disabled, and 6 closed issues all authored by Dependabot. `README.md:35` and `docs/installation.md:21` instruct users to run `uv tool install git+https://github.com/luanmorenommaciel/briefspec.git@v0.2.0` — a private repository under its former name. `docs/installation.md:140` documents `codex plugin marketplace add luanmorenommaciel/brief-spec --ref v0.5.0`; that ref does not exist. All three PyPI names return HTTP 404 (`brief-spec`, `briefspec`, `brief-spec-renderer-pdf`, `brief-spec-renderer-audio`), so nothing is published and nothing is reserved. Externally, the ecosystem this wants to join is moving fast and in public: Agent Skills has ~40 adopting tools, Agent Plugins 1.0 landed 2026-08-06, and MCP/goose/AGENTS.md are governed by the Linux Foundation's Agentic AI Foundation with 150+ members and eight platinum members including Anthropic, OpenAI, Google, Microsoft, AWS, and Block.
- **Why it matters:** "Cross-harness standard" and "private repository, unpublished package, zero external users" cannot both be true. There is currently no way for anyone to validate, criticize, extend, or adopt the contract, which means the standards thesis has accumulated exactly zero evidence across five versions. The names are also unclaimed, so a third party can take `brief-spec` on PyPI at any time.
- **Recommended response:** Sequence it deliberately, not all at once. (a) Reserve the three PyPI names now via Trusted Publishing to a placeholder `0.0.0` — this is cheap and removes a real squatting risk. (b) Fix every documented install command to reference a name and ref that exist. (c) Make the repository public at the same moment a tag exists that the docs point to, so the first external visitor's first command works. Do not go public with install instructions that 404.
- **What would verify:** From a clean machine with no access to this account: the exact command in `README.md` succeeds, `brief-spec --version` prints the documented version, and `brief-spec doctor all --probe` runs.

### F7 — Hosted CI has never executed for this candidate; all evidence is one machine

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** CI run `31708342030` on `4adf204` (2026-08-13T14:05:36Z) is a `failure` in which **every job was rejected before execution**. All 17 matrix jobs completed in 2–5 seconds with the annotation "The job was not started because recent account payments have failed or your spending limit needs to be increased"; `Build and clean-room installation` was skipped. The previous main-branch run `31516322113` (2026-08-11) failed identically. `docs/verification.md:15-24` documents this honestly. The consequence is that the matrix `ci.yml` defines — Ubuntu, macOS, **Windows** × Python 3.11/3.12/3.13/3.14, the Codex/Claude plugin validators, the Windows Codex project-hook regression, the Linux PDF/Chromium job, and the macOS audio job — has produced no evidence for 0.5.0. The passing evidence is `docs/verification.md:28-36`: one macOS machine on Python 3.13.
- **Why it matters:** The Windows exposure is concrete, not theoretical. `installers.py` contains Windows-only code paths that only that matrix exercises: `_codex_project_powershell_command` (`:285-300`) and `_powershell_command` (`:303-326`) build PowerShell invocations with hand-rolled single-quote escaping, and `ci.yml:77-97` exists specifically to run the nested-directory Codex hook regression on `windows-latest`. None of it has run for this candidate. More broadly, a release process this carefully staged is gated on a billing setting, which is a single point of failure sitting outside the engineering work.
- **Recommended response:** Restore Actions billing and re-run the full matrix on the exact candidate revision before any tag. If billing cannot be restored quickly, that is a strategic fact, not a delay: run the matrix on a free public-repository allowance (which requires F6's public step) or a self-hosted runner, and state in `verification.md` which platforms have *never* been tested for this candidate rather than leaving the reader to infer it from a "Blocked" row.
- **What would verify:** A green `CI` run on the tagged revision with all matrix legs `success`, linked from `docs/verification.md`.

### F8 — The schemas cannot function as a standard: unresolvable `$id`s, split namespace, and a second hand-written validator

- **Severity:** high
- **Evidence label:** `[direct]`, `[external]`
- **Observation:** Four compounding problems. (a) Both `$id` hosts are unregistered: `nslookup brief-spec.dev` and `nslookup briefspec.dev` both return **NXDOMAIN**. (b) The namespace is split mid-rename — canonical files use `https://brief-spec.dev/schemas/…` while `outcome-brief`, `session-checkpoint`, `evidence`, and the legacy delivery/receipt/manifest files use `https://briefspec.dev/schemas/…`. (c) The canonical `brief-spec-delivery.schema.json:103-104` `$ref`s **absolute** URLs on the *other*, non-existent host, whereas the legacy `briefspec-delivery.schema.json:35-36` uses relative refs. So the canonical 2.0 schema is strictly *less* portable than the 1.0 schema it supersedes; it resolves only because `tests/test_schema_contracts.py:20-38` builds a local `referencing.Registry` keyed by `$id`. (d) `grep -rn "jsonschema" src/` returns nothing: the schemas are never used at runtime. Enforcement is a second, hand-written implementation in `delivery.py:436-662` and `markdown.py`.
- **Why it matters:** The schemas are the only artifact a second implementer would consume, and today a stranger with a standard JSON Schema validator cannot resolve them. Two independent validators (JSON Schema and hand-rolled Python) will drift, and the Python one is authoritative in practice while the JSON one is what you would publish as "the standard." External context makes this the highest-leverage gap: Agent Plugins 1.0 explicitly states it "defines no permission model, no sandboxing, no signature checks," and commentary on the 2026 ecosystem summarizes it as portability solved in eight months while "verification systems remain organizational problems with no assigned owner." Brief-Spec has the verification design and is failing to ship it in a form anyone can implement against.
- **Recommended response:** (a) Register one namespace and use it for every file, or switch entirely to relative `$ref`s plus a documented local registry so resolution never depends on DNS. (b) Publish a **conformance test-vector suite**: a directory of golden canonical objects, malformed variants, and expected verdicts per verification level, so a TypeScript or Go implementation can prove semantic equivalence without reading the Python. (c) Generate one validator from the other, or add a differential test that fuzzes objects and asserts the JSON Schema and Python validators agree — a disagreement should fail CI. (d) Once the vectors exist, contribute the delivery/receipt schema to AAIF as the verification layer that Agent Plugins deliberately left out.
- **What would verify:** A third-party validator (`ajv`, `check-jsonschema`) validating a canonical object from the repository with no local ref rewriting, plus a differential test in CI, plus one non-Python implementation passing the vectors.

### F9 — Four hand-rolled plugin manifests, none conformant with the standard that now exists

- **Severity:** medium
- **Evidence label:** `[direct]`, `[external]`
- **Observation:** The repository maintains `plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, plus three marketplace manifests (`.claude-plugin/`, `.github/plugin/`, `.agents/plugins/`) with overlapping content. Agent Plugins Specification v1.0.0 §5.3 requires exactly two fields in the manifest: `$schema` (must equal `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`) and `name`. **None of the three `plugin.json` files declares `$schema`**, so none is a conformant Agent Plugin.
- **Why it matters:** This is the layer being commoditized. Brief-Spec is spending maintenance on per-host manifests at the moment the ecosystem standardized packaging, and it is not getting the interoperability benefit — a conformant plugin is discoverable by every conformant client, while these are discoverable only by the hosts someone hand-coded. Adding the field is nearly free; the real win is deleting bespoke manifests.
- **Recommended response:** Add `$schema` to the root `plugin.json` and validate it against the published schema in `verify-release.py`. Then test whether the per-host manifests are still necessary for the hosts you actually support, and delete the ones that are not. Keep host-specific *interface* metadata (Codex's `interface` block) only where a host genuinely reads it.
- **What would verify:** `check-jsonschema --schemafile https://agent-plugins.org/schemas/1.0.0/plugin.schema.json plugin.json` passing in CI, and at least one host installing from the conformant manifest with no host-specific file present.

### F10 — Renderer entry points are an unguarded code-execution surface inside `verify`

- **Severity:** medium
- **Evidence label:** `[direct]`
- **Observation:** `available_renderers()` (`renderers.py:25-38`) iterates entry points in the groups `briefspec.renderers` and `brief_spec.renderers` and calls `entry_point.load()` — importing and instantiating code from **any** installed distribution that advertises either group. There is no name allowlist, no version compatibility check, and no signature check. It is called from `verify_target` for `.pdf`/`.mp3` targets and from `_verify_bundle` whenever `rendered=True` (`verification.py:182`, `:377-378`), so `brief-spec verify bundle.zip --level rendered` — the "prove this download is trustworthy" command — imports third-party code as a side effect. `README.md:577` states "The package has no runtime dependencies," which is true of the core and not of this path.
- **Why it matters:** The threat model is real for this product: a bundle arrives from elsewhere, the recipient runs `verify --level rendered` precisely *because* they do not trust it, and that command loads whatever renderer plugins happen to be installed. Nothing here is exploitable by the bundle itself, but the trust boundary is inverted relative to the command's purpose, and the security posture is weaker than the surrounding code's standard.
- **Recommended response:** Load only entry points whose names are in an explicit allowlist (`pdf`, `audio`) and whose distribution version matches the core's, refusing others with a visible diagnostic rather than silently. Document in `SECURITY.md` that installing a renderer is a trust decision equivalent to installing a dependency. Consider a `--no-plugins` flag so `verify` can run with a guaranteed-minimal surface, and record in the receipt which renderer versions participated (the receipt already carries `renderer_versions`).
- **What would verify:** A test installing a distribution that registers a hostile-named entry point in the group, asserting it is not loaded and that a diagnostic is emitted; plus `verify --no-plugins` succeeding on a core-only bundle.

### F11 — A documented install-safety promise contradicts the installer

- **Severity:** medium
- **Evidence label:** `[direct]`
- **Observation:** `docs/installation.md:174-176` promises: "Brief-Spec-owned assets are refreshed; foreign **or locally modified** files cause a conflict instead of being overwritten." `installers.py:96-102` raises `InstallConflict` only when the target differs **and** (`name not in {"SKILL.md", "openai.yaml"}` **or** the file lacks a Brief-Spec marker) **and** the content does not match a receipt hash. For a locally edited `SKILL.md` that still contains `<!-- brief-spec:skill:v1 -->`, both branches of that middle clause are false, so no conflict is raised and the edit is silently overwritten. `_owned_marker` (`:43-52`) matches the bare substrings `brief-spec:` and `briefspec:`, so any file mentioning the project is treated as owned. Uninstall *does* honor modification (hash check at `:1056-1059`), which is likely the source of the confusion.
- **Why it matters:** Customizing a `SKILL.md` is the single most likely local modification a user will make, and it is destroyed by a routine upgrade with no warning and no backup. The generic ownership marker also means a user's own note that quotes `brief-spec:` becomes overwritable. This undercuts the trust the installer otherwise earns.
- **Recommended response:** Decide which promise you mean and make code and docs agree. The better behavior: on upgrade, if a marker-bearing skill file differs from both the shipped content and its receipt hash, write the new version to `SKILL.md.new`, keep the user's file, and report it as a warning in the operations list and in `doctor`. Replace the substring-marker heuristic with a structured owned-file marker that includes the version and receipt id.
- **What would verify:** A test that edits an installed `SKILL.md`, re-runs `setup`, and asserts the edit survives and a warning is reported; and `docs/installation.md` restated to match.

### F12 — Operator-precedence bug in runtime auto-detection

- **Severity:** medium
- **Evidence label:** `[direct]`
- **Observation:** `cli.py:37-41`:
  ```python
  if (
      any(name.startswith("CLAUDE_CODE") for name in os.environ)
      or os.environ.get("CLAUDE_PLUGIN_ROOT")
      and not os.environ.get("CODEX_THREAD_ID")
  ):
      return Runtime.CLAUDE
  ```
  `and` binds tighter than `or`, so this evaluates as `CLAUDE_CODE* or (CLAUDE_PLUGIN_ROOT and not CODEX_THREAD_ID)`. The `CODEX_THREAD_ID` guard — clearly written to prevent misdetection — never applies to the first condition.
- **Why it matters:** Reached via `hook --provider auto`, which is exactly what the native plugin hooks use (`hooks/hooks.json` passes `--provider auto`). A Codex session started from an environment where any `CLAUDE_CODE*` variable is exported gets `Runtime.CLAUDE`: the wrong session-state bucket (`state.py:80-86` keys sessions on `runtime` + session id), the wrong output shape in `render_decision`, and misleading `harness` metadata in the delivery. Nested and cross-harness sessions are a first-class Brief-Spec use case, so this is likely to fire in the field.
- **Recommended response:** Parenthesize to `(A or B) and not C`, or restructure into explicit sequential checks with a stated precedence order. Add a test matrix over the detection environment variables including the both-present case, and prefer an explicit `runtime`/`provider` field in the payload over environment sniffing wherever a host supplies one.
- **What would verify:** A parametrized test asserting that `CLAUDE_CODE_ENTRYPOINT` plus `CODEX_THREAD_ID` resolves to `codex`.

### F13 — The rename is only partly done, and the compatibility surface is now doubled

- **Severity:** low
- **Evidence label:** `[direct]`
- **Observation:** `BRIEFSPEC_STOP_HOOK_ACTIVE` has no canonical counterpart (`adapters/base.py:159`) — every other state variable was renamed. `hooks/hooks.json` invokes `scripts/briefspec-hook`, the legacy entrypoint, in the *native plugin* path. Renderer package directories are still `packages/briefspec-renderer-{pdf,audio}` while their distribution names are `brief-spec-renderer-*`. `schemas/` carries six files where three would do (canonical + legacy delivery, receipt, manifest), with the inner brief schemas left on the old namespace. `README.md:394` calls the config block "the complete v0.1 policy surface" at version 0.5.0, and lists the sections in a different order than `config_template()` emits. Internal source packages remain `src/briefspec/` (canonical) with `src/brief_spec/` as a 15-line forwarder — the inverse of the stated canonical direction.
- **Why it matters:** Individually trivial; collectively this is the tax the whole `0.x` line now pays. Every reader must hold two vocabularies, and each half-renamed item is a place where a future contributor guesses wrong. It also makes the `1.0` cut harder to specify than it needs to be.
- **Recommended response:** Write the deprecation table now — every legacy interface, its canonical replacement, and the version that removes it — and add the missing canonical alias for the stop-hook variable. Point the native plugin hooks at `scripts/brief-spec-hook`. Rename the renderer directories. Do not delete anything before `1.0`; do decide, in writing, what `1.0` drops.
- **What would verify:** A `docs/compatibility.md` deprecation table plus a `verify-release.py` check that every legacy interface listed there is still functional and every canonical interface exists.

### F14 — The harness registry is twelve positional booleans

- **Severity:** low
- **Evidence label:** `[direct]`
- **Observation:** `harnesses.py:128-278` constructs each `HarnessAdapter` with twelve consecutive positional `bool` arguments (`user_scope` through `model_metadata`). The Codex entry, for example, is `True, True, True, True, True, True, True, False, True, True, True`.
- **Why it matters:** `capabilities()` output is a published product claim about what each host supports, consumed by `doctor` and documented in `docs/compatibility.md`. One transposed flag silently changes an advertised capability with no compiler or reviewer able to catch it, and there are eight adapters × twelve flags to keep aligned with reality.
- **Recommended response:** Use keyword-only fields (`@dataclass(frozen=True, slots=True, kw_only=True)`) and convert every call site. Consider moving the registry to a data file, which is what `docs/compatibility.md:3` already calls it ("data-driven harness adapter registry").
- **What would verify:** `kw_only=True` on the dataclass, all call sites named, and a test that cross-checks each adapter's advertised capabilities against the compatibility table in the docs.

## Ten opportunities

| # | Opportunity | User impact | Strategic leverage | Evidence confidence | Effort | Risk | Horizon |
|---|---|---|---|---|---|---|---|
| 1 | **Honest classifier**: abstain on low margin, cap inferred confidence at `medium`, drop matches inside negation windows, classify only the request span (F2) | 5 | 4 | 5 | M | low | next release |
| 2 | **Real classification eval**: 300–500 verbatim + adversarial prompts, two-rater labels, published confusion matrix and abstention rate as the release gate (F1) | 4 | 5 | 5 | M | low | next release |
| 3 | **Bind classification to the classifier**: hook-authored session record + keyed digest; typed marker carries only a reference; `rule_ids` preserved into the canonical object (F4) | 4 | 5 | 5 | M | medium | next release |
| 4 | **Run the Apex pilot**: 5–10 engineers, two conditions, publish time-to-status/action/proof and wrong-status rate including negative results (F3) | 5 | 5 | 5 | S | low | next release |
| 5 | **Conformance test-vector suite + resolvable schema namespace**: golden objects, malformed variants, expected verdicts per level; one namespace, resolvable refs (F8) | 3 | 5 | 5 | M | low | later `0.x` |
| 6 | **Machine-checked truth boundary**: `verify-release.py --truth-boundary` asserting doc claims against git, tags, and the GitHub API; fails when a documented open prerequisite is already done (F5) | 3 | 4 | 5 | S | low | next release |
| 7 | **Open the distribution path**: reserve the three PyPI names, fix every install command to a name/ref that exists, then go public in the same change (F6) | 5 | 5 | 5 | S | medium | next release |
| 8 | **Restore hosted CI and publish the platform matrix**, especially Windows and Python 3.14; state explicitly which platforms are untested (F7) | 4 | 4 | 5 | S | low | next release |
| 9 | **Agent Plugins 1.0 conformance**: add `$schema`, validate in CI, then delete every bespoke manifest a supported host does not actually read (F9) | 2 | 4 | 4 | S | low | later `0.x` |
| 10 | **Cross-harness semantic equivalence as a shipped command**: `brief-spec equivalence a.json b.json` proving two hosts produced semantically identical canonical objects for the same task, with a documented equivalence relation | 3 | 5 | 3 | L | medium | `1.0` |

## Three highest-conviction bets

### Bet 1 — Make classification honest before making it better

**Why it dominates.** It is the only issue that is simultaneously critical, cheap, and self-inflicted. Opportunities 1–3 together are maybe two weeks, and until they land, every other investment compounds a defect: the wrong type shapes the model's response, the wrong subject lands in the HTML header, and an unverifiable `confidence=high` sits inside the artifact whose entire value proposition is that it does not over-claim. Publishing, standardizing, or adding harnesses on top of this makes the problem harder to retract, because each one creates a consumer of the bad field. Every other opportunity also gets easier once the classifier can say "I don't know."

**User problem.** A reviewer asks for a review and receives an implementation-shaped explanation, labelled high-confidence, because the prompt contained the word "implement" inside a prohibition. The user cannot tell that the label is a guess.

**Measurable outcome.** On the new adversarial slice: zero confidently-wrong classifications (defined as `confidence=high` with a wrong `work_type`); abstention rate reported rather than minimized; macro-F1 on verbatim prompts published with its confusion matrix; and 100% of canonical deliveries carrying a `classification` block that the tooling can trace to a hook-authored record or that is visibly marked `reported`.

**Must be true first.** You must accept that abstention is a success state — that `general/fallback/low` on an ambiguous prompt is the correct answer, not a coverage failure. If the product goal is "always pick a type," this bet is incoherent and the contrarian bet below applies instead.

### Bet 2 — Make Brief-Spec obtainable and implementable by a second party

**Why it dominates.** The standards thesis has zero evidence after five versions for one structural reason: no one outside this account can get the software. Opportunities 5, 7, 8, and 9 are one program — reserve the names, fix the install commands, go public with a tag that exists, restore CI, publish resolvable schemas and conformance vectors. The external timing is unusually favorable and will not stay that way: Agent Skills and Agent Plugins 1.0 standardized portability across ~40 tools in eight months and explicitly excluded trust, provenance, signing, and verification; AAIF exists with 150+ members and no owner for the verification layer. Brief-Spec has a working, deterministic, receipt-backed answer to exactly that. Test vectors, not a Python package, are what let someone else implement it — and a second implementation is the only thing that converts a tool into a standard.

**User problem.** A team on a harness Brief-Spec does not support, or in a language other than Python, has no way to produce or check a conformant delivery.

**Measurable outcome.** From a clean machine with no privileged access: the README command succeeds and `doctor --probe` passes. A green CI matrix on the tagged revision. A third-party JSON Schema validator resolving the canonical schema with no local rewriting. At least one non-Python implementation passing the conformance vectors. Then, as the real signal: one external contributor or adopter who is not the author.

**Must be true first.** You must be willing to receive public criticism of an 0.x candidate, and to freeze `brief-spec-delivery/2.0` semantics enough that vectors mean something. If the schema is still moving weekly, publish vectors as `2.0-draft` and say so.

### Bet 3 — Get human evidence for the reading claim, and publish it even if it is bad

**Why it dominates.** Opportunity 4 is the cheapest high-consequence action available — the study is already designed with numeric thresholds; what is missing is five colleagues and two days. Every roadmap decision downstream depends on the answer, and `docs/theory.md:351-371` already names the falsification conditions, so the project has pre-committed to caring. If time-to-action improves materially, that number is the strongest marketing and standards argument the project will ever have. If it does not, you learn it now instead of after `1.0`, and the correct pivot is likely toward the verification layer alone (see the contrarian bet).

**User problem.** Nobody, including the author, knows whether Brief-Spec reduces the reading cost it was built to reduce.

**Measurable outcome.** A committed results file with per-session raw numbers against the pre-registered thresholds: status and action identified in ≤15s, proof located in ≤30s, comprehension ≥4/5, checkpoint helpfulness ≥4/5 — plus wrong-status rate and evidence-open rate for both conditions, and an explicit statement of what n=5–10 cannot support.

**Must be true first.** Pre-register the thresholds and the analysis before collecting data (they already exist in `pilots/apex/config.toml`, so this is free), and commit to publishing negative results. A pilot run after the fact, or reported selectively, is worth less than no pilot.

## One contrarian bet

**Remove automatic work-type classification from the default path. Ship the eight profiles as explicitly-invoked prompts, and make the delivery/verification layer the product.**

Concretely: `typing.activation` defaults to `explicit` instead of `substantive`; the hook injects a classification only when the user or host names a type; the eight profiles stay in `skills/brief-spec/references/` as things the router reads when asked. The regex inference engine stops running by default.

**The strongest argument for it.** Classification is the newest, least defensible, and most damaging component. It has no measured accuracy (F1), it is confidently wrong on realistic prompts including this review's own request (F2), and it injects an unverifiable provenance field into the one artifact sold on never over-claiming (F4). Meanwhile the delivery layer is excellent and completely independent of it — determinism, manifests, receipts, and four verification levels do not need to know whether the task was a review or an implementation. The external landscape says the same thing from the outside: portability and packaging are solved and governed; trust and verification are explicitly out of scope everywhere and have no owner. Brief-Spec's defensible position is "the layer that proves an agent's claim," not "the layer that guesses what kind of work you asked for." Removing the guess costs one config default and makes every remaining claim honest. There is also a second-order benefit: the profiles are probably *more* useful when a human chooses them, because a human choosing "explain this as a review" is stating an intent the regex can only approximate.

**The strongest argument against it.** Typing is the entire 0.5.0 release — `brief-spec-delivery/2.0`, the typed wrapper, `types`/`classify`, the universal router skill, and eight profiles all exist to serve it. Retreating to explicit activation is a visible walk-back of the headline feature and would strand the `classification` block as a mostly-empty required field in a schema you want others to implement. More seriously, opt-in features in agent harnesses have a well-known failure mode: users forget they exist. Automatic routing is what makes the type-aware explanation happen at all, and the hook-injected guidance is the mechanism by which a human ever sees the benefit. An explicit-only default may reduce the feature's real-world usage to approximately zero, at which point the honest move is to delete it rather than demote it. The counter-counter is that this is precisely what an experiment settles.

**Evidence needed to decide.** Add a third arm to the Apex pilot: (a) auto-routed typing on, (b) explicit-only typing, (c) untyped Outcome Brief. Same underlying work, same readers, measuring time-to-action, wrong-status rate, and — critically — whether readers in arm (a) ever notice a misclassification. Two numbers decide it: if auto-routing beats explicit-only on time-to-action by a margin larger than the misclassification rate costs in wrong-status, keep it on by default and fix the classifier. If auto-routing produces *more* wrong-status than untyped output, it is a net negative regardless of its speed benefit, and demotion becomes the conservative choice. Pair this with the classifier's measured accuracy from Bet 1; if honest calibration pushes the abstention rate above roughly a third of real prompts, automatic routing is not carrying its weight and the contrarian path wins on the arithmetic alone.

## What not to build

- **More harness adapters.** Copilot, Cursor, and Goose are already `experimental` with no live gates, and the five `verified` hosts have no hosted-CI matrix (F7). A ninth adapter adds maintenance and dilutes the meaning of the maturity column. The right move is to finish proving five, not to start a sixth.
- **A hosted Brief-Spec service, dashboard, or registry.** It would invert the architecture's best property — everything is local, network-free, and dependency-free — and immediately create the data-retention and auth surface the project currently, correctly, does not have. `README.md:471` explicitly promises the Copilot cloud path needs no runtime download; a service breaks that promise's spirit.
- **Deeper audio and PDF.** SSML sophistication, voice selection, multi-provider TTS, PDF theming. The renderers already exist and already exceed demonstrated demand; there is not one human data point saying anyone listened to a Spoken Brief. Revisit only if the Apex pilot shows the spoken mode is used.
- **Any knowledge-graph, memory, or ingestion feature.** `docs/theory.md:320-349` argues against it better than I can, and `README.md:474` makes it an invariant. This boundary is a strategic asset; the temptation will come from users asking for search over past briefs. The answer is explicit promotion into a system that already does that.
- **A model-based classifier, or any classifier that makes a network call.** `README.md:150-151` and `skills/brief-spec/SKILL.md` promise local, bounded, no-network classification. Solving F1/F2 with an LLM call would trade a measurable defect for an unmeasurable one and break the promise. Fix the rules and add abstention.
- **Custom primary work types.** `types_document()` already returns `"custom_primary_types": false` — hold that line. Eight types with an open subject slug is the right factoring; user-defined primary types would fragment the one thing that has to be stable for cross-harness equivalence to mean anything. Subjects are the extension point.
- **Enforce-by-default lifecycle policy.** `docs/configuration.md:57-58` is right that a stop hook cannot infer every terminal boundary. Blocking a stop by default on a heuristic (`looks_like_action_request`, `triggers.py:16-20`) would make Brief-Spec the reason someone's agent felt broken. `suggest` is the correct default.
- **A marketplace or plugin ecosystem for Brief-Spec itself.** There is one renderer plugin group and it is already an unguarded code-execution surface (F10). Do not widen it before it is hardened, and probably not at all.

## Proposed next-release steel thread

**Thesis to prove:** *a Brief-Spec classification is either trustworthy or visibly absent — and a reader can verify which, from the artifact alone.*

One bounded increment. `0.6.0`.

**User scenario.** An engineer in Claude Code asks: "Review this pull request for merge risk, but don't change any code." Brief-Spec classifies it as `review + pull-request`, explains the work with the review profile, and closes with a typed Outcome Brief. The engineer then asks a deliberately ambiguous follow-up — "figure out what's going on with the deploy and clean it up" — and Brief-Spec **abstains**: the handoff says `general`, `origin=fallback`, `confidence=low`, and the reader can see it was a fallback rather than a decision. Both handoffs export to a bundle; `brief-spec verify --level rendered` reports for each whether the classification is hook-attested or model-reported.

**Entry point.** No new command. The existing `UserPromptSubmit` hook plus the existing `brief-spec classify` and `export`/`bundle`/`verify` commands. One new flag: `brief-spec classify --explain`, printing the matched rules, the runner-up family, and the decision margin.

**Classification behavior.** (a) Margin rule: a family wins only if it exceeds the runner-up by at least one matched rule; ties and near-ties yield `general/fallback/low`. (b) Negation windows: a rule match inside a `do not | don't | never | avoid | without | instead of` span up to the next sentence boundary does not count toward its family, and does not seed the subject. (c) Calibration: `high` is reserved for `explicit` and `host` origins; `inferred` caps at `medium`. (d) Subject: chosen from rules matched in the winning family's span, not from a global priority list; `general` when none applies.

**Explanation behavior.** Unchanged profiles and ordering. One addition: when `origin` is `fallback`, the router uses the `general` profile and the injected hook guidance says so plainly — "Brief-Spec could not determine a work type; explain as general" — instead of asserting a type. This is the whole point: absence must be legible.

**Canonical data changes.** Additive within `brief-spec-delivery/2.0`; no breaking change, no migration cost. `classification` gains `basis` (`attested` | `reported`) and keeps a populated `rule_ids` array. `classification.attestation` (optional object: `session_ref`, `digest`) is present when the hook authored the record. `load_delivery` resolves the typed marker against the session record when available and substitutes the authoritative values; when unavailable it sets `basis=reported` and downgrades `confidence` to `low`, adding a warning. A delivery whose marker claims `origin=explicit` with no attestation validates but is visibly `reported`.

**Download or delivery changes.** No new formats. `render_html` shows the classification eyebrow with an explicit `attested`/`reported` qualifier. The bundle manifest records `classification_basis`. `verify --level structural` gains one check, `classification attestation`, reporting `PASS` (attested and digest matches), `WARN` (reported), or `FAIL` (attestation present but digest mismatched) — following the existing convention that unresolved evidence warns rather than passes.

**Harnesses involved.** Claude Code and Codex only, both scopes. No adapter changes; no new host. OMP, Grok, and Kimi inherit the core behavior without new integration work, and no claim is made about them in this release.

**Security and privacy boundary.** Unchanged and re-asserted. The attestation digest is keyed by a per-installation secret stored in the private state root (mode `0600`, `atomic_write`) — it proves *this installation's hook* authored the classification, not identity, and it is not a signature for third parties. **No prompt text, no rule-matched substrings, and no assistant text enter the record or the digest input** — only the fields already stored in `SessionState` (`work_type`, `subject`, `confidence`, `origin`, `rule_ids`, `classified_at`). Nothing new is written into any exported artifact beyond the enum values and an opaque reference. `--explain` prints to the terminal and persists nothing. No network calls anywhere in the thread; hooks continue to fail open.

**Automated tests.**
1. Adversarial prompt slice (≥60 verbatim prohibition-heavy, multi-intent, and terse prompts) asserting **zero** `confidence=high` wrong classifications, with the three cases from F2 as named regressions.
2. Negation-window unit tests, including a negation followed by a genuine request in the same prompt.
3. Margin-rule tests: exact tie, one-rule margin, and confirmation that abstention emits `general/fallback/low`.
4. Attestation round trip: hook classifies → model emits marker → `load_delivery` produces `basis=attested` and matching `rule_ids`.
5. Forgery test: marker claims `origin=explicit confidence=high` while the record says `fallback/low` → canonical object carries `fallback/low`, `basis=reported`, and a warning; `--strict` fails.
6. Missing-record test: no session record → `basis=reported`, `confidence=low`, warning, and `verify --level structural` returns `WARN` not `FAIL`.
7. Determinism preserved: identical canonical input still yields byte-identical Markdown, JSON, HTML, and ZIP with the new fields present.
8. Privacy test asserting no prompt substring appears in the session record, the digest input, or any exported artifact.

**Live acceptance test.** Extend `scripts/run-live-e2e.py` with two scenarios per host on Claude Code and Codex, in a disposable trusted repository: one unambiguous `review + pull-request` prompt that must classify correctly with `basis=attested`, and one deliberately ambiguous prompt that must abstain to `general/fallback/low` and still produce a valid, exportable, verifiable delivery. Retain sanitized event metadata, the canonical objects, and the verify reports — no transcripts, no credentials — under the existing ignored evidence tree, and record the result in `docs/verification.md` as live-host evidence for two hosts only.

**Success metric.** Zero confidently-wrong classifications on the adversarial slice; 100% of deliveries produced through a Brief-Spec hook carry `basis=attested` with populated `rule_ids`; 100% of hand-authored or forged markers surface as `reported`; and the abstention rate on the adversarial slice is *reported* rather than optimized. Determinism regression count: zero.

**Explicit exclusions.** No new work types. No changes to the seven Outcome Brief fields or the three checkpoint modes. No new harness, no promotion of any experimental harness. No renderer changes. No PyPI publication, no tag, no repository visibility change (that is Bet 2's separate program, gated on hosted CI). No schema major version. No cryptographic signing intended for third-party verification — the digest is installation-local and must be documented as such. No Apex pilot changes; the pilot runs in parallel and is not gated on this thread.

## Evaluation plan

Each item below names what is measured, how, and the gate. Everything is reportable from CI or a committed results file.

**Classification quality.** Corpus of 300–500 verbatim prompts from real sessions plus an adversarial slice, labelled independently by two raters with inter-rater agreement (Cohen's κ) published. Report macro-F1, per-type F1, the full confusion matrix, and abstention rate. Two gates: macro-F1 on the verbatim subset with a floor set from the first measured baseline, and **zero** `confidence=high` misclassifications on the adversarial slice. Report abstention; never gate on minimizing it.

**Explanation usefulness.** Per work type, ask readers of a real handoff two questions: "which section answered your question?" and "was any section noise?" Gate: for each of the eight profiles, ≥70% of readers name a section that answered them, and no single section is marked noise by >50%. A profile failing twice is a candidate for deletion — eight types is a hypothesis, not a commitment.

**Time to identify status, action, and proof.** Apex protocol, screen-recorded, two conditions (raw agent output vs Brief-Spec handoff) over identical underlying work, counterbalanced order. Report medians and full distributions, not means, with n stated. Pre-registered thresholds already exist: ≤15s for status and action, ≤30s for proof.

**Evidence-open success rate.** Fraction of proof items a reader can open and reach the intended artifact within 30 seconds, and fraction of readers who open at least one proof item per handoff. The second number matters more: `docs/theory.md:365` names "stable cards make people inspect evidence less often" as a falsification condition, so a *drop* in open rate versus the raw-output condition is a red flag even if the times improve.

**Wrong-status rate.** Reader states what they believe is true about the work; compare to ground truth established from the repository. Rate of "believed complete when it was not" is the single most important safety number in the product. Gate: not worse than the raw-output condition, and ideally lower. Track separately for correctly-classified and misclassified handoffs to isolate the classifier's contribution.

**Cross-harness semantic equivalence.** Define the equivalence relation explicitly: same `classification.work_type` and `subject`, same `brief.kind`, same `brief.status` (or `mode`), same explanation section ids in the same order, and proof sets that resolve to the same locator set. Then run one fixed task on N hosts in a disposable repository and compute pairwise equivalence. Gate: 100% across the five `verified` hosts; report, do not gate, for experimental ones. This is the number that would justify calling Brief-Spec cross-harness.

**Download completion.** For each format and each supported platform: render, then independently verify at `rendered` level in a clean environment. Gate: 100% for `markdown`, `json`, `html`, `zip` on all CI matrix legs; PDF and MP3 gated only on the legs where their toolchains are installed, with unsupported legs reported as "not attempted" rather than omitted.

**Delivery verification success.** Two rates: true-accept (a well-formed delivery verifies at every applicable level) and true-reject (each seeded corruption is caught). Seed at minimum: edited `brief.md`, edited manifest hash, added unlisted member, removed member, mismatched HTML canonical JSON, expired artifact, path escaping the workspace, symlinked evidence, and a receipt pointing at different bytes. Gate: 100% true-accept and 100% true-reject; each corruption class is a named test.

**Installation and rollback reliability.** For each host × scope, on each CI platform: install into a pristine `HOME`, snapshot every managed path, force a mid-install failure, and assert byte-and-mode-exact restoration. Separately: install over a hand-modified `SKILL.md` and a foreign `settings.json` and assert the documented behavior (F11). Gate: 100% exact restoration, zero silent overwrites of user-modified files.

**User trust.** Two questions after a week of real use: "did Brief-Spec ever tell you something was done when it wasn't?" and "did you ever stop reading the underlying evidence because the brief looked complete?" Any "yes" to the first is a defect to root-cause. The second is the compression-induced false-confidence risk `docs/theory.md:363` names; track its rate over time rather than gating on it.

## Roadmap recommendation

### Now — before any tag, publication, or new feature

1. **Classifier honesty** (F1, F2; opportunities 1–2). Margin rule, negation windows, confidence calibration, adversarial slice. Rename the template test and stop citing it as quality evidence.
2. **Run the Apex pilot** (F3; opportunity 4). Parallel to (1), gated on nothing. Publish results including negatives.
3. **Correct the truth boundary** (F5; opportunity 6). Refresh `docs/verification.md` for the committed state and add the machine check so it cannot drift again.
4. **Restore hosted CI** (F7; opportunity 8). Everything below depends on this.
5. **Reserve the three PyPI names** (F6). Cheap, removes a squatting risk, blocks nothing.
6. **Fix the two small correctness bugs**: the `_detect_runtime` precedence bug (F12) and the `SKILL.md` overwrite-versus-documentation contradiction (F11).

### Next — the `0.6.0` steel thread, then publication

7. **Classification attestation** (F4; opportunity 3) — the steel thread above. *Depends on:* Now-1.
8. **Renderer plugin hardening** (F10; opportunity 9's sibling). Allowlist, version check, `--no-plugins`. *Depends on:* nothing; do it before anyone can install a renderer from PyPI.
9. **Publish `0.6.0`**: tag, GitHub release, PyPI via Trusted Publishing, repository public, every documented install command pointing at something that exists (F6; opportunity 7). **Gate:** green full CI matrix on the tagged revision + Now-3 + steel-thread live acceptance on two hosts.
10. **Agent Plugins 1.0 conformance** (F9; opportunity 9). *Depends on:* nothing technically; sequence it with (9) so the first public visitor sees a conformant plugin.

### Later `0.x`

11. **Resolvable schema namespace and conformance test vectors** (F8; opportunity 5). *Depends on:* (9) — vectors are only meaningful once the schema is public and reasonably frozen.
12. **Finish the rename and publish the deprecation table** (F13). **Gate:** must land before `1.0`, because `1.0` is where legacy interfaces are dropped.
13. **Complete the five-host live matrix** across all eight types and all four presentation modes, including the Grok stability hold documented at `docs/verification.md:137-139`. *Depends on:* (4).
14. **Keyword-only harness registry** (F14) and a test cross-checking advertised capabilities against `docs/compatibility.md`.
15. **Second implementation** of the conformance vectors in another language — ideally by someone else. This is the real gate on calling Brief-Spec a standard. *Depends on:* (11).

### `1.0`

16. **Freeze `brief-spec-delivery/2.0`** with published vectors, a documented equivalence relation, and a stated compatibility promise.
17. **Drop the legacy interfaces** enumerated in (12) — `briefspec` CLI, `briefspec` markers and schemas, `BRIEFSPEC_HOME`, `install` alias, legacy entry-point group. **Gate:** the deprecation table has shipped for at least two minor releases with warnings.
18. **`brief-spec equivalence`** as a shipped command (opportunity 10). *Depends on:* (11), (13).
19. **Publication gate for `1.0`:** classification metrics published, Apex results published, full CI matrix green, five-host live matrix complete, at least one external adopter or second implementation.

### Reject or defer

- New harness adapters before (13). **Reject** until the current five are proven.
- Hosted service, dashboard, registry. **Reject.**
- SSML/voice depth, PDF theming, additional TTS providers. **Defer** until the Apex pilot shows anyone uses spoken mode.
- Knowledge-graph, memory, or transcript ingestion. **Reject** — it is an architectural invariant.
- Model-based or networked classification. **Reject.**
- Custom primary work types. **Reject**; subjects are the extension point.
- `enforce` as a default policy. **Defer** indefinitely; `suggest` is correct.
- Third-party cryptographic signing of deliveries. **Defer** past `1.0`; the installation-local digest in the steel thread is deliberately weaker and must be documented as such rather than quietly upgraded.

## Risks and failure modes

**Technical.** The regex classifier is at its complexity ceiling — 24 rules across 8 families with tie-breaking and a 16-entry priority list for subjects, and its behavior is already hard to predict (F1, F2). Adding rules will make it worse, not better; abstention is the only scalable answer. Two validators for one contract (JSON Schema and hand-written Python) will drift, and today the schemas are not even runtime-loaded (F8). Windows PowerShell escaping in `installers.py` is entirely unexercised for this candidate (F7). `session_lock` (`state.py:93-118`) breaks a lock it judges stale after 30 seconds by wall-clock mtime, which is a pragmatic choice that can double-write under clock skew or a slow host.

**Product.** The core reading-cost hypothesis is untested after five versions (F3) — the largest single risk in the review, because it is upstream of every design decision. `docs/theory.md:363` names the specific inversion to watch: a stable, complete-looking card may cause readers to inspect evidence *less*, which would make Brief-Spec a false-confidence generator wearing an evidence-preservation costume. Scope is also drifting outward — eight harnesses, five renderers, six schemas, three checkpoint modes, eight work types — while the one thing that would validate any of it (a human study) remains a template.

**Security and privacy.** The privacy design is genuinely good: no raw prompts, no tool results, no transcripts in state; transcript reads bounded to 256 KiB with symlink refusal (`adapters/base.py:88-119`); private modes and atomic writes; 1 MiB hook input bound. Two real gaps. First, renderer entry points execute third-party code during `verify --level rendered` (F10) — the trust boundary is inverted relative to that command's purpose. Second, `_owned_marker`'s substring test (`installers.py:43-52`) makes any file mentioning `brief-spec:` overwritable, which is a small but genuine footgun on shared config paths. Note also that `_resolve_delivery` makes outbound `HEAD` requests to URLs found in evidence (`verification.py:304-307`); that is documented and defaults are conservative, but verifying a hostile bundle without `--offline` does contact attacker-chosen URLs.

**Ecosystem.** Timing risk cuts both ways. The layer Brief-Spec has invested most engineering in — installers, adapters, per-host manifests — is being commoditized by Agent Plugins 1.0 and Agent Skills across ~40 tools, while the layer nobody owns is verification and provenance, which Brief-Spec has already built. Staying private means watching that window narrow (F6). There is also a governance risk: if AAIF or a vendor ships a verification/attestation layer first, Brief-Spec becomes one implementation of someone else's contract rather than the contract. Conversely, going public invites a large vendor to absorb the ideas — which is a better outcome than obscurity, but should be a conscious choice.

**Maintenance.** Single maintainer, ~16k lines, eight host integrations tracking eight independently-versioned upstream lifecycle APIs, plus a doubled compatibility surface from an unfinished rename (F13). Six schema files, three plugin manifests, three marketplace manifests, and two CLI entry points all encode the same facts in different places; `verify-release.py` exists to keep them aligned, which is both an impressive mitigation and a signal that there is too much duplication. Twelve positional booleans per harness (F14) is a latent correctness hazard in published capability claims.

**Adoption.** Zero external users, private repository, unpublished package, install commands that do not work (F6). The value proposition also requires a behavior change from readers before it pays off — position becomes a cue only after repeated exposure (`docs/theory.md:56-60`) — so first-session value is low by design and the onboarding must carry a lot of weight. Lifecycle automation is the mechanism that produces repeated exposure, which is why the classifier being wrong matters so much: a bad first automatic classification is a plausible reason to set `policy = "off"` and never return.

**Supply chain.** Three unregistered PyPI names, any of which a third party can claim (F6). Two unregistered schema `$id` domains — `brief-spec.dev` and `briefspec.dev` both NXDOMAIN — which someone could register and serve different schemas from, at URLs the project's own artifacts point to (F8). Mitigations already in place and worth protecting: zero runtime dependencies, full-SHA GitHub Action pins with Dependabot, Trusted Publishing with no long-lived token, `attest` build provenance, restart-safe digest preflight, and `verify-release.py` checking source-to-wheel byte equality. The residual risks are the names and the domains, both cheap to fix today.

## Open questions

1. **Is the classifier load-bearing?** If Apex arm (b) (explicit-only) matches or beats arm (a) on time-to-action with a lower wrong-status rate, what is the classifier for? Answering this requires the pilot, not more code.
2. **Is `private` a decision or a default?** Everything about the project — MIT license, `SECURITY.md`, `CONTRIBUTING.md`, marketplace manifests, standards language — assumes public. If there is a deliberate reason for private, the standards framing in README and docs should be softened; if not, F6 is the top priority.
3. **Who is the first non-author user, concretely?** A named team on a named harness with a named workflow. Every roadmap choice here depends on whether that user is a solo engineer wanting a calmer read or a platform team wanting attestable agent output for compliance. Those want different `1.0`s.
4. **Is the eight-type taxonomy right, or is it three types with subjects?** `review`/`implementation`/`debugging` overlap heavily in real prompts (my `mixed-real` test collapsed a three-intent prompt to `implementation/high`). Would `general` + `evidence-bearing` + `investigation` with an open subject slug cover the same ground with far less classifier surface?
5. **What is the compatibility promise for `brief-spec-delivery/2.0`?** Publishing conformance vectors implies a stability commitment. Is `2.0` frozen at `1.0`, or is it explicitly a moving `0.x` contract? A second implementer needs this answered before starting.
6. **How much of the harness layer survives Agent Plugins 1.0?** Requires actually testing whether a single conformant plugin is discovered by the hosts Brief-Spec supports. If it is, several hundred lines of installer become deletable — a large maintenance win for one maintainer.
7. **Should the attestation digest ever become a real signature?** The steel thread deliberately proposes an installation-local keyed digest, not third-party-verifiable signing, because signing implies key management and identity. If the target user is a compliance team, that answer changes and should change early, before the field's semantics are frozen.
8. **What does `verification.md` promise a reader?** It is currently an author's working log (candidate paths, local absolute paths, run URLs) doing double duty as a public trust artifact. Those want different documents; splitting them may be the cheapest way to stop the drift in F5.
9. **Is Grok worth the cost?** Thirteen recorded smoke attempts in `.briefspec/live-e2e/` for one host, ending in a documented hold on upstream tool-path instability. At what point is a host's own instability a reason to move it to `experimental` rather than to keep it blocking a release?
10. **What is the `0.5.0` disposition?** Version `0.5.0` is committed to `main`, referenced by every manifest, cited in a verification record, and built into six local distributions — but was never released, and the changelog already folds `0.3.0` and `0.4.0` into it. Publishing `0.6.0` after these fixes leaves `0.5.0` as a permanent ghost. Decide explicitly whether to publish `0.5.0` first as-is (not recommended, given F1/F2/F4) or to skip it and document why.

## Evidence ledger

Permalinks use the inspected commit `4adf20412028aa858a982c2149c3622327efa11a` under the current canonical repository path `luanmorenommaciel/brief-spec`. The repository is private, so they resolve only for authorized accounts. All observations dated **2026-08-13**.

| # | Label | Locator | Proves | Does not prove |
|---|---|---|---|---|
| 1 | `[direct]` | `git rev-parse HEAD`, `git rev-parse origin/main`, `git diff --stat origin/main HEAD`, `git status --short` | Local checkout equals `origin/main` at `4adf204`; tracked tree clean | That ignored artifacts (`.briefspec/`, `dist/`) match any published state |
| 2 | `[direct]` | `gh api repos/luanmorenommaciel/briefspec` → `full_name: luanmorenommaciel/brief-spec`, `visibility: private`, 0 stars/forks, `has_discussions: false` | The rename already happened; the project is private with no external engagement | That no private collaborators or internal users exist |
| 3 | `[direct]` | `gh release list`; `gh api .../tags` | Latest release `v0.2.0` (2026-07-31T20:40:31Z); only `v0.1.0` and `v0.2.0` tags exist | That `0.5.0` artifacts were never built — six exist locally |
| 4 | `[direct]` | `gh run view 31708342030`; `gh api .../actions/runs/31708342030/jobs` | All 17 CI jobs on `4adf204` were rejected pre-execution for account billing; 2–5s durations; build job skipped | That the code would fail those jobs — nothing ran |
| 5 | `[direct]` | [`tests/test_work_types.py#L24-L69`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/tests/test_work_types.py#L24-L69) | The "160-prompt corpus" is 8 templates × 20 numeric substitutions, drawn from the classifier's own keyword vocabulary; gates are macro-F1 ≥0.95, per-type ≥0.90 | That the classifier is inaccurate on the templates — it passes them |
| 6 | `[direct]` | Runtime: `PYTHONPATH=src python3 -c` importing `briefspec.work_types.classify_task` on this task's prompt | This review request classifies as `implementation` / `pull-request` / `high` / `inferred`, from words inside its prohibition block; `"Do not open a pull request…"` → `review` / `pull-request` | A population error rate; these are three constructed cases |
| 7 | `[direct]` | Claude Code `UserPromptSubmit` hook output in this session | The live hook classified this task as `general + pull-request (low, fallback)` — a different wrong answer with the subject still from a prohibition | That the hook is misconfigured; this is designed behavior |
| 8 | `[direct]` | [`work_types.py#L286-L373`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/work_types.py#L286-L373) | `confidence=high` from ≥2 matched rules in one family; ties fall back to `general/low`; subject is first-match over a fixed priority list; no negation handling | That a better rule set is impossible |
| 9 | `[direct]` | [`markdown.py#L271-L328`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/markdown.py#L271-L328); [`hooks.py#L178-L182`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/hooks.py#L178-L182); [`delivery.py#L505-L513`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/delivery.py#L505-L513) | `confidence`/`origin` come from the model-written marker, are never cross-checked against session state, and `rule_ids` is hard-coded empty | That any agent has actually forged them |
| 10 | `[direct]` | `.briefspec/live-e2e/0.5.0-smoke-claude-review/claude/review-teach/result.json` | A real live-host delivery carries `confidence: high, origin: inferred, rule_ids: []`; that run passed `resolved`, `rendered`, and `delivered` verification at USD 0.3245685 | That the `high` label was justified for that prompt |
| 11 | `[direct]` | [`docs/verification.md#L13`, `#L71-L73`, `#L124`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/verification.md#L124) vs evidence 1–2 | The record calls the candidate "uncommitted" and the rename an open prerequisite; both are now false | That any other row in the truth table is stale |
| 12 | `[direct]` | `pilots/apex/config.toml`, `pilots/apex/results-template.json`, `scripts/run-pilot.py`; no results file in repo or `.briefspec/` | A rigorous study is designed with numeric thresholds and has produced no human data; the runner validates fixtures, not readers | That no informal feedback exists — only that none is recorded |
| 13 | `[direct]` | `curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/{brief-spec,briefspec,brief-spec-renderer-pdf,brief-spec-renderer-audio}/json` → all `404` | Nothing is published to PyPI and none of the names is reserved | That Trusted Publishing is misconfigured |
| 14 | `[direct]` | `nslookup brief-spec.dev`, `nslookup briefspec.dev` → NXDOMAIN; `grep '"\$id"\|"\$ref"' schemas/*.json`; `grep -rn jsonschema src/` (no matches) | Both schema `$id` hosts are unregistered; canonical 2.0 refs absolute URLs on the other host while legacy 1.0 uses relative refs; schemas are never loaded at runtime | That the schemas are internally wrong — the local test registry validates them |
| 15 | `[direct]` | [`renderers.py#L25-L38`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/renderers.py#L25-L38); [`verification.py#L182`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/verification.py#L182) | `entry_point.load()` runs for any distribution advertising the renderer groups, including during `verify --level rendered`; no allowlist or version check | That a hostile renderer package exists |
| 16 | `[direct]` | [`installers.py#L96-L102`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/installers.py#L96-L102) vs [`docs/installation.md#L174`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/installation.md#L174) | A user-modified `SKILL.md` retaining a Brief-Spec marker is overwritten on reinstall, contradicting the documented promise | Which behavior is intended |
| 17 | `[direct]` | [`cli.py#L37-L41`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/cli.py#L37-L41) | `or`/`and` precedence makes the `CODEX_THREAD_ID` guard inapplicable to the `CLAUDE_CODE*` branch | That the misdetection has occurred in production |
| 18 | `[direct]` | `plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` | No manifest declares `$schema` | That the supported hosts currently require it |
| 19 | `[direct]` | [`bundle.py#L231-L239`, `#L277-L286`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/bundle.py#L277-L286); [`verification.py#L152-L158`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/verification.py#L152-L158); [`delivery.py#L98-L130`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/delivery.py#L98-L130) | Determinism is implemented, not aspirational: fixed ZIP metadata, single canonical timestamp, and re-render-and-byte-compare on verify; `deliver` refuses an unverified bundle | That byte-identical output holds across Python versions — untested off one machine |
| 20 | `[direct]` | [`docs/theory.md#L37-L39`, `#L136-L137`, `#L351-L371`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/theory.md#L351-L371) | The design document cites its sources, refuses to over-claim from them, and names its own falsification conditions | That the hypotheses have been tested |
| 21 | `[direct]` | `grep -rh 'def test_' tests/ packages/*/tests/ \| wc -l` → 198 (190 in `tests/`) | 198 test functions exist across core and renderer packages | The 414-test / 86.86%-coverage figures in `docs/verification.md:38-40`; I did not run the suite |
| 22 | `[external]` | [nerdleveltech.com/agent-skills-portable-unverified](https://nerdleveltech.com/agent-skills-portable-unverified) — published 2026-08-09, retrieved 2026-08-13 | Agent Plugins 1.0 shipped 2026-08-06 standardizing packaging across five major clients; Agent Skills, MCP, and Agent Plugins collectively omit trust, provenance, and quality mechanisms; 26.1% of 31,132 sampled marketplace skills contained ≥1 vulnerability | Demand for Brief-Spec specifically; it is secondary commentary, not a first-party spec |
| 23 | `[external]` | [agent-plugins.org/specification](https://agent-plugins.org/specification) (v1.0.0, Working Draft), retrieved 2026-08-13 | §5.3 requires exactly `$schema` and `name`; the spec defines no signature, attestation, permission, or sandboxing mechanism and names no client implementations | Which hosts have shipped conformant loaders |
| 24 | `[external]` | [linuxfoundation.org press release](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) and 2026 summaries, retrieved 2026-08-13 | AAIF exists with 150+ members and eight platinum members (AWS, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft, OpenAI), anchored by MCP, goose, and AGENTS.md; Agent Skills spans ~40 products | That AAIF would accept a verification-layer contribution |
| 25 | `[derived]` | Evidence 5 + 6 + 8 | The classification release gate cannot detect the failure mode the classifier actually exhibits, because the corpus is generated from the same vocabulary as the rules | An exact real-world error rate — that needs a real corpus |
| 26 | `[derived]` | Evidence 2 + 13 + 22 + 24 | The layer Brief-Spec invested most in (installers, adapters, manifests) is being commoditized by public standards, while the layer those standards explicitly exclude (verification, provenance) is Brief-Spec's built and unpublished differentiator | That publishing would produce adoption |
| 27 | `[unknown]` | — | Whether the seven-field contract measurably reduces reading cost for real readers; whether spoken mode is ever used; whether byte-identical determinism holds on Windows and Python 3.14; whether an external party would implement the schema | — |

## Final recommendation

**ADVANCE WITH CONDITIONS**

**Rationale.** The foundation deserves to continue: determinism with real byte-comparison verification, enforced status semantics, receipts that attest to delivered bytes, transactional installers with rollback, and a design document that names its own falsification conditions. That is a better base than most tools have at `1.0`. But the current release candidate must not be published as-is. Its headline feature is a classifier whose quality gate is circular (F1) and which returns confidently wrong types and subjects from negated text — demonstrated on this review's own request (F2) — and it writes an unverifiable `confidence`/`origin` pair into the one artifact whose entire value is that it never over-claims (F4). Meanwhile the truth-boundary document that earns the project its credibility has itself drifted (F5), hosted CI has never run for this candidate (F7), and the schemas that would make this a standard resolve to two unregistered domains (F8). Fix classification honesty, run the pilot that has been designed and never executed, correct and automate the truth boundary, and get the software into someone else's hands. Those are weeks of work, not quarters, and they convert a well-built private artifact into a credible standard candidate.

**The single most important next action.** Make the classifier abstain. Require a margin over the runner-up, cap `inferred` confidence at `medium`, discount rule matches inside negation spans, and add an adversarial prompt slice with the three cases from F2 as named regressions. Ship no other feature until a review request stops being classified as high-confidence implementation.

**The single most important thing Brief-Spec should protect.** The invariant that a presentation artifact never becomes more authoritative than the evidence it represents — and, just as importantly, the habit of writing down where its own evidence stops. The truth-boundary table, the "Honest limits" section, the `Hold` row on Grok, and the theory document's refusal to over-claim from the research it cites are what make this project worth taking seriously. Every finding above is ultimately a place where that invariant slipped. Automate the check so it cannot slip quietly again.
