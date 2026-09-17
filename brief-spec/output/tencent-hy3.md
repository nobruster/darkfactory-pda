# Brief-Spec Independent Review — Tencent Hunyuan 3 (hy3)

## Reviewer context

- **Provider and model:** `tencent` / `hy3` (runtime metadata: `Model: openrouter/tencent/hy3`). Display name: Tencent Hunyuan 3.
- **Harness or interface:** super.engineering (OMP) coding-agent skill runtime. The `brief-spec` artifact inspected is an installed OMP agent skill.
- **Date:** 2026-08-13.
- **Repository URL (as supplied):** https://github.com/luanmorenommaciel/briefspec
- **Branch and commit inspected:** Not available. The supplied repository returned HTTP 404 from the GitHub API and from web fetch. The only inspectable Brief-Spec material is the **locally installed `brief-spec` skill** resolved by the `read` tool to virtual path `/Users/luanmorenommaciel/.omp/agent/skills/brief-spec/`.
- **Latest release observed:** None accessible (no releases, tags, or CHANGELOG reachable).
- **Materials available:**
  - `skill://brief-spec/SKILL.md` (router).
  - 8 profile reference files: `references/{general,exploration,review,implementation,debugging,planning,research,operations}.md`.
  - Enumeration of the owner's 10 public repositories (none named `briefspec`/`brief-spec`).
  - One native web search on the adjacent ecosystem (provider: `web_search`).
- **Research providers used:** native web search (`web_search`) for ecosystem grounding only. No market/demand evidence was gathered.
- **Important inspection limitations:**
  - The GitHub repository at the given URL is **not accessible** (404). README.md, CHANGELOG.md, pyproject.toml, docs/*, schemas/, src/brief_spec/, src/briefspec/, packages/, tests/, and .github/workflows/ could **not** be inspected.
  - The `brief-spec classify` CLI referenced by the skill was **not** inspected and could not be confirmed to exist.
  - Every feature described in the task orientation beyond classification + profile-driven explanation (deterministic Markdown/JSON/HTML/ZIP/PDF/audio projections, provenance/hashes/delivery receipts, harness adapters for Codex/Claude Code/OMP/Grok/Kimi/Copilot/Cursor/Goose, doctor/drift/ownership/migration/rollback) is **unverified** and treated as intent, not fact.
  - **Task classification note (per the brief-spec skill):** a review task maps to the `review` profile (Scope, Verdict, Findings, Risk, Validation, Recommendation); this report follows that order inside the mandated structure. The harness auto-classified the incoming task as `general` + `pull-request` (low, fallback); `classified_at=2026-08-13T14:09:29.110000Z`, `profile=1.0`.

## Executive verdict

Brief-Spec, as inspectable, is **not** the broad verified-delivery protocol the orientation describes. It is a compact, well-shaped **classification-and-explanation router** shipped as an OMP agent skill: it picks one work type + subject, selects one of eight fixed-section profiles, and emits an Outcome Brief or Session Checkpoint wrapped in a typed HTML-comment region for machine parsing. That core is genuinely good and targets a real, currently-unfilled niche — there is no cross-harness agent-output standard today, and the emerging best practice (human summary + machine-readable outcome + lifecycle hooks) matches Brief-Spec's instinct. `[direct]` `[external]`

The problem is the gap between that instinct and everything else. The GitHub repository is inaccessible (404), and the canonical machine-readable Outcome Brief schema, the classifier implementation, harness adapters, provenance, and delivery receipts are all unconfirmed. A standard cannot be a standard without a published, versioned contract and at least one working adapter. `[unknown]`

**Verdict: ADVANCE WITH CONDITIONS.** The design direction is worth pursuing, but only after the repo is published, a concrete Outcome Brief JSON Schema + typed-region grammar ships, and one real harness adapter proves cross-harness equivalence. Without those, Brief-Spec is a promising idea with no enforceable contract.

## What Brief-Spec has become

In plain terms: Brief-Spec is a **router that turns "what an agent did" into a consistent, parseable explanation.** An agent finishes work; Brief-Spec classifies the work into a type (implementation, review, debugging, planning, research, exploration, operations, or general) and a subject slug, then forces the explanation into a fixed section order for that type. The explanation is wrapped in a machine-readable region (`<!-- brief-spec:typed:v1 ... -->`) carrying type, subject, confidence, origin, and a classification timestamp, with a legacy `<!-- briefspec:outcome:v1 -->` region preserved for backward compatibility. `[direct]`

Its mental model is sound: separate the *human-readable narrative* (the profile sections) from the *machine-readable metadata* (the typed region + an outcome brief), and keep classification stable so the same task is explained the same way. That is exactly the contract a multi-harness world lacks.

## Strongest foundations to protect

1. **Stable, profile-keyed explanation structure.** The eight profiles each prescribe a fixed section order (e.g., review: Scope, Verdict, Findings, Risk, Validation, Recommendation). `[direct]` This makes briefs comparable and machine-testable — the single most valuable property for a standard. Protect it as the canonical layer.
2. **Typed wrapper region as a portability primitive.** `<!-- brief-spec:typed:v1 type=… subject=… confidence=… origin=… classified_at=… profile=1.0 -->` carries structured metadata without requiring harnesses to own the format. `[direct]` This is the right abstraction: harness-agnostic, diff-friendly, and embeddable in any Markdown output.
3. **Legacy-compat region.** `<!-- briefspec:outcome:v1 -->` is preserved inside the new wrapper. `[direct]` This shows migration was considered up front — rare and worth keeping. Protect it; do not break it without a documented path.
4. **Evidence-label discipline.** Profiles instruct authors to keep direct, derived, and reported evidence distinct. `[direct]` This is the seed of the provenance story the orientation wants; it is cheap and already in the design. Protect and enforce it.
5. **Classification-before-narration discipline.** The router mandates honoring an explicit type, else running a classifier, else `general`, and keeping the choice stable for the task. `[direct]` This prevents the failure mode of ad-hoc, non-comparable summaries. Protect the "classify once, explain within profile" rule.

## Findings

### F1 — Repository inaccessible; stated scope is unverifiable
- **Severity:** critical
- **Evidence label:** [direct] + [unknown]
- **Observation:** The supplied GitHub repo returns 404 from the API and web; the owner's 10 public repos contain no `briefspec`/`brief-spec`. The orientation describes deterministic projections, provenance, hashes, delivery receipts, and nine harness adapters — none of which are present in the only inspectable artifact (the skill). `[direct]`
- **Why it matters:** Every downstream claim about delivery, security, and cross-harness support is currently unsupported. A reviewer, user, or investor cannot validate the product.
- **Recommended response:** Publish the repository (or grant read access) and reconcile the name (`briefspec` vs `brief-spec` vs the owner's `agentspec`). Until then, treat all non-skill features as proposals.
- **What would verify:** `GET` on the repo returns 200 with README.md, a schemas directory, and at least one adapter; a published release exists.

### F2 — No inspectable canonical machine-readable Outcome Brief schema
- **Severity:** high
- **Evidence label:** [unknown]
- **Observation:** The skill references `outcome-brief` and `briefspec:outcome:v1` but no `brief-spec.schema.json` exists in the skill tree (probe 404). `[direct]` No versioned JSON contract is inspectable.
- **Why it matters:** "Type-aware explanation" and "verified delivery" are empty without a schema. Cross-harness semantic equivalence cannot be enforced or tested.
- **Recommended response:** Ship a versioned `outcome-brief` JSON Schema (status, summary, changes, verification, next_actions, risks, metadata) plus a typed-region grammar, with a reference validator.
- **What would verify:** A schema file passes `ajv`/等效 on a sample brief; the validator rejects a malformed brief.

### F3 — Classification is a prose heuristic with no measurable quality
- **Severity:** high
- **Evidence label:** [direct]
- **Observation:** `SKILL.md` says "when available, run `brief-spec classify - --json`," but the classifier is unverified and routing rules are prose ("honor explicit; else classify; else general"). There is no labeled corpus or accuracy metric. `[direct]`
- **Why it matters:** Classification is Brief-Spec's differentiator. Without a measurable classifier and ground truth, "classification quality" can neither be improved nor defended, and confidence values are uncalibrated.
- **Recommended response:** Define deterministic classification rules, build a labeled corpus, and publish an accuracy/confidence-calibration metric.
- **What would verify:** A held-out eval reporting type accuracy and confidence ECE.

### F4 — Evidence-label discipline is not enforced
- **Severity:** medium
- **Evidence label:** [direct]
- **Observation:** Profiles ask authors to separate direct/derived/reported evidence, but nothing validates that a brief actually carries the labels. `[direct]`
- **Why it matters:** Provenance claims are only as strong as their enforcement; voluntary labeling drifts.
- **Recommended response:** Add a lint rule requiring evidence labels on material claims in any emitted brief.
- **What would verify:** A validator flags a brief missing required labels.

### F5 — Typed region grammar is unspecified beyond the example
- **Severity:** medium
- **Evidence label:** [direct]
- **Observation:** The `brief-spec:typed:v1` region is shown as an example with placeholder substitution rules, but no formal grammar or parser is inspectable. `[direct]`
- **Why it matters:** A portability primitive with no parser is not portable; adapters will diverge.
- **Recommended response:** Publish a grammar + a reference parser (one function, multi-language).
- **What would verify:** Two independent parsers agree on a fixture set.

### F6 — Identity inconsistency across names and surfaces
- **Severity:** medium
- **Evidence label:** [direct] + [unknown]
- **Observation:** Skill name `brief-spec`; legacy region `briefspec:outcome:v1`; supplied repo name `briefspec` (404); owner also publishes `agentspec`. `[direct]`
- **Why it matters:** A standard that cannot name itself consistently will not be adopted as a standard.
- **Recommended response:** Choose one canonical name + namespace; document the `briefspec`→`brief-spec` migration explicitly.
- **What would verify:** One name used across repo, schema `$id`, region tag, and CLI.

### F7 — No inspectable harness adapter
- **Severity:** medium
- **Evidence label:** [unknown]
- **Observation:** The orientation lists Codex, Claude Code, OMP, Grok Build, Kimi Code, Copilot, Cursor, and Goose; none is present in the inspectable artifact. `[unknown]`
- **Why it matters:** The "cross-harness standard" thesis is unproven without at least one real adapter demonstrating equivalence.
- **Recommended response:** Ship two reference adapters (Claude Code `Stop` hook + Codex `--output-schema`) and prove parity on a sample task set.
- **What would verify:** Both adapters emit schema-valid, semantically equivalent briefs on N public tasks.

### F8 — Skill is OMP-coupled despite a portability thesis
- **Severity:** low
- **Evidence label:** [direct]
- **Observation:** The artifact resolves under `/Users/luanmorenommaciel/.omp/agent/skills/brief-spec/` — an OMP-specific install path. `[direct]`
- **Why it matters:** A cross-harness standard shipped only as an OMP skill contradicts its own portability claim.
- **Recommended response:** Package a harness-agnostic core (npm/PyPI) and keep the OMP skill as one adapter.
- **What would verify:** `npm i brief-spec` (or equivalent) emits a brief outside OMP.

### F9 — No inspectable tests, CI, or release evidence
- **Severity:** medium
- **Evidence label:** [unknown]
- **Observation:** `.github/workflows/`, `tests/`, and releases are inaccessible. `[unknown]`
- **Why it matters:** Quality bar and regression safety cannot be assessed; a schema change could silently break adapters.
- **Recommended response:** Publish a test suite (schema + classifier + adapter parity) and CI that fails on contract breakage.
- **What would verify:** A green CI run on a contract change is observable.

### F10 — Profile rigidity may force unnatural explanations
- **Severity:** low
- **Evidence label:** [derived]
- **Observation:** Fixed section orders aid parsing but may misfit some tasks (e.g., a mixed research+implementation task). `[derived]`
- **Why it matters:** Over-rigid structure reduces explanation usefulness, the product's actual user value.
- **Recommended response:** Keep rigidity at the machine layer; allow narrative freedom in the human layer; permit a secondary profile tag.
- **What would verify:** User study shows briefs rated useful while still validating.

## Ten opportunities

1. **Canonical Outcome Brief JSON Schema + validator** — User impact 5, Strategic leverage 5, Evidence confidence 4, Effort M, Risk low, Horizon: next release. *The contract everything else depends on.*
2. **Publish/grant access to the repository and reconcile naming** — User impact 4, Strategic leverage 4, Evidence confidence 5, Effort S, Risk low, Horizon: now. *Unblocks all validation.*
3. **Measurable `brief-spec classify` classifier + labeled corpus** — User impact 5, Strategic leverage 4, Evidence confidence 3, Effort L, Risk medium, Horizon: next release. *Makes classification defensible.*
4. **Two reference harness adapters (Claude Code Stop hook + Codex --output-schema)** — User impact 4, Strategic leverage 5, Evidence confidence 3, Effort M, Risk medium, Horizon: next release. *Proves the standard thesis.*
5. **Typed-region grammar + multi-language reference parser** — User impact 3, Strategic leverage 4, Evidence confidence 4, Effort S, Risk low, Horizon: next release. *Makes the portability primitive real.*
6. **Evidence-label linter for emitted briefs** — User impact 3, Strategic leverage 3, Evidence confidence 4, Effort S, Risk low, Horizon: later 0.x. *Enforces provenance discipline.*
7. **Harness-agnostic packaged core (npm/PyPI) + OMP skill as adapter** — User impact 3, Strategic leverage 4, Evidence confidence 3, Effort M, Risk medium, Horizon: later 0.x. *Resolves the OMP coupling.*
8. **Legacy-region migration tool (`briefspec:outcome:v1` → `brief-spec:typed:v1`)** — User impact 2, Strategic leverage 3, Evidence confidence 4, Effort S, Risk low, Horizon: later 0.x. *Protects the compatibility promise.*
9. **Cross-harness equivalence test suite on public OSS tasks** — User impact 4, Strategic leverage 5, Evidence confidence 3, Effort M, Risk medium, Horizon: next release. *The audit buyers will ask for.*
10. **Deterministic artifact manifest (checksums) for delivered briefs** — User impact 2, Strategic leverage 3, Evidence confidence 3, Effort S, Risk low, Horizon: later 0.x. *Cheap provenance; prerequisite to receipts.*

## Three highest-conviction bets

**Bet 1 — Ship the canonical, versioned Outcome Brief JSON Schema + validator.**
- *Why it dominates:* Every other opportunity (delivery, provenance, cross-harness equivalence, adapters) is blocked until there is a concrete, versioned contract. It is the lowest-effort, highest-leverage move and converts "idea" into "standard."
- *User problem:* Agents and harnesses cannot interoperate because no machine-checkable outcome contract exists.
- *Measurable outcome:* 100% of briefs emitted by a reference adapter validate; cross-harness diff on N tasks ≤ agreed threshold.
- *Must be true before implementation:* Field set agreed (status, summary, changes, verification, next_actions, risks, metadata); `classified_at` uniqueness rule defined; semver policy for the schema.

**Bet 2 — Build and publish the `brief-spec classify` classifier with a labeled evaluation corpus.**
- *Why it dominates:* Classification is the product's only durable differentiator versus "just write a good summary." Without measurable quality and calibrated confidence, the typed region's `confidence` field is decorative and the whole type-aware claim is unprovable.
- *User problem:* Inconsistent, low-trust classification across tasks and harnesses.
- *Measurable outcome:* Type accuracy ≥ target on held-out corpus; confidence ECE ≤ threshold.
- *Must be true before implementation:* A labeled corpus with documented ground-truth rules; decision procedure separable from narrative generation.

**Bet 3 — Prove cross-harness equivalence with two reference adapters on a public sample task set.**
- *Why it dominates:* The entire "cross-harness standard" thesis is unproven without it. One working, parity-tested adapter pair is worth more than nine speculative ones.
- *User problem:* Vendors cannot rely on portability claims.
- *Measurable outcome:* Semantic-equivalence rate reported; documented divergences categorized.
- *Must be true before implementation:* Schema (Bet 1) and classifier (Bet 2) exist; a public task set is selected.

## One contrarian bet

**Bet — Do NOT build the broad "verified-delivery protocol" (deterministic ZIP/PDF/audio projections, provenance hashes, delivery receipts, doctor/drift/ownership/rollback, nine harness adapters) in 0.x. Ship one thin, rigorously-specified contract (typed Outcome Brief + classifier + one adapter) and let adoption, not feature breadth, drive 1.0.**
- *Strongest argument for:* Standards win on simplicity and one killer adapter, not breadth. The orientation's full scope is a textbook path to over-engineering and abandonment for a single-maintainer project. External evidence shows the unfilled niche is satisfied by a minimal human-summary + JSON-outcome + lifecycle-hooks contract. `[external]`
- *Strongest argument against:* The orientation explicitly sells the full protocol; users may expect delivery receipts and provenance; a narrower scope can look unfinished next to the owner's broader `agentspec` ecosystem.
- *Evidence needed to decide:* Adoption signal from one adapter; whether users actually consume ZIP/PDF/audio vs JSON; the measured cost of deferring each deferred feature.

## What not to build

- **Nine harness adapters up front.** Build two reference adapters; let the ecosystem build the rest against the schema.
- **Audio / spoken projections in 0.x.** No demand evidence; high cost; text+JSON must prove value first. `[unknown]`
- **A hosted delivery / receipt service.** Contradicts local-first provenance, adds supply-chain and privacy attack surface, and is not needed for a standard.
- **A marketplace or ecosystem portal.** Premature; distracts from the contract.
- **A second competing classification taxonomy.** Keep work-type + subject; do not introduce parallel taxonomies.
- **Breaking the `briefspec:outcome:v1` legacy region** without a documented, tool-assisted migration.

## Proposed next-release steel thread

- **User scenario:** A developer runs an agent on a pull request; at session stop, a hook emits a validated Brief-Spec Outcome Brief into the repo.
- **Entry point:** Claude Code `Stop` hook (reference adapter) invokes `brief-spec classify` on the transcript, then renders the brief.
- **Classification behavior:** `type=implementation` (or `pull-request`), `subject=pr`, `confidence` computed, `origin=claude-code`, `classified_at` captured once.
- **Explanation behavior:** Implementation profile sections (Intent, Changes, Resulting behavior, Verification, Tradeoffs) filled; evidence labels applied.
- **Canonical data changes:** Emit `outcome-brief/v1` JSON (status, summary, changes, verification, next_actions, risks, metadata) + the `brief-spec:typed:v1` region; legacy `briefspec:outcome:v1` preserved.
- **Download or delivery changes:** Write `.agent/artifacts/outcome.json` and `outcome.md`; write a checksum manifest (no network egress).
- **Harnesses involved:** Claude Code `Stop` hook + Codex `--output-schema` parity test on the same task.
- **Security and privacy boundary:** No secrets in briefs; redaction rules for tokens/paths; local-only; zero network egress by default.
- **Automated tests:** Schema validation; classifier accuracy on corpus; hook rejects an invalid/missing brief; parity test vs Codex adapter.
- **Live acceptance test:** Run on 5 public OSS PRs; both adapters produce schema-valid, semantically equivalent briefs with no secret leakage.
- **Success metric:** 100% validation; cross-harness semantic-equivalence diff ≤ agreed threshold; zero secret leakage; classifier accuracy ≥ target.
- **Explicit exclusions:** No audio/PDF/ZIP; no other seven harnesses; no hosted receipt; no migration tooling beyond the legacy region.

## Evaluation plan

- **Classification quality:** Type accuracy and macro-F1 on a held-out labeled corpus; confusion matrix per work type.
- **Explanation usefulness:** Blind user rating (1–5) of briefs vs free-form summaries on "would you trust/merge this?"
- **Time to identify status, action, proof:** Median seconds to locate status / next action / verification in a brief (vs baseline summary).
- **Evidence-open success rate:** Fraction of material claims carrying a valid evidence label.
- **Wrong-status rate:** Fraction of briefs whose `status` contradicts recorded verification (e.g., `completed` with a failed check).
- **Cross-harness semantic equivalence:** Edit-distance / LLM-judge agreement between two adapters on N tasks; target ≥ agreed threshold.
- **Download completion:** Fraction of emitted briefs with a valid checksum manifest.
- **Delivery verification success:** Fraction of briefs that validate against the schema in a clean environment.
- **Installation and rollback reliability:** Success rate of `npm i brief-spec@x` and downgrade to `@y` with legacy-region still parseable.
- **User trust:** Repeat-use rate and stated confidence in brief accuracy (post-task survey).

## Roadmap recommendation

- **Now**
  - Publish/grant repo access; reconcile naming (F1, F6). *Gate: repo returns 200 with README + schemas.*
  - Ship `outcome-brief/v1` JSON Schema + validator (Bet 1, Opp 1). *Gate: validator passes sample; rejects malformed.*
- **Next**
  - Typed-region grammar + reference parser (Opp 5, F5). *Depends on schema.*
  - `brief-spec classify` classifier + labeled corpus (Bet 2, Opp 3, F3). *Depends on schema.*
  - Two reference adapters + parity suite (Bet 3, Opp 4, Opp 9, F7). *Depends on schema + classifier.*
- **Later**
  - Evidence-label linter (Opp 6, F4).
  - Harness-agnostic packaged core (Opp 7, F8).
  - Legacy-region migration tool (Opp 8).
  - Deterministic artifact manifest/checksums (Opp 10).
- **Reject or defer**
  - Audio/spoken projections (defer; no demand evidence).
  - Hosted delivery/receipt service (reject; privacy + supply-chain).
  - Nine-harness adapter build-out (defer; ecosystem builds against schema).
  - Marketplace/portal (reject).

## Risks and failure modes

- **Technical:** Schema churn breaking adapters; classifier drifting across model versions; typed-region parser divergence.
- **Product:** The niche (cross-harness agent output) may be too small or too dependent on vendor cooperation; agents may not adopt a third-party contract.
- **Security and privacy:** Briefs can leak secrets (API keys in diffs, internal paths); provenance must stay local; a hosted receipt service would be a high-value target. `[derived]`
- **Ecosystem:** Vendors (Anthropic, OpenAI, etc.) may ship their own outcome formats; Brief-Spec could be marginalized unless it is strictly simpler and adapter-led. `[external]`
- **Maintenance:** Single-maintainer project with ten public repos; attention is split; bus-factor risk. `[derived]`
- **Adoption:** Requires harness buy-in (hooks/flags); without it, the standard has no surface.
- **Supply-chain:** If a hosted receipt/delivery service is ever built, it introduces auth, storage, and availability risk contrary to local-first provenance.

## Open questions

- Is the `brief-spec classify` CLI implemented anywhere, and against what ground truth? `[unknown]`
- What is the owner's intent for the repo name and access (briefspec vs brief-spec vs agentspec)?
- Is there demand for audio/PDF/ZIP projections, or is JSON+Markdown sufficient? `[unknown]`
- Will harness vendors adopt a third-party outcome contract, or standardize internally? `[unknown]`
- What license governs Brief-Spec, and does it permit adapter ecosystems?
- What is the agreed field set and semver policy for `outcome-brief`?

## Evidence ledger

| Evidence label | Repository locator / external source | Observation date | What it proves | What it does not prove |
|---|---|---|---|---|
| [direct] | `skill://brief-spec/SKILL.md` (virtual `/Users/luanmorenommaciel/.omp/agent/skills/brief-spec/SKILL.md`) | 2026-08-13 | Router classifies work type+subject, selects 1 of 8 profiles, emits typed region + outcome brief; references `brief-spec classify` CLI. | That the CLI, schemas, or adapters exist. |
| [direct] | `skill://brief-spec/references/{general,exploration,review,implementation,debugging,planning,research,operations}.md` | 2026-08-13 | Eight fixed-section profiles; evidence-label discipline; legacy `briefspec:outcome:v1` preserved. | That any briefs are emitted or validated in practice. |
| [direct] | `skill://brief-spec/schemas/brief-spec.schema.json` (probe → File not found) | 2026-08-13 | No schema bundled in the skill. | — |
| [direct] | `skill://brief-spec/docs/architecture.md` (probe → File not found) | 2026-08-13 | No docs bundled in the skill. | — |
| [direct] | GitHub API `repos/luanmorenommaciel/briefspec` → 404; web fetch → 404 | 2026-08-13 | Supplied repo is not publicly accessible. | — |
| [direct] | GitHub API `user:luanmorenommaciel` repos (10 items) | 2026-08-13 | Owner has no `briefspec`/`brief-spec` repo; publishes `agentspec` and others. | That Brief-Spec lives under another owner. |
| [external] | web_search (provider `web_search`), code.claude.com/docs/en/hooks-guide; github.com/openai/codex (cli.rs, issues/19816) | 2026-08-13 | No cross-tool agent-output standard exists; recommended pattern is human summary + JSON outcome + lifecycle hooks; Claude Code hooks and Codex `--output-schema` are complementary. | Market demand or adoption rates. |
| [unknown] | Task orientation (deterministic projections, provenance, hashes, receipts, 9 adapters, doctor/drift/ownership/rollback) | 2026-08-13 | Stated intent of the project. | That any of it is implemented or published. |
| [derived] | Inference from single-maintainer + 10-repo footprint and skill coupling | 2026-08-13 | Maintenance/bus-factor and OMP-coupling risk. | Causal attribution to specific failures. |

## Final recommendation

**ADVANCE WITH CONDITIONS**

- **Rationale:** The inspectable core — a stable, profile-keyed, typed-region explanation router — is a clean, opinionated design for a real, unfilled niche (no cross-harness agent-output standard exists today, and the emerging best practice matches Brief-Spec's instinct). `[direct]` `[external]` But the GitHub repository is inaccessible, and the canonical schema, classifier, and adapters that would make it a *standard* are unverified. Advancing without those conditions risks shipping a compelling idea with no enforceable contract.
- **Single most important next action:** Publish (or grant access to) the repository and ship one versioned `outcome-brief` JSON Schema plus a reference validator — the contract every other capability depends on.
- **Single most important thing to protect:** The typed `brief-spec:typed:v1` region + legacy `briefspec:outcome:v1` compatibility boundary. It is the only genuine portability primitive present, and breaking it would destroy the one property that makes Brief-Spec worth adopting.
