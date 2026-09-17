# Brief-Spec Independent Review — Moonshot Kimi K3

## Reviewer context

- **Provider and model:** Moonshot AI, `k3` (read from runtime configuration
  `default_model = "kimi-code/k3"` in `~/.kimi-code/config.toml`; slug
  `moonshot-k3`). Not inferred or invented.
- **Harness / interface:** Kimi Code CLI (yolo permission mode), running on
  macOS inside a super.engineering terminal session, with the Brief-Spec plugin
  itself active in the session (a form of live dogfooding, noted for
  transparency, not used as product evidence).
- **Date:** 2026-08-13 (UTC).
- **Repository URL:** Task brief gave
  `https://github.com/luanmorenommaciel/briefspec`. The authenticated GitHub CLI
  resolves the actual repository as `luanmorenommaciel/brief-spec` — the
  `briefspec` name redirects after a rename. The repository is **PRIVATE** as of
  the retrieval date.
- **Branch and commit inspected:** `main` at
  `4adf20412028aa858a982c2149c3622327efa11a`. Local checkout HEAD is identical
  to the GitHub `main` HEAD (`git ls-remote` match), so the local tree and the
  hosted default branch are the same revision. Working tree was **clean**.
- **Latest release observed:** GitHub Release `v0.2.0` ("BriefSpec 0.2.0 —
  first-class Claude Code experience", 2026-07-31), tags `v0.1.0`, `v0.2.0`.
  Source candidate in the tree is `0.5.0` (pyproject.toml, CHANGELOG
  "[0.5.0] - Unreleased candidate"). `dist/` also contains unpublished `0.2.1`
  artifacts. **Nothing exists on PyPI** (`brief-spec`, `briefspec`,
  `brief-spec-renderer-pdf`, `brief-spec-renderer-audio` all return HTTP 404,
  checked 2026-08-13). Zero GitHub issues.
- **Materials available:** full local checkout (source, tests, docs, schemas,
  skills, workflows, renderer packages), authenticated `gh` CLI, web search.
- **Authoritative source:** the local checkout at the commit above, which equals
  hosted `main`. No attached archive. The task brief's URL spelling
  (`briefspec`) and the repository's actual name (`brief-spec`) differ; this is
  treated as a finding, not resolved by assumption.
- **Research providers used:** Kimi Code native web search (2 result sets,
  2026-08-13). Individual sources with dates are in the Evidence ledger. No Exa,
  Tavily, or Firecrawl research APIs were used.
- **Important inspection limitations:**
  - The repository is private, so I could not verify what an unauthenticated
    user sees; all "public release" claims were evaluated against that fact.
  - I did not run the live-host E2E harness (`scripts/run-live-e2e.py`) — it
    requires authenticated host CLIs and is explicitly out of scope
    ("do not install software"; no new credentials). Live-host status is taken
    from `docs/verification.md` as reported evidence, not re-verified.
  - I did not execute the optional PDF/audio renderers (Playwright/ffmpeg
    boundaries); their CI wiring was inspected statically.
  - Hosted CI for the 0.5.0 candidate has never run (billing block, per
    `docs/verification.md`); I could not contradict or confirm that from inside
    the repo.

## Executive verdict

Brief-Spec has become something rarer than its README admits: the only serious,
working attempt at a **cross-harness contract for the agent→human handoff** —
typed explanations, a terminal Outcome Brief, checkpoints, and a hash-verified
delivery envelope — at a moment when input-side (AGENTS.md), tool-side (MCP),
agent-to-agent (A2A), and skill packaging (SKILL.md) standards all exist but
nothing standardizes what the human reads at the end of a task.

The engineering culture is its best asset: truth boundaries are enforced in
code and process, the delivery pipeline is deterministic and verified at four
levels, installers are transactional with real rollback tests, and the
verification record refuses to promote local evidence into published claims.

The product reality is harsher. The repository is private, PyPI is empty, the
0.5.0 candidate is blocked on a CI billing issue, and not one measured human
session has validated the core cognitive hypothesis. The install/adapter layer
is a per-host maintenance liability that converging `.agents/skills/` and
native plugin systems will partially commoditize. Classification is an honest
regex router with a visible ceiling.

**Verdict: ADVANCE WITH CONDITIONS** — publish immediately (0.2.1 is already
built), run one measured real-user pilot before any new feature work, and
position the Outcome Brief as an open spec. Everything else is secondary.

## What Brief-Spec has become

Strip away the renderers, installers, and hooks, and Brief-Spec's durable core
is one idea, well executed:

> **Standardize the shape of the answer, not the thinking that produced it.**

Where AGENTS.md standardized what humans tell agents, and MCP/A2A standardized
how agents reach tools and each other, Brief-Spec standardizes the last mile:
what the human receives when the agent stops. A task is classified locally into
one of eight work types; each type has a fixed explanation section order;
substantive work ends in a seven-field Outcome Brief whose status vocabulary
(`DONE`, `REVIEW`, `DECIDE`, `BLOCKED`, `FAILED`) carries enforced semantics;
and the whole handoff can be exported as one canonical JSON object projected
deterministically into Markdown, HTML, ZIP, PDF, and MP3, with manifests,
SHA-256 hashes, and cumulative verification levels.

The second, quieter idea is **epistemic hygiene as a build artifact**: direct
vs. derived vs. reported evidence, gaps stated instead of smoothed, local vs.
hosted vs. live vs. published kept separate — in the product *and* in the
project's own release discipline. Brief-Spec's `docs/verification.md` is the
product's philosophy applied to itself, and it is the most persuasive document
in the repository.

What it has *not* become: a memory system, a summarizer, an orchestrator, or a
model-calling layer. That restraint is deliberate (docs/theory.md §11) and is
one of the things worth protecting.

## Strongest foundations to protect

1. **Enforced epistemic honesty in the terminal contract.** The validator
   rejects `DONE` carrying gaps or required human action, requires `DECIDE` to
   name an open decision, caps Proof/Next/Open cardinalities, and requires at
   least one inspectable proof locator (`src/briefspec/markdown.py:172-224`).
   Status semantics are machine-checked, not convention. This is the
   differentiation. *(Evidence: direct, markdown.py + tests/test_markdown_contracts.py.)*
2. **One canonical object, deterministic projections, real verification.**
   `canonical_json_bytes` (sorted keys, fixed separators) feeds SHA-256
   digests carried into HTML meta tags, ZIP manifests, and external receipts;
   `rendered`-level verification re-renders core formats from `brief.json` and
   demands byte identity (`src/briefspec/verification.py:152-158`). Forged
   hash-consistent Markdown is rejected in tests. Tamper-evidence is engineered,
   not implied. *(Evidence: direct, delivery.py:98-130, verification.py, test_delivery_edge_cases.py.)*
3. **Transactional, receipt-based installation with proven rollback.**
   Multi-host setup is one two-phase transaction; failures restore preexisting
   bytes; uninstall removes only receipt-owned files whose hashes still match
   and preserves user-modified ones (`src/briefspec/installers.py:762-1076`),
   with dedicated failure-path test files. Most developer tools never achieve
   this; it is what makes "installs into 8 harnesses" survivable.
4. **Fail-open hooks and the one-repair guard.** An internal Brief-Spec error
   can never wedge the host session; an invalid handoff triggers at most one
   corrective pass (`src/briefspec/hooks.py`, tests/test_hook_policies.py,
   tests/test_state_and_hooks.py). This is the correct power budget for a
   presentation layer and a trust prerequisite for everything else.
5. **Evidence-graded project process.** The project separates proposed /
   implemented / locally validated / live-host / hosted-CI / published states
   and blocks its own release on missing gates (`docs/verification.md`), backed
   by 414 tests at 86.86% branch coverage (floor 85%), real-Chromium and
   real-Poppler renderer CI, and PyPI byte-identity checks. My independent
   re-run at the inspected commit passed 413 of 414 — the one failure is
   itself instructive and becomes finding F6 below. Few 0.x tools can show
   this level of process. *(Evidence: direct for the re-run; reported for the
   counts.)*

## Findings

Ordered by consequence.

### F1 — Critical: the product currently has no distribution channel

- **Severity:** critical. **Evidence:** [direct].
- **Observation:** The GitHub repository is `visibility: PRIVATE` (gh API,
  2026-08-13); all four PyPI names return 404; the README's public install
  command (`uv tool install git+https://github.com/luanmorenommaciel/briefspec.git@v0.2.0`)
  cannot succeed for anyone but the owner; the 0.5.0 candidate is blocked on
  GitHub Actions billing (docs/verification.md:16-24); and built, twine-checked
  0.2.1 artifacts sit unpublished in `dist/` since 2026-08-03.
- **Why it matters:** Every other quality in this review is unrealized value.
  Worse, the unclaimed PyPI names (`brief-spec` et al.) are a live supply-chain
  exposure: the day the README circulates, a squatter can own the install
  vector.
- **Recommended response:** Treat publication as the next engineering task, not
  an administrative afterthought: (a) register all four PyPI names *now* even
  with the 0.2.0/0.2.1 bytes; (b) make the repository public or fix the README
  to describe a private preview honestly; (c) decide 0.2.1-vs-0.5.0 on gate
  evidence, not on completeness feelings — 0.2.1 already has a tag-driven
  workflow and built artifacts.
- **What would verify it:** `pip install brief-spec` succeeds from a clean
  machine; PyPI project pages exist with owner-controlled Trusted Publishing;
  README install command run verbatim by a second machine/account.

### F2 — High: repository and naming identity is fragmented

- **Severity:** high. **Evidence:** [direct].
- **Observation:** At least three identities coexist: remote
  `luanmorenommaciel/briefspec.git`, actual repo name
  `luanmorenommaciel/brief-spec` (pyproject URLs, CHANGELOG links), and a
  README badge pointing at `luanmorenomaciel/briefspec` (one `m` short — 404
  even authenticated). The task brief for this review used yet the old name.
  `docs/verification.md:124` still lists "rename the GitHub repository to
  `brief-spec`" as a pending prerequisite even though the rename has already
  happened (the old remote redirects). `integrations/copilot/cloud/README.md`
  names hook files `briefspec.json` where the installer writes
  `brief-spec.json` (installers.py:222).
- **Why it matters:** For a project whose entire thesis is "trust the label,"
  broken badges and drifting names are disproportionately damaging, and they
  will compound at publication (PyPI name, repo name, CLI name, schema `$id`
  domain `briefspec.dev` vs `brief-spec.dev` in the schema pairs).
- **Recommended response:** One canonical identity sweep (repo, PyPI, schema
  domain, badges, docs) folded into the 0.5.0 gate; extend
  `scripts/verify-release.py` to fail on non-resolving first-party URLs.
- **What would verify it:** every first-party URL in README/pyproject/CHANGELOG
  returns 200 in CI; verification record no longer lists a completed rename as
  pending.

### F3 — High: the core product hypothesis has zero measured human evidence

- **Severity:** high. **Evidence:** [direct] + [derived].
- **Observation:** `docs/theory.md` §12 lists falsification tests (time to find
  outcome/action, evidence location, checkpoint annoyance). `pilots/apex/`
  defines success thresholds (15s status-action, 30s proof location) — but its
  corpus is five synthetic fixtures validated by `run-pilot.py` against the
  project's own parser. No human session has been timed. The 160-prompt
  classification corpus measures the classifier against itself.
- **Why it matters:** The theory of change (stable schema → faster recognition
  → better judgment) is plausible and well-cited, but the alternative
  hypothesis — fixed boilerplate adds reading cost that outweighs recognition
  gains for expert users — is equally consistent with everything currently in
  the repository. Features are accumulating (PDF! audio! 8 harnesses!) ahead of
  the cheapest decisive measurement.
- **Recommended response:** Run the bounded Apex pilot with 5–10 real sessions
  across at least two harnesses before any new capability work; instrument
  time-to-status, time-to-proof, override rate, and dismissal rate.
- **What would verify it:** a filled `results-template.json` from real sessions
  with a pre-registered threshold verdict, published in the repo.

### F4 — High: the per-host installation/lifecycle layer is the deepest maintenance sink and faces commoditization

- **Severity:** high. **Evidence:** [direct] + [external].
- **Observation:** `installers.py` (1110 lines) carries per-host special cases:
  `$CLAUDE_PROJECT_DIR` anchors, `git rev-parse` Codex anchors plus a
  PowerShell `commandWindows` variant, a ~100-line generated OMP TypeScript
  extension, dual Copilot bash/powershell payloads, Kimi's user-plugin vs
  project-skills split, Goose's capability-marker non-hooks. Doctor adds
  another ~230 lines of host-specific branches. Meanwhile the ecosystem is
  converging: SKILL.md became an open standard (2025-12-18) with 40+ adopters,
  and `.agents/skills/` is emerging as the cross-tool skills directory
  (cantrips multi-harness research, 2026-07-10; agentskills.io).
- **Why it matters:** Every host release can silently break eight
  integrations, and the parts most likely to break (lifecycle hook wiring) are
  exactly the parts hosts are native-izing. The durable asset — the contract
  and the delivery pipeline — risks being held hostage by the most perishable
  layer.
- **Recommended response:** In later 0.x, re-tier the architecture: skills +
  CLI + delivery as the evergreen core; per-host lifecycle glue as thin,
  explicitly-versioned adapters with a stated "host broke us" policy; adopt
  `.agents/skills/` projection where hosts read it natively.
- **What would verify it:** adapter layer shrinks (measurable LOC/branch
  count); a host minor-version bump produces a doctor WARN, not a broken
  install.

### F5 — Medium: verification levels have honest but real gaps an adversary or accident can exploit

- **Severity:** medium. **Evidence:** [direct].
- **Observation:** (a) `resolved` verification issues HTTP HEAD only —
  `provenance[].content_sha256` is never checked against a body
  (verification.py:304-313); (b) proof kinds `test`, `pr`, `issue`,
  `observation` are never resolved at all (WARN branch,
  verification.py:315-317), so the enforced "DONE needs direct/derived pass"
  rule validates declared metadata, not the underlying artifact, for those
  kinds; (c) no zip-bomb guard or member-size cap in bundle verification; (d)
  `validate_delivery` imposes no array-size limits on `provenance`,
  `artifacts`, `work_items`; (e) evidence file hashing reads whole files
  unbounded (verification.py:272); (f) `parse_time` silently substitutes
  `now()` for unparseable timestamps (adapters/base.py:56-58).
- **Why it matters:** The product's promise is "a brief is never more
  authoritative than its source." Gaps (a) and (b) are exactly where that
  promise currently rests on the author's honesty — acceptable at 0.x if
  disclosed, corrosive if discovered by a user.
- **Recommended response:** Document the attestation boundary in
  docs/delivery.md; add opt-in `--fetch-urls` body verification behind the
  existing consent pattern; add zip/size/depth bounds; make `parse_time`
  failures recorded as warnings in state.
- **What would verify it:** new failure-path tests for each bound; docs name
  precisely what `resolved` does and does not attest.

### F6 — Medium: the "deterministic" local gate is not hermetic — the suite result depends on host PATH

- **Severity:** medium. **Evidence:** [direct].
- **Observation:** my independent `uv run pytest -q` at the inspected commit
  produced **1 failure in 414 tests**:
  `test_doctor_all_can_treat_an_unavailable_host_as_optional`
  (tests/test_bundle_cli_doctor.py:145-152). Root cause: the test asserts that
  doctor reports COPILOT as WARN-optional when uninstalled, but
  `optional_when_absent` only rewrites FAILs when neither a receipt **nor the
  host executable** exists — and this machine has `copilot` on PATH
  (`~/.superconductor/bin/copilot`, confirmed via `shutil.which`). The test
  therefore passes on a clean CI runner and fails on the maintainer's own
  fully-installed dogfooding machine. The verification record's "414 passed on
  macOS" claim could not be reproduced in the maintainer's actual daily
  environment.
- **Why it matters:** the project's central process asset is "deterministic
  gates." A suite whose result flips with the host's PATH is not deterministic,
  and it means the published verification record and the maintainer's live
  machine currently disagree — precisely the class of drift Brief-Spec exists
  to catch.
- **Recommended response:** make the test hermetic (stub `shutil.which` /
  PATH in the fixture), and add a CI leg that runs the suite with a
  fully-populated host PATH so both environments are gated.
- **What would verify it:** the suite passes identically on a bare runner and
  on a machine with all eight host CLIs installed.

### F7 — Medium: regex classification is transparent but has a visible ceiling and no feedback loop

- **Severity:** medium. **Evidence:** [direct] + [derived].
- **Observation:** Classification is ~25 keyword rules
  (src/briefspec/work_types.py:167-231); ties and misses fall back to
  `general`/LOW; English-only patterns; the typed wrapper then stamps
  `type=`/`confidence=` on user-visible output. There is no opt-in mechanism to
  learn from overrides.
- **Why it matters:** A wrong `type=` badge on an otherwise good brief quietly
  taxes the trust the product is built on. But adding an LLM classifier to core
  would break the dependency-free, network-free invariant — a real tradeoff,
  not an oversight.
- **Recommended response:** Keep the deterministic core; surface `confidence`
  and `rule_ids` in the human output when LOW/MEDIUM; make the override gesture
  one word (`type: review`); count overrides in bounded state as the pilot's
  classification metric.
- **What would verify it:** pilot override-rate < 15% with stable per-type F1
  on a refreshed corpus including non-English prompts.

### F8 — Medium: standards adjacency is asserted but not yet engaged

- **Severity:** medium (as opportunity cost). **Evidence:** [external] + [derived].
- **Observation:** AGENTS.md (2025-08), Agent Skills (2025-12-18, 40+
  adopters), MCP and A2A (both under the Linux Foundation's agentic working
  group in 2026) cover instructions, skills, tools, and agent-to-agent. My
  searches surfaced **no** standard for the agent→human terminal handoff;
  absence-of-evidence caveat applies ([unknown] until a systematic sweep
  confirms). Brief-Spec's markers (`<!-- briefspec:outcome:v1 -->`) and schemas
  are bespoke and not submitted anywhere; provenance cites W3C PROV as
  inspiration but exports no PROV-O/JSON-LD mapping.
- **Why it matters:** the whitespace is real but the window is not permanent;
  the first credible convention to be copied by two harnesses wins by default.
- **Recommended response:** publish the Outcome Brief + typed wrapper as a
  small standalone spec (versioned, implementation-independent), with
  Brief-Spec as reference implementation; optional PROV-O alignment at 1.0.
- **What would verify it:** one external project or harness copies the format
  without Brief-Spec code.

### F9 — Low: code health is good; specific dead/duplicated spots should be cleaned at 0.5.0, not later

- **Severity:** low. **Evidence:** [direct].
- **Observation:** `models.SourceMetadata` is unused (delivery builds `source`
  as a dict); the codex/claude/copilot adapter modules are 10-line identity
  pass-throughs behind a registry indirection; CSP directive tuples and
  external-reference regexes are duplicated inside verification.py; the spoken
  "Screen-only proof" special case appears three times in delivery.py; receipt
  JSON is constructed twice in bundle.py; `HookDecision` appears unused.
- **Why it matters:** individually trivial; collectively they are where a
  0.x→1.0 reviewer forms an impression of the codebase.
- **Recommended response:** one deletion pass before 0.5.0; no behavior change.
- **What would verify it:** grep shows single definitions; suite stays green.

### F10 — Opportunity: dogfooding data is being generated and discarded

- **Severity:** opportunity. **Evidence:** [derived].
- **Observation:** the author dogfoods 0.5.0 across five hosts daily
  (docs/verification.md:111-118). Those sessions are exactly the pilot cohort
  F3 needs, and the bounded state already contains the counters — but nothing
  aggregates them into evaluation.
- **Recommended response:** a `brief-spec state stats` (or pilot exporter) that
  turns existing counters into the pilot metrics without storing content.
- **What would verify it:** the pilot report in F3 is produced from real state,
  not manual notes.

### F11 — Opportunity: CI consumption of briefs is unbuilt but cheap

- **Severity:** opportunity. **Evidence:** [derived].
- **Observation:** `brief-spec verify` on an agent-produced bundle is a natural
  PR check ("the agent's claimed delivery verifies at `rendered`"), fitting the
  existing CLI and exit codes, yet no docs or workflow demonstrate it.
- **Recommended response:** one documented GitHub Actions recipe; no new code
  expected.
- **What would verify it:** the recipe runs on this repository's own PRs.

## Ten opportunities

Scores: user impact / strategic leverage / evidence confidence (1–5); effort
S/M/L/XL; risk; horizon.

1. **Publish: PyPI names registered + public repo + shipped release.**
   5/5/5 · S · low · next release. Unlocks every other opportunity; closes the
   name-squatting exposure.
2. **Measured real-session pilot (Apex) with pre-registered thresholds.**
   5/5/4 · M · medium · next release. Converts the theory of change from essay
   to evidence; gates all further feature investment.
3. **Publish the handoff contract as an open mini-spec; Brief-Spec as reference
   implementation.** 4/5/3 · M · medium · later 0.x → 1.0. Claims the agent→human
   whitespace while the window is open.
4. **Re-tier architecture: evergreen core + thin versioned host adapters;
   adopt `.agents/skills/` projections.** 4/4/4 · L · medium · later 0.x.
   Cuts the largest maintenance and host-drift risk.
5. **Close verification attestation gaps (URL bodies behind consent, archive
   and size bounds, timestamp-failure signaling).** 3/3/5 · S · low · next
   release. Aligns the code with the trust promise.
6. **Classification transparency + one-word override + override-rate metric.**
   3/4/4 · S · low · later 0.x. Protects trust at the regex ceiling without an
   LLM in core.
7. **Restore hosted CI (billing or self-hosted) and wire `run-live-e2e.py` as a
   scheduled, credentialed gate.** 4/4/4 · M · medium · next release. Turns the
   project's own truth boundaries into repeatable infrastructure.
8. **PROV-O/JSON-LD export mapping for provenance and delivery envelopes.**
   3/4/3 · M · low · 1.0. Makes briefs ingestible by compliance and archival
   tooling without core changes.
9. **Renderer SDK hardening + third-party renderer authoring guide.**
   3/3/3 · M · low · 1.0. The entry-point protocol is already clean; the gap is
   documentation and stability promises.
10. **"Verify the agent's delivery in CI" recipe (GitHub Action / PR check).**
    4/4/3 · M · medium · later 0.x. Extends Brief-Spec from reading aid to
    delivery gate — the strongest enterprise hook available.

## Three highest-conviction bets

### Bet 1 — Publish now (Opportunity 1)

- **Why it dominates:** every other bet multiplies an installed base of zero.
  It is also the only bet that is pure execution: 0.2.1 artifacts are built and
  twine-checked, the release workflow exists and is pinned, and the only
  blocker named in the verification record is account billing.
- **User problem addressed:** "I read about Brief-Spec; I cannot install it."
  Today that is 100% of potential users.
- **Measurable outcome:** `pip install brief-spec` succeeds from a clean
  environment; four PyPI names owner-registered with Trusted Publishing; clone
  and install by a non-owner GitHub account succeeds.
- **Must be true first:** the maintainer accepts shipping 0.2.1 (or a
  scope-cut 0.5.0) rather than waiting for the full 0.5.0 gate set; CI billing
  resolved or an equivalent hosted gate stood up.

### Bet 2 — Prove the reading-time hypothesis with a measured pilot (Opportunity 2)

- **Why it dominates:** it is the only bet that can falsify the product. The
  theory document already names the metrics; the pilot scaffolding already
  exists; the maintainer's own five-host dogfooding is a ready cohort. No other
  opportunity changes what should be built next as much as this one's result.
- **User problem addressed:** re-entry cost — "before acting, you must first
  discover how to read the answer." Currently asserted, not measured.
- **Measurable outcome:** median time-to-status ≤ 15 s and time-to-proof ≤ 30 s
  on Brief-Spec handoffs vs. a matched unstructured baseline; wrong-status
  interpretation rate and checkpoint dismissal rate reported either way —
  including a negative result, which is itself the deliverable.
- **Must be true first:** 5–10 real sessions across ≥ 2 harnesses can be
  captured without storing content (privacy invariant holds); thresholds are
  pre-registered in `pilots/apex/config.toml` before data collection.

### Bet 3 — Claim the open whitespace: the handoff contract as a spec (Opportunity 3)

- **Why it dominates:** inputs (AGENTS.md), skills (SKILL.md), tools (MCP), and
  agent-to-agent (A2A) are all standardized as of 2025–2026; the agent→human
  handoff is the remaining unstandardized surface, and Brief-Spec is — per my
  searches — the only artifact with a working contract, validator, and
  cross-harness evidence. Specifications are winner-take-most; being second is
  worth little.
- **User problem addressed:** multi-harness users (the README's actual audience)
  re-learn output conventions per agent; a spec makes the convention survive
  any single tool, including Brief-Spec itself.
- **Measurable outcome:** a versioned, implementation-independent spec document
  published; at least one external adoption signal (another tool emitting or
  consuming the markers; a harness docs reference; a third-party validator).
- **Must be true first:** Bet 1 (a spec for an uninstallable tool is a
  curiosity); naming identity unified (F2) so the spec has one canonical home.

## One contrarian bet

**Freeze — possibly delete — the automatic lifecycle-hook layer, and ship
Brief-Spec as skills + CLI only.**

- **Strongest argument for:** The hook layer is where the maintenance cost
  (F4), host fragility (Grok's ignored passive-hook stdout; Kimi's user-plugin
  constraint; Goose's non-hooks), and safety engineering (fail-open, one-repair,
  loop guards) all concentrate. Hosts are native-izing session lifecycle
  features at high velocity; Brief-Spec's per-host projections will be
  re-implemented badly and often. Meanwhile the contract, validator, and
  delivery pipeline lose *nothing* if a checkpoint is invoked manually or via a
  host's own native reminder. "Same fields, same order" does not require a
  PostToolUse hook. Deleting the layer would shrink the adversarial surface,
  the installer, and the support matrix simultaneously.
- **Strongest argument against:** boundary-aware checkpoints are a genuine
  differentiator — the interruption-timing research grounding (theory.md §5) is
  the most original product thinking in the repo, and manual invocation
  reliably under-fires precisely when sessions get long (the exact failure the
  feature exists for). Without lifecycle integration, Brief-Spec risks being
  "just a format," competing on documentation quality alone.
- **Evidence needed to decide:** the Bet 2 pilot, specifically: (a) how often
  users invoke checkpoints manually when hooks are off (suggest vs manual A/B
  within the pilot), (b) dismissal/annoyance rate of automatic checkpoints,
  (c) maintenance hours per host per month attributed to hook wiring. If
  automatic checkpoints show low value *or* hook maintenance exceeds a set
  budget, the contrarian bet wins and should be executed deliberately rather
  than by slow decay.

## What not to build

- **A hosted Brief-Spec service / dashboard.** The network-free, state-minimal
  invariant is the trust story; a server would trade the moat for features
  already owned by host vendors' dashboards.
- **Knowledge-base ingestion or "memory."** Explicitly and correctly excluded
  today (theory.md §11); any drift toward a second brain blurs the epistemic
  boundary that makes the briefs trustworthy.
- **LLM-based classification inside the core package.** Breaks the
  dependency-free, offline, deterministic guarantees to fix a medium-severity
  problem that transparency + override (F7) addresses cheaper. A separate
  optional plugin could explore it post-1.0.
- **More output modalities (video, slides, slides-as-PDF variants).** PDF and
  audio are already at the edge of the core promise; each new renderer is a
  verification-surface multiplier.
- **Custom user-defined work types at 0.x.** `types_document()` deliberately
  reports `custom_primary_types: false`; keep the vocabulary small until the
  pilot shows which distinctions users actually read.
- **A brief registry / marketplace / gallery.** Premature distribution
  infrastructure for an artifact whose value is private and local.
- **More harnesses** (Gemini CLI, Amp, Aider, …) until the experimental three
  (Copilot, Cursor, Goose) are either promoted through live gates or dropped.
  Breadth is already ahead of evidence.

## Proposed next-release steel thread

**"Publish and prove": one bounded increment that ships 0.2.1 and runs the
measured pilot on it — nothing else.**

- **User scenario:** a solo engineer (the maintainer counts) runs real daily
  work across two installed harnesses (e.g., Codex + Kimi, both already
  doctor-green) for five working days, installing exclusively from the
  *published* artifact.
- **Entry point:** `uv tool install brief-spec` (or the git-tag URL) from a
  clean machine — the install itself is part of the experiment, timed.
- **Classification behavior:** unchanged 0.2.x/0.5.0 deterministic rules; every
  LOW/MEDIUM-confidence or overridden classification is logged via bounded
  counters (no content).
- **Explanation behavior:** unchanged type profiles; the observer records
  time-to-status and time-to-proof with a stopwatch protocol defined in the
  pilot config before starting.
- **Canonical data changes:** none permitted. If 0.5.0 is chosen instead of
  0.2.1, the schema is frozen at the inspected commit — no delivery-object
  edits during the pilot.
- **Download or delivery changes:** none. Each day, one handoff is exported
  (`markdown,json,html`), bundled, delivered to a local directory, and verified
  at level `delivered` — exercising the existing pipeline end to end as a
  smoke, not developing it.
- **Harnesses involved:** the two installed; explicitly not all eight.
- **Security and privacy boundary:** pilot state stays within existing
  counters/timestamps/hashes; no prompts, transcripts, or tool outputs are
  recorded; the published-artifact install is verified against PyPI digests.
- **Automated tests:** existing suite + one new test asserting the published
  wheel's version equals the tagged release (the release workflow already has
  most of this; the gap is running it).
- **Live acceptance test:** (1) non-owner machine installs from PyPI and runs
  `brief-spec doctor <host> --probe` green; (2) pilot metrics file filled for
  every session; (3) `brief-spec verify ... --level delivered` passes on each
  day's bundle.
- **Success metric:** install-to-first-valid-brief < 15 minutes on the clean
  machine; ≥ 90% of pilot sessions end with a valid brief; median
  time-to-status ≤ 15 s vs. the unstructured baseline; classification override
  rate reported (target < 15%).
- **Explicit exclusions:** new harnesses, new renderers, schema 2.1, spec
  publication, `.agents/skills/` re-tiering, any classifier changes.

## Evaluation plan

- **Classification quality:** maintain the labelled corpus as a versioned,
  growing asset (current: 160 prompts, macro + per-type F1 gates); add
  non-English and adversarial prompts; track pilot override rate as the field
  metric. Report per-type precision/recall, not only macro F1.
- **Explanation usefulness:** pilot task — given only the typed explanation,
  can the reader state what changed and why in ≤ 30 s? Score per section;
  sections scoring low are candidates for removal, not rewrite.
- **Time to identify status, action, and proof:** stopwatch protocol in the
  pilot; report median and p90 against a matched unstructured-baseline reading
  of the same sessions' transcripts.
- **Evidence-open success rate:** fraction of Proof locators that resolve when
  clicked/run by the reader (already enumerable from `resolved` verification +
  pilot sampling); target ≥ 90%; investigate every failure class.
- **Wrong-status rate:** fraction of briefs whose status the human reader
  judges incorrect after inspection (e.g., `DONE` that wasn't). Target < 10%;
  this is the trust-killer metric and should gate any `enforce`-policy default.
- **Cross-harness semantic equivalence:** extend the existing
  contract-equivalence tests with a live matrix: same task, two harnesses,
  compare normalized canonical JSON (excluding source metadata); already
  prototyped in the live smokes — promote to a scheduled gate.
- **Download completion:** bundle build → deliver → verify chain success rate
  in pilot (target 100%; every failure is a bug by definition).
- **Delivery verification success:** `verify --level delivered` pass rate on
  recipient machines, including cross-platform (macOS→Linux) transfers.
- **Installation and rollback reliability:** doctor pass rate after install,
  after host upgrade, and after uninstall-reinstall cycles; the installer test
  suite already simulates failures — add a weekly real-matrix CI job once
  hosted CI is restored.
- **User trust:** 3-question post-session pilot survey (did the brief match
  reality? did you check proof? would you keep it?) plus the behavioral proxy
  that matters most: proof-open rate. If stable cards cause users to inspect
  evidence *less*, theory.md §12 says the design needs revision — measure it.

## Roadmap recommendation

- **Now (next release — the steel thread):**
  1. Register PyPI names; publish 0.2.1 (or gate-passed 0.5.0); make the repo
     public or rebrand the preview honestly. *(F1)*
  2. Naming-identity sweep; verification-record refresh (the repo rename is
     done — the doc is stale); `verify-release.py` URL liveness check. *(F2)*
  3. Close the cheap verification bounds (zip/size caps, timestamp warnings) —
     hours of work, trust-surface payoff. *(F5 partial)*
  4. Pre-register and run the Apex pilot. *(F3)*
  - *Gate to Next:* pilot metrics file complete; published install verified by
    a non-owner.
- **Next (later 0.x):**
  5. Restore hosted CI; wire scheduled credentialed live-host matrix. *(F4
     prerequisite, O7)*
  6. Classification transparency + override metric. *(F7)*
  7. Re-tier adapters; `.agents/skills/` projections; drop or promote the three
     experimental harnesses based on live-gate evidence. *(F4)*
  8. CI verification recipe for agent deliveries. *(F11)*
  - *Gate to 1.0:* pilot shows positive or null-but-acceptable reading metrics;
    no critical host-drift incident for one full host release cycle.
- **Later (1.0 and after):**
  9. Open mini-spec for the handoff contract; PROV-O/JSON-LD mapping. *(F8, O8)*
  10. Renderer SDK stability promises + authoring guide. *(O9)*
  11. Decide the contrarian bet (freeze hooks?) on pilot evidence.
- **Reject or defer:** hosted service, memory features, LLM-in-core
  classification, more modalities, custom work types, brief marketplaces, more
  harnesses. *(See "What not to build"; classification override is F7.)*

Dependencies: 1→everything; 2→9; 4→6, 7, 11; 5→7.

## Risks and failure modes

- **Technical:** host lifecycle APIs drift per release across 8 harnesses with
  no hosted CI currently running to catch it; Grok's live gate is already on
  hold for host tool bugs (verification.md:88); verification bounds gaps (F5)
  could let a malformed bundle exhaust memory; regex classifier misfires on
  non-English or jargon-dense prompts.
- **Product:** fixed boilerplate may add reading cost for experts (the
  unfalsified alternative hypothesis); status vocabulary may fail to express
  real engineering states (theory.md §12 names this); typed badges with wrong
  LOW-confidence classifications quietly tax trust; checkpoint annoyance is
  unmeasured.
- **Security and privacy:** PyPI name squatting is an open exposure today;
  hooks receive host payloads (bounded to 1 MiB, but they arrive at all); the
  256 KiB transcript tail read is a real, if bounded, content exposure worth
  re-stating in SECURITY.md terms; the optional OpenAI audio path is
  well-gated (consent + env-only credentials) and must stay that way.
- **Ecosystem:** hosts absorb the feature natively — a first-party "session
  summary" in two major harnesses would compress Brief-Spec's window faster
  than any competitor; conversely, standardization bodies could pick a
  different handoff convention, making the spec bet (Bet 3) the mitigation.
- **Maintenance:** single-maintainer project with an 8-harness support matrix,
  two renderer packages with heavy native dependencies (Playwright/Chromium,
  Poppler, ffmpeg), and a release process with many manual gates — bus factor
  and burnout risk are the realistic ceiling on ambition.
- **Adoption:** private repo + empty PyPI + fragmented naming means adoption
  starts from zero *after* two weeks of release-candidate effort; the README is
  excellent but currently unpublishable-grade honest about a release that
  isn't reachable.
- **Supply-chain:** dependency-free core is exemplary; the risk concentrates in
  renderer deps and GitHub Actions (mitigated: full-SHA pins + Dependabot) —
  and in the unclaimed PyPI names, which is self-inflicted and fixable today.

## Open questions

1. Ship 0.2.1 now vs. hold for 0.5.0 — is the typing/delivery-2.0 surface worth
   another release delay, or is it exactly the kind of scope that should follow
   pilot evidence? *(human judgment)*
2. What reading-time improvement would justify the boilerplate — 10%? 50%? —
   and who is the threshold user: the multi-agent power user or the occasional
   one? *(customer evidence)*
3. Will any major harness ship a native structured handoff in the next 12
   months, and would Brief-Spec's response be spec-first cooperation or
   differentiation? *(ecosystem watch)*
4. Is the enforce/auto corrective pass acceptable to users in practice, or does
   one forced repair feel like the tool fighting the agent? *(pilot)*
5. Does the Copilot cloud bridge have real users, or is it maintained
   complexity for a hypothetical surface? *(usage evidence)*
6. Should schemas move to a real domain (briefspec.dev is referenced in `$id`s
   — ownership/resolution unverified from here) before the spec bet? *(technical
   validation)*
7. What is the maintenance budget per host per month that triggers the
   contrarian hook-freeze decision? *(human judgment — set it before the pilot,
   not after)*

## Evidence ledger

Permalinks use the inspected commit `4adf204`; the repository is private, so
links resolve for the owner only. Dates: all repository observations
2026-08-13.

| Claim | Label | Locator | Proves | Does not prove |
| --- | --- | --- | --- | --- |
| Repo is private; actual name `brief-spec`; HEAD = local 4adf204 | [direct] | `gh repo view luanmorenommaciel/brief-spec` (2026-08-13); `git ls-remote` | Distribution is currently impossible for non-owners; local==hosted main | Intent; future visibility |
| No PyPI packages under any of the four names | [direct] | `pypi.org/pypi/{brief-spec,briefspec,brief-spec-renderer-pdf,brief-spec-renderer-audio}/json` → 404 (2026-08-13) | No Python-package distribution; names unclaimed | That names won't be squatted tomorrow |
| Latest release v0.2.0 (2026-07-31); no issues | [direct] | `gh release list` | Only 0.1.0/0.2.0 have ever shipped | Release quality |
| 0.5.0 blocked on CI billing; live Grok gate on hold | [reported→direct] | `docs/verification.md:12-24,82-96` (in-repo record) | The project's own gating is honest and currently red | The underlying live runs still pass today |
| Local gates: 414 tests, 86.86% branch coverage claimed | [reported→partially confirmed] | `docs/verification.md:38`; independent `uv run pytest -q` at 4adf204: 413/414 passed, 1 environment-dependent failure (see F6) | Suite is real and overwhelmingly green on a second run context | That the gate is hermetic — it is not (F6) |
| Validator enforces status semantics, order, caps, proof locators | [direct] | `src/briefspec/markdown.py:172-260`; `tests/test_markdown_contracts.py` | Contract integrity is machine-enforced | That honest-looking claims are true |
| Deterministic canonical JSON + byte-identity re-render verification | [direct] | `delivery.py:98-130`; `verification.py:152-158`; `test_delivery_edge_cases.py` | Tamper-evident pipeline | URL/provenance body integrity (HEAD-only, `verification.py:304-313`) |
| Installers transactional with rollback and receipts | [direct] | `installers.py:762-1076`; `test_installer_failure_paths.py` | Failure safety engineered and tested | Behavior against future host config formats |
| Classification is ~25 regex rules, fallback general/LOW, no learning | [direct] | `work_types.py:167-373` | Transparency and ceiling | Real-world accuracy beyond the 160-prompt corpus |
| AGENTS.md is an adopted cross-harness input standard (rel. 2025-08) | [external] | augmentcode.com harness guide (2026-04-16); harness.io blog (2026-03-16) | Input-side standardization happened | Anything about output-side demand |
| SKILL.md/Agent Skills open standard (2025-12-18), 40+ adopters; `.agents/skills/` interop dir | [external] | agentman.ai ecosystem report (2026-06-24); github.com/toverux/cantrips multi-harness research (2026-07-10) | Skill packaging is commoditizing across hosts | That lifecycle hooks will commoditize equally |
| MCP (agent-to-tool) and A2A (agent-to-agent) under Linux Foundation; no handoff standard surfaced | [external] + [derived] | gravity.fast (2026-07-10); braiviq.com (2026-06-25) | Adjacent layers standardized; handoff whitespace plausible | That no handoff standard exists anywhere ([unknown] — two search sessions, not a systematic sweep) |
| README badge/points to nonexistent `luanmorenomaciel/briefspec`; verification.md lists completed repo rename as pending | [direct] | `README.md:14`; `docs/verification.md:124`; gh 404 checks | Naming/identity drift | Scope of user-facing damage |
| Dist contains built 0.2.1 artifacts since 2026-08-03 | [direct] | `dist/`, `CHANGELOG.md:67-89` | A shippable increment exists today | That 0.2.1 gates all passed hosted |
| Schema v1/v2 pairs coexist; legacy migrated in memory | [direct] | `schemas/` (9 files); `delivery.py:359-386` | Compatibility posture is real | Long-term dual-schema cost is paid |

## Final recommendation

**ADVANCE WITH CONDITIONS**

- **Rationale:** the foundations are genuinely strong and genuinely rare —
  enforced contract semantics, a deterministic verified delivery pipeline,
  transactional installation, and honest release gating — aimed at a real,
  currently unstandardized surface. But the project is one billing issue and
  one private toggle away from being indistinguishable from vaporware, and its
  central product claim has never been measured on a human. Advance, with
  publication and measurement as hard conditions before further feature work.
- **Single most important next action:** register the PyPI names and publish a
  release (0.2.1 with existing artifacts, or 0.5.0 once its hosted gate runs) —
  this week, before any code changes.
- **Single most important thing to protect:** the truth-boundary discipline —
  a brief that never becomes more authoritative than its evidence, and a
  project that applies the same rule to itself. Features can be rebuilt; that
  credibility, once lost to overclaiming, cannot.
