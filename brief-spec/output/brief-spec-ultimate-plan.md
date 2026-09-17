# Brief-Spec Ultimate Project Plan

## Implementation update

The trust-correction program below has now been implemented in the local `0.5.0` candidate. The
authoritative current evidence is [the generated verification record](../docs/verification.md) and
the sanitized, source-fingerprinted `release/live-e2e-evidence.json`, not the point-in-time audit
table later in this synthesis.

Current release posture: 469 tests, 403 source checks, 459 final-wheel checks, deterministic
browser/PDF/local-audio gates, exact wheel/sdist clean-room installs, global and project rollback
proofs, and live matrices of Codex 8/8, Claude 8/8, OMP 4/4, Grok 4/4, and Kimi 4/4. The five-host
local authorization is green. Publication remains blocked by exact-SHA hosted CI, PyPI Trusted
Publisher setup, public-release account decisions, and explicit commit/tag/release authorization.

## Synthesis record

| Field | Value |
| --- | --- |
| Synthesis date | 2026-08-13 |
| Repository | `luanmorenommaciel/brief-spec` |
| Revision audited | `4adf20412028aa858a982c2149c3622327efa11a` |
| Branch | `main` |
| Source candidate | `0.5.0` |
| Published GitHub release | `v0.2.0` |
| Published PyPI distributions | None observed on 2026-08-13 |
| Review files read | 9 |
| Review volume | 3,724 lines; 61,237 words |
| Planning decision | Advance with conditions; freeze breadth until trust, publication, and product-evidence gates pass |

This plan synthesizes every review under `output/`, checks their important claims against the
repository and current public state, resolves contradictions, and converts the result into one
implementation program. A repeated model opinion is not treated as proof. A recommendation enters
the plan only when it is supported by repository evidence, primary-source ecosystem evidence, or a
clearly labeled product hypothesis with an evaluation gate.

## Executive decision

Brief-Spec should become the open, independently testable **agent-to-human handoff standard**:

> Different agents may reason differently. Their transfer of status, action, evidence, uncertainty,
> and delivery integrity should remain predictable and verifiable.

The durable product is not the number of harnesses, work types, or download formats. It is the
combination of:

1. a stable human contract;
2. an honest evidence vocabulary;
3. one canonical machine object;
4. deterministic projections;
5. cumulative, independently inspectable verification;
6. reversible installation into heterogeneous harnesses; and
7. conformance evidence that never claims more than was actually exercised.

The current `0.5.0` source is an unusually strong implementation candidate, but it is not ready to
be called the Ultimate project or a public standard. It has four classes of proof debt:

- **publication debt:** private repository, no PyPI distributions, hosted candidate CI rejected
  before execution, and public/candidate version drift;
- **product debt:** no completed human study demonstrates faster or more accurate recognition;
- **semantic debt:** classification, proof linkage, maturity labels, and typed-first rendering can
  imply more confidence than their evidence supports;
- **security and portability debt:** network resolution, renderer discovery, schema identifiers,
  archive bounds, and release gating need hardening before strangers verify untrusted artifacts.

Therefore the next move is a trust-correction release, not another feature release. Keep `0.5.0` as
the next public version, repair it before tagging, and do not publish intermediate `0.2.1`, `0.3.0`,
or `0.4.0` releases.

## The Ultimate north star

```text
optional Task-Spec authority contract
                ↓
host task → bounded local classification hint → type-shaped explanation
                ↓
Outcome Brief or Session Checkpoint
                ↓
canonical Brief-Spec delivery object
                ↓
deterministic Markdown · JSON · HTML · ZIP · optional PDF/audio
                ↓
structural · resolved · rendered · delivered verification
                ↓
versioned conformance receipt
                ↓
human judgment and, when applicable, independent Task-Spec acceptance
```

Two boundaries are non-negotiable:

- A Brief-Spec `DONE` means the handoff declares the agent task finished under the Brief-Spec
  workflow contract. It does **not** mean a Task-Spec task was independently accepted.
- A verification level describes what Brief-Spec checked. It does **not** prove the underlying
  engineering claim unless the claim is explicitly linked to evidence capable of supporting that
  lifecycle state.

This makes Task-Spec and Brief-Spec complements instead of competitors:

| Product | Core question | Authority |
| --- | --- | --- |
| Task-Spec | What may the agent do, what counts as success, and was it independently accepted? | Scope, execution contract, evidence policy, PRE/POST acceptance |
| Brief-Spec | What happened, what needs the human, what supports it, and how can the handoff be consumed? | Presentation, provenance, deterministic delivery, conformance |

## Current truth boundary, independently refreshed

The following state was observed during this synthesis, not copied from the model reviews.

| Boundary | Current observation | Evidence basis | Decision |
| --- | --- | --- | --- |
| Source | `pyproject.toml` declares `brief-spec 0.5.0`; `main` is `4adf204…` | Direct repository inspection | Implemented candidate |
| Working tree | Only `output/` is untracked during synthesis | `git status --short` | Review files and this plan are the only new paths |
| Local tests | The ordinary environment passes the full suite; the Copilot-optional test fails when the existing Superconductor `copilot` is added to `PATH` | Direct execution | Suite contains a reproduced hermeticity defect |
| Source verifier | `scripts/verify-release.py` passes 348 checks | Direct execution | Local structural gate passes |
| Formatting/lint | Ruff check passes; 102 files are formatted | Direct execution | Local style gate passes |
| GitHub repository | Canonical GitHub name is `luanmorenommaciel/brief-spec`; visibility is private | Authenticated GitHub metadata | Rename is complete; public adoption is not |
| GitHub release | Latest release is `v0.2.0`; no `v0.5.0` tag exists | GitHub release/tag inspection | Candidate is unpublished |
| Candidate hosted CI | Run `31708342030` on `4adf204…` rejected every matrix job before steps ran | GitHub Actions metadata | Infrastructure failure; zero candidate hosted test evidence |
| PyPI | `brief-spec`, PDF renderer, and audio renderer have no matching distributions | PyPI index probes | No immutable public package |
| Schema namespace | `brief-spec.dev` and `briefspec.dev` return no A/AAAA records; schema IDs are split across both | DNS and schema inspection | Not independently resolvable |
| Live harnesses at initial synthesis | Repository record then reported four passing hosts and Grok on Hold | Historical point-in-time evidence; superseded by the implementation update above | Preserve this row as the reason the Grok gate was repaired |
| Human benefit | Apex contains a protocol and empty template, not completed participant results | Direct repository inspection | Core cognitive claim remains a hypothesis |

The existing verification record must be corrected because it still calls the candidate an
uncommitted tree and still lists the already-completed GitHub rename as open. Its older failed CI
run should also be replaced by the exact current candidate run.

## Review council and reliability weighting

All nine files were read. They are not equally authoritative.

| Review | Repository access | Independent execution | Weight in this plan | Most valuable contribution |
| --- | --- | --- | --- | --- |
| Anthropic Claude Opus 5 | Full local and GitHub access | Classifier probes and extensive source tracing | High | Classifier honesty, truth-record drift, installer/runtime defects, plugin loading |
| OpenAI GPT-5 | Full local and GitHub access | Primary-source and source inspection | High | Claim-to-evidence linkage, SSRF boundary, exact-SHA release gating, conformance receipts |
| DeepSeek V4 Pro | Full local access | Tests, determinism, classifier and locator probes | High | Hermetic tests, locator grammar, cross-harness equivalence, re-entry study |
| DeepSeek V4 Flash | Full local access | Two suite runs and release verifier | High | Publication steel thread, adapter enforcement truth, suggest-default policy |
| Moonshot K3 | Full local access | Suite run and source/market inspection | High | Publish-and-prove framing, archive bounds, standard/spec opportunity, CI recipe |
| xAI Grok 4.6 | Full local and GitHub access | Current research via Exa/Tavily/native search | High | Status-first UX, maturity correction, work-item truth, scope freeze |
| Xiaomi Mimo 2.5 | Full local access | Repository inspection | Medium | Namespace complexity, onboarding, type-profile experiment |
| Z-AI GLM 5.2 | Local source available but public-source confusion | Mixed | Medium-low | Positioning and external-adoption urgency; factual public-state claims rechecked |
| Tencent Hunyuan 3 | Installed skill only; repository unavailable to reviewer | No project execution | Low for implementation facts | Valuable cold-start evidence: a private/unreachable project looks nonexistent |

Tencent's claims that schemas, adapters, tests, and parsers do not exist are false for the audited
checkout and are not included as defects. They are retained as evidence that a private repository
prevents an external reviewer from distinguishing “implemented privately” from “not implemented.”

## Consensus map

Counts below are thematic signals, not democratic votes. Each review contributes at most once to a
theme, and implementation decisions still require evidence.

| Theme | Reviews raising it | Synthesis verdict |
| --- | ---: | --- |
| Public distribution/installability is the immediate existential gap | 9/9 | Adopt as the first external gate |
| The human reading/re-entry thesis lacks completed evidence | 8/9 | Adopt; make a paired pilot a roadmap gate |
| The 160-prompt classifier gate is synthetic or circular | 8/9 | Adopt; rename it as a rule-consistency test and build a real corpus |
| Harness breadth/maturity outruns live conformance depth | 7/9 | Adopt; replace one “verified” label with evidence tiers |
| Naming, URLs, schema IDs, or compatibility surfaces are fragmented | 7/9 | Adopt; preserve legacy reads but define one write surface |
| Hosted CI and exact-candidate release binding are insufficient | 6/9 | Adopt; exact-SHA evidence must authorize publishing |
| Truth-boundary documentation already drifted | 6/9 | Adopt; generate and verify the record mechanically |
| Verification needs stronger security/attestation boundaries | 5/9 | Adopt; offline default, SSRF hardening, archive bounds, renderer trust |
| Type-aware content may increase reading cost or false confidence | 4/9 | Treat as an experiment; make status/action first in re-entry artifacts |
| Public schemas/conformance vectors are the path from tool to standard | 5/9 | Adopt for `0.6–0.7`, not as a last-minute release add-on |
| Multi-agent `work_items` are representational rather than end-to-end | 4/9 | Admit the limit; implement a minimal projection only after two live fixtures |
| No more renderers, harnesses, cloud services, or type expansion now | 8/9 | Adopt as a scope freeze |

## Contradictions resolved

### Publish `0.2.1` now versus repair and publish `0.5.0`

Some reviewers recommend publishing the already-built `0.2.1` immediately. This conflicts with the
explicit consolidation decision and would create another public version that does not represent the
current product. Decision: **do not publish an intermediate release**. Repair the unpublished
`0.5.0` candidate, obtain hosted proof, then publish it once.

### Require all five hosts versus stop letting Grok block the product — resolved

The previous acceptance plan calls Codex, Claude, OMP, Grok, and Kimi “verified” and requires all
five. At synthesis time, the evidence placed Grok on Hold. Decision: **repair and exercise the
native lifecycle path rather than weaken the acceptance policy**. Grok now passes its required 4/4
matrix using passive classification, one bounded Stop correction, and a native read/edit allowlist
inside disposable repositories. It is promoted only for the source-fingerprinted local candidate;
this is not hosted-CI or publication evidence.

### Keep types versus delete or hide them

Types are potentially useful, but the current benchmark does not measure natural-language quality
and the current rendering puts type sections before the handoff signal. Decision: **keep the eight
types, make inferred classification advisory, make status/action first in portable re-entry
artifacts, and measure matched-profile value**. Do not add types or allow custom primary profiles
before the evaluation.

### Full adapter breadth versus two-host focus

Removing built adapters would throw away tested work; calling all of them equally verified would
overclaim. Decision: **freeze the adapter count and certify incrementally**. Codex and Claude form
the reference conformance pair; OMP and Kimi remain supported with live-smoke receipts; Grok stays
Hold; Copilot, Cursor, and Goose remain experimental.

### Sign everything versus stay hash-only

Hashes prove byte correspondence but not producer identity. A new proprietary signature system
would create key-management debt. Decision: **keep unsigned receipts in `0.5/0.6`; add optional
DSSE/in-toto-compatible attestations only after a concrete external trust requirement appears**.

### Conform immediately to Agent Plugins 1.0 versus retain host manifests

The primary Agent Plugins 1.0 Working Draft does require `$schema` and `name`, and supports optional
metadata plus namespaced extensions. Current Brief-Spec manifests contain non-standard top-level
host fields. Decision: **build a conformant portable root manifest and move host-only fields under
extensions, but do not delete a host-native manifest until its real host installation still passes**.

## Product principles to freeze

1. **Same facts, multiple projections.** Model output never independently authors Markdown, JSON,
   HTML, ZIP, PDF, or audio variants.
2. **Status is workflow state, not truth.** `DONE` is constrained but is not independent acceptance.
3. **Evidence strength is explicit.** Direct, derived, and reported remain separate from pass, fail,
   and info.
4. **Verification says exactly what was checked.** “Structural,” “rendered,” and “published” are
   never collapsed into “verified.”
5. **Network access requires consent.** Verification is offline by default.
6. **Core stays dependency-free and deterministic.** Optional renderers remain separate packages.
7. **Classify locally and abstain safely.** No hidden or network model call in core.
8. **Hooks fail open.** Brief-Spec cannot trap a user in an agent session.
9. **Adapters do not define the standard.** The contract and conformance vectors do.
10. **No transcript warehouse.** Bounded state and explicit knowledge promotion remain mandatory.
11. **Portable user scope is authoritative.** Native host plugins are alternatives, not duplicates.
12. **Public claims expire.** Host/version conformance must be dated and invalidated by meaningful
    version changes.

## Release `0.5.0-RC2`: Trust correction

This phase fixes reproduced defects without expanding product breadth. It is the only phase allowed
to precede public `0.5.0`.

### P0.1 — Make classification honest

Current defects:

- rule matches inside “do not implement or modify code” can yield
  `implementation/high/inferred`;
- any two keyword-family matches produce `high` confidence;
- subject selection is independent and fixed-priority;
- the reported 160 prompts are eight sentences with only a changed integer;
- model-written marker metadata is accepted as `origin` and `confidence`, while `rule_ids` are lost.

Implementation:

1. Rename the existing corpus test to `test_keyword_rules_match_declared_vocabulary` and stop
   describing it as natural-prompt quality evidence.
2. Tokenize only enough to identify imperative/request spans; mask matches inside bounded negation
   windows such as `do not`, `don't`, `never`, `avoid`, and quoted prohibition blocks.
3. Require a score margin over the runner-up type; ties and low margins abstain to
   `general/low/fallback`.
4. Reserve `high` confidence for explicit and host-native decisions. Cap inferred decisions at
   `medium`.
5. Infer a subject only from affirmative text or host metadata. If work type falls back, default the
   subject to `general` unless the subject is explicit or host-supplied.
6. Persist a hook-authored classification sidecar containing `decision_id`, type, subject,
   confidence, origin, `rule_ids`, classification time, bounded-input digest, and adapter version.
   Do not persist the prompt.
7. Let the typed marker reference `decision_id`. When no authoritative sidecar is available, import
   marker metadata as `reported/low`, not `explicit/high`.
8. Preserve rule IDs and decision-record hash in canonical JSON. The hash is tamper-evidence, not a
   producer signature.

Required tests:

- every explicit type override remains authoritative;
- every host-native review context remains authoritative;
- negated, quoted, mixed-intent, terse, multilingual, malicious, and pivot prompts;
- zero inferred `high` classifications;
- no subject from a prohibited action;
- marker forgery cannot upgrade the authoritative sidecar;
- missing sidecar yields a visible reported downgrade;
- classification remains deterministic for identical bounded input and fixed time.

RC gate:

- named regression prompts from the reviews classify correctly or abstain;
- harmful confidently-wrong classifications: `0`;
- explicit and host decisions: `100%` correct on contract tests.

### P0.2 — Make verification offline-first and SSRF-resistant

Current `resolved` verification performs an HTTP `HEAD` against an artifact-controlled locator
unless `--offline` is supplied. It does not reject loopback, private, link-local, metadata, or
redirected private targets.

Implementation:

1. Make offline behavior the default.
2. Replace the negative `--offline` choice with explicit `--consent-network`; keep `--offline` as a
   compatibility alias that makes the default explicit.
3. Resolve every hostname and redirect hop before connection. Reject non-global IPv4 and IPv6,
   loopback, private, link-local, multicast, unspecified, and known metadata ranges.
4. Ignore environment proxy settings unless a separate `--allow-proxy` is supplied.
5. Cap redirects at 5, requests at 10 per delivery, headers at 64 KiB, timeout at 10 seconds, and
   fetched body at 16 MiB when content-hash verification is requested.
6. Distinguish `declared`, `publicly_reachable`, and `content_hash_matched`. A reachable URL is not
   promoted to truth.
7. Never use an artifact's self-declared `access=public` as the network-safety decision.
8. Continue refusing to execute command evidence.

Required security tests:

- literal, integer, IPv4-mapped IPv6, IPv6, DNS, redirect, proxy, and rebinding-style private
  targets;
- zero requests without consent;
- private/expired URLs remain unresolved warnings;
- body hashes verify only within the byte limit;
- timeouts and network failures do not mutate the workspace.

### P0.3 — Bound untrusted files and archives

Add default limits:

- input bundle: 64 MiB;
- archive members: 128;
- single expanded member: 64 MiB;
- total expanded bytes: 256 MiB;
- compression ratio: 100:1;
- no traversal, absolute names, special files, duplicate member names, or symlink entries;
- local evidence hashing: 256 MiB unless `--allow-large-artifact` is explicit.

All failures must occur before extraction or large allocation and must produce machine-readable
diagnostics.

### P0.4 — Remove implicit renderer code loading from trust verification

Implementation:

1. Add `brief-spec verify --no-plugins` and make it the default for core bundles.
2. Discover renderer entry points only when a target actually declares a renderer artifact and the
   user allows plugins.
3. Allow only registered renderer names and expected distributions.
4. Enforce `brief-spec>=X,<Y` compatibility and exact major/minor alignment for official renderers.
5. Record renderer distribution, version, and entry-point group in the manifest and receipt.
6. Document that installing a renderer is equivalent to trusting installed code.
7. Test a hostile/unrecognized entry point and prove it is never loaded by core verification.

### P0.5 — Preserve locally modified managed skills

Current behavior can overwrite a modified `SKILL.md` that still contains a Brief-Spec marker,
contradicting the installation documentation.

Implementation:

1. Ownership comes from a matching receipt path plus prior hash, not a substring marker alone.
2. A marker-bearing file with no matching receipt is foreign.
3. A receipt-owned file whose bytes differ from the receipt is locally modified.
4. On upgrade, preserve the modified file and place the candidate at `SKILL.md.brief-spec-new` (or
   an equivalent deterministic sibling); report a conflict with remediation.
5. `doctor --fix` never overwrites it without an explicit `--replace-modified` confirmation flag.
6. Setup-all rollback removes every temporary sibling it created.

### P0.6 — Fix runtime auto-detection precedence

Replace boolean-precedence environment sniffing with an explicit decision table:

1. explicit payload runtime/provider;
2. native stable session identifier;
3. mutually exclusive host environment markers;
4. deterministic default.

If Codex and Claude markers coexist, a Codex thread ID wins over inherited Claude variables. Add a
parameterized matrix for all host-marker combinations and a test for the reproduced
`CLAUDE_CODE_ENTRYPOINT + CODEX_THREAD_ID` case.

### P0.7 — Make human re-entry artifacts status-first

Interactive answers may use the type-specific explanation naturally, but exported re-entry
artifacts must lead with the decision signal.

Target order for Markdown, HTML, PDF, and default screen views:

1. Status;
2. Outcome;
3. Human action;
4. type and subject metadata;
5. type-specific explanation sections;
6. Proof;
7. Gaps;
8. Next;
9. Open;
10. provenance/artifacts/work items/integrity details.

Preserve the unchanged Outcome Brief and Checkpoint 1.0 inner fields. Extend the typed parser to
accept both old explanation-first and new brief-first outer ordering through `0.x`; render only the
new ordering. Keep Proof and Gaps expanded by default. Collapse canonical JSON and deep provenance.
Audio still consumes only the Spoken `Script`.

Acceptance:

- Status, Outcome, and Human action are visible in the first viewport at 1280×800 and 390×844;
- keyboard and print behavior remains green;
- all existing typed and legacy fixtures parse;
- canonical input remains byte-deterministic.

### P0.8 — Repair schema portability without breaking legacy readers

Before publication:

1. Choose one canonical schema namespace.
2. Either acquire and host immutable resources at `brief-spec.dev`, or use immutable repository
   release URLs plus a self-contained offline compound schema. Do not ship IDs for an unowned
   domain.
3. Use relative references inside the offline bundle.
4. Preserve old `briefspec.dev` IDs as read aliases in the resolver map through `0.x`; do not emit
   them for new artifacts.
5. Add AJV and Python `jsonschema` clean-room validation with no custom in-memory rewriting beyond
   the published compound bundle.
6. Differential-test the JSON Schema validator and Python semantic validator on generated valid and
   invalid objects.
7. Publish checksums and immutable version paths.

### P0.9 — Bind release publication to exact-SHA hosted evidence

The current tag-triggered release workflow runs source checks but is not mechanically dependent on
the full CI matrix for the tag SHA.

Implementation:

1. CI uploads a signed/attested candidate artifact containing exact SHA, matrix results, source
   verifier result, test summary, browser/PDF/audio results, and live-gate references.
2. The release workflow accepts only that artifact for the exact tag SHA. It must not rebuild.
3. A failed, missing, stale, or different-SHA CI artifact blocks the tag workflow before a draft
   release or PyPI OIDC request.
4. Protect the `pypi` environment with a human reviewer and restrict it to `release.yml`.
5. Keep build-once, draft GitHub release, Trusted Publishing, digest comparison, published clean
   install, and GitHub finalization.
6. Test restart after each stage and reject an existing PyPI file whose digest differs.
7. Add a workflow test proving a tag on a deliberately failing SHA cannot publish.

### P0.10 — Generate the truth boundary

Split the current working log from the public release record:

- `docs/verification.md`: generated, portable, exact revision and public evidence;
- ignored local run ledger: machine-specific absolute paths and candidate detail.

`verify-release.py --truth-boundary` must compare:

- package version, current SHA, tag, release, and changelog;
- GitHub canonical repository name and visibility;
- latest exact-SHA CI run and whether steps actually executed;
- PyPI project/file existence and digest;
- schema URL/compound-bundle availability;
- harness maturity versus retained conformance receipts;
- candidate versus published wording;
- completed prerequisites that are still listed as open.

The check must fail on the current stale “uncommitted tree” and “rename repository” statements.

### P0.11 — Replace “verified harness” with evidence tiers

Use these machine-readable maturity states:

| State | Required evidence |
| --- | --- |
| `available` | Adapter and deterministic fixtures exist |
| `install-verified` | Clean install, discovery, doctor, rollback, and uninstall pass on supported OS |
| `lifecycle-smoke` | Authenticated host exercised at least one scenario and emitted a valid delivery |
| `lifecycle-certified` | Required scenario matrix passes on pinned host version with conformance receipt |
| `hold` | Previously available surface is blocked by a known unresolved condition |
| `experimental` | Best-effort surface; no certification claim |

For public `0.5.0`:

- Codex and Claude: target `lifecycle-certified`;
- OMP and Kimi: minimum `lifecycle-smoke`, target certified later;
- Grok: `live-verified` after the required 4/4 matrix passed on Grok 1.0.3;
- Copilot, Cursor, Goose: `experimental` or `install-verified` only when evidence exists.

Every conformance receipt records host version, adapter version, scenario IDs, exercised
capabilities, limitations, timestamp, expiry, canonical digest, and artifact digests. A host major
version change invalidates certification. A minor change schedules revalidation.

### P0.12 — Make the suite hermetic

Inject or monkeypatch executable discovery in every doctor/installer test. Run two CI lanes:

1. no optional host CLIs on `PATH`;
2. deterministic fake/pinned host CLIs for all adapters.

The reproduced Copilot-optional test must pass in both environments. No test may depend on the
maintainer's actual host inventory, home directory, credentials, locale, timezone, network, or
existing receipts.

## Public `0.5.0` release gate

Publication occurs only after all RC2 work above and the following sequence.

### Repository-owned gates

```text
uv run ruff check .
uv run ruff format --check .
uv run python scripts/verify-release.py --truth-boundary
uv run pytest --cov=briefspec --cov-report=term-missing
```

Additional mandatory gates:

- 3 OS × Python 3.11–3.14 hosted matrix on the exact candidate SHA;
- no-CLI and all-fake-CLI hermetic lanes;
- zero-network core verification security suite;
- classifier adversarial regressions;
- status-first browser/mobile/print snapshots;
- PDF/audio optional package tests without making OpenAI network speech a pull-request gate;
- clean wheel and sdist installs for canonical and legacy CLIs/imports;
- exact-SHA release authorization test;
- Codex and Claude lifecycle certification matrix;
- OMP and Kimi smoke receipts;
- Grok 4/4 live evidence retained and source-fingerprinted;
- no unauthorized project changes.

### Account-owned gates

These require the repository owner and cannot be silently replaced by code:

1. restore GitHub Actions billing/spending or provide an equivalently isolated hosted runner;
2. decide and apply public repository visibility at the release boundary;
3. register Trusted Publishers for all three distributions;
4. acquire/control the canonical schema domain or approve immutable release URLs instead;
5. authorize one OpenAI audio smoke with a cost ceiling if network audio remains advertised;
6. approve the tag and public release.

### Release sequence

1. Freeze the exact SHA.
2. Run full hosted CI and produce its exact-SHA authorization artifact.
3. Run live host gates and issue sanitized conformance receipts.
4. Update the generated verification record.
5. Tag `v0.5.0` only after all repository gates are green.
6. Stage a draft GitHub release from the already-tested bytes.
7. Publish the identical core/PDF/audio distributions via PyPI Trusted Publishing.
8. Compare GitHub, CI, and PyPI digests.
9. Clean-install the public bytes and rerun the golden path.
10. Finalize the GitHub release.
11. Replace the local RC with `brief-spec==0.5.0` and aligned renderer packages.
12. Refresh user-scope integrations.
13. Upgrade only receipt-owned Converge and Nexo project paths.
14. Verify rollback and unrelated-worktree preservation.

### Public acceptance

From a clean machine/account with no private GitHub authorization:

```text
uv tool install "brief-spec==0.5.0"
brief-spec --version
brief-spec setup codex --scope user
brief-spec doctor codex --scope user --probe
```

The command must complete without private source access. The first verified Outcome Brief must take
less than five minutes after package installation on the golden-path harness.

## Release `0.6.0`: Prove human value and semantic integrity

`0.6.0` is an evidence release. It adds only the minimum contract changes needed to test and
strengthen the thesis.

### Natural-prompt classification corpus

Build a frozen, consented, de-identified corpus of 400 prompts:

- at least 40 per primary type;
- at least 60 intentionally ambiguous/fallback prompts;
- mixed intent, negation, quotation, pivots, terse prompts, non-native English, Portuguese, and
  malicious instruction text;
- no raw secrets, repository names, customer data, or transcripts;
- two human labels plus adjudication;
- annotator notes, disagreement record, corpus provenance, and immutable split.

Report:

- inter-rater agreement;
- macro and per-type precision/recall/F1;
- harmful-misroute rate;
- abstention/fallback rate;
- confidence calibration by origin;
- confusion matrix;
- override rate in explicit pilot sessions.

Release minimums:

- explicit override correctness: 100%;
- host-native context correctness: 100%;
- harmful confidently-wrong decisions: 0;
- macro F1 on held-out natural prompts: at least 0.85 for `0.6.0`, target 0.90 for `1.0`;
- no primary type recall below 0.75 for `0.6.0`, target 0.85 for `1.0`;
- abstention is reported and never optimized away by unsafe guessing.

### Apex paired human pilot

Participants and tasks:

- at least 12 engineers;
- at least 24 paired task readings;
- Codex and Claude reference outputs;
- all eight work types represented;
- raw/ordinary handoff versus Brief-Spec, randomized and blinded where practical;
- matched facts so format, not underlying quality, is the treatment.

Primary metrics:

| Metric | `0.6.0` gate |
| --- | --- |
| Median time to identify status, action, and proof | ≤15 seconds and ≥25% faster than baseline |
| Status/action correctness | ≥90% |
| Local/Git evidence-open success | ≥95% |
| Wrong workflow/lifecycle state | ≤2% |
| False-confidence delta | Must not worsen versus baseline |
| Evidence inspection rate | Must not fall because the card looks authoritative |
| Type-profile usefulness | Median ≥4/5 with no correctness loss |
| Checkpoint annoyance/dismissal | Reported; must not justify default enforcement if high |

Publish the protocol, aggregate results, confidence intervals where defensible, negative findings,
and exclusions. Do not publish raw transcripts. If the pilot fails, simplify the contract or type
surface; do not compensate by adding features.

### Claim-linked evidence in delivery `2.1`

Keep this deliberately smaller than a knowledge graph.

Add:

```text
evidence[].evidence_id
claims[].claim_id
claims[].statement
claims[].lifecycle_state
claims[].evidence_ids[]
verification_summary.requested_level
verification_summary.achieved_level
verification_summary.unresolved_count
```

Lifecycle states are separate from Outcome Brief status:

```text
proposed
implemented
locally_validated
live_host_validated
hosted_ci_validated
published
```

Rules:

- every material outcome claim links to at least one evidence ID;
- a `DONE` outcome cannot rely on unrelated passing proof;
- `published` requires a release/package locator and digest, not source code or a local test;
- `hosted_ci_validated` requires an exact-SHA hosted run that executed;
- reported evidence cannot alone produce a direct lifecycle claim;
- contradictory evidence is visible and blocks stronger state;
- delivery 1.0/2.0 remain readable through deterministic migration and visible warnings.

Adversarial fixtures include irrelevant tests, wrong checkout, stale commit, local pass represented as
CI, public claim backed by a private candidate, and altered receipt.

### Evidence locator grammar 2.0

Support without execution:

- `path`;
- `path:line[:column]`;
- `path:start-end`;
- `path::pytest-test-id`;
- `git:<commit>`;
- pull request and issue URLs/identifiers;
- URL fragments;
- artifact IDs bound through the manifest.

Unparseable plausible locators warn with a correction hint. Traversal and workspace escape remain
hard failures unless explicitly authorized.

### Task-Spec bridge

Add an optional, dependency-free upstream-contract reference rather than merging the products.

The canonical delivery may carry:

```json
{
  "upstream_contract": {
    "kind": "TaskHandoff/v1",
    "task_id": "...",
    "locator": "...",
    "sha256": "...",
    "authorization_state": "declared",
    "acceptance_state": "unknown",
    "acceptance_receipt": null
  }
}
```

Behavior:

- import only public/credential-free TaskHandoff fields;
- never copy signing keys, hidden holdouts, or credentials;
- verify the task/handoff digest when available;
- display Brief-Spec status and Task-Spec acceptance separately;
- update `acceptance_state` only from an independently verifiable Task-Spec receipt;
- a Brief-Spec `DONE` plus Task-Spec `unknown` renders “agent reports done; independent acceptance
  not observed,” never “accepted.”

This bridge is the flagship self-dogfood scenario: Task-Spec authorizes work; Brief-Spec explains
and delivers the result; Task-Spec independently accepts or rejects it.

### Research provenance normalization

Keep Exa, Tavily, Firecrawl, and future providers out of core dependencies. Add offline importers for
their exported result shapes and normalize them into one provenance vector containing:

- provider and provider result ID;
- query/request fingerprint, not secret credentials;
- source URL/locator;
- retrieval time;
- source content hash when available;
- normalized excerpt hash when used;
- direct/derived/reported basis;
- public/private/local access classification;
- transformation lineage;
- expiry/freshness policy;
- license or usage note when supplied.

CLI shape:

```text
brief-spec provenance normalize INPUT --provider exa|tavily|firecrawl --output provenance.json
brief-spec provenance validate provenance.json --offline
```

The normalizer makes no retrieval call. It must redact tokens and reject raw authentication fields.
Provider-specific SDKs may live in separate connector packages later if actual demand exists.

## Release `0.7.0`: Make conformance the ecosystem product

### Public schema registry and compound bundle

Publish:

- immutable versioned schemas;
- an offline compound schema;
- SHA-256 checksums;
- canonical valid examples;
- invalid examples with expected diagnostics;
- migration vectors for legacy markers, delivery 1.0, 2.0, and 2.1;
- renderer manifests and receipts;
- a schema-support policy.

Old published schema bytes never change. Corrections require a new identifier.

### Conformance test-vector suite

Create implementation-independent vectors for:

- parsing bounded Markdown;
- status semantics;
- typed classification migration;
- claim/evidence linkage;
- deterministic canonical JSON;
- deterministic core exports and ZIP;
- path and URL safety;
- manifests and receipts;
- verification-level promotion;
- Task-Spec upstream boundaries;
- research provenance imports;
- legacy compatibility.

Every vector contains input, expected normalized object, expected diagnostics, expected exit class,
and expected hashes where deterministic. Python, JavaScript, and one compiled verifier must agree on
the vectors before `1.0`.

### Executable harness conformance

Add `brief-spec conformance run HOST` and `brief-spec conformance verify RECEIPT`.

Scenarios:

- review + pull-request;
- exploration + codebase;
- implementation + feature;
- debugging + bug;
- Outcome, Orient, Teach, and Spoken across the set;
- one pivot;
- one fallback;
- one subagent projection where supported;
- installation, drift, rollback, uninstall;
- no unauthorized repository mutation.

Cross-host equivalence is defined carefully:

- exact equality for schema versions, allowed statuses, field presence/order, evidence vocabulary,
  verification semantics, and deterministic exports from the **same canonical object**;
- normalized equality for host/model/session metadata;
- adjudicated semantic equivalence, not byte equality, for independently generated natural-language
  claims;
- byte equality is never required between two different model responses.

### Out-of-tree harness adapter protocol

Freeze new built-ins until one external adapter passes. The protocol declares:

- detection commands;
- supported scopes and managed roots;
- event names and normalized mappings;
- final-output and pre-compaction behavior;
- session/model metadata;
- install operations as data, not arbitrary writes;
- uninstall ownership;
- security boundary and known omissions;
- conformance fixture compatibility.

Core validates an adapter plan before executing it. An adapter cannot write outside declared roots
or advertise a capability without a matching conformance scenario. Keep a small certified reference
set in core; community adapters remain separately versioned.

### Minimal work-item projection

Do not build an orchestrator. Implement only host-supplied bounded activity:

- parent and child opaque IDs;
- current activity;
- headline;
- last update;
- human action;
- result reference;
- freshness/omission state.

Rules:

- parent `DONE` cannot coexist with an unacknowledged `RUNNING` or `FAILED` child;
- completed child needs a result reference;
- missing host events are “unavailable,” not an empty proof of no subagents;
- no raw subagent prompts, transcripts, or tool output are retained;
- main task remains the only user-facing brief owner.

### CI consumption

Ship a pinned GitHub Actions recipe and a generic CI recipe:

```text
brief-spec validate delivery.json --strict --json
brief-spec verify bundle.zip --level rendered --offline --no-plugins --json
brief-spec conformance verify receipt.json --json
```

The recipe validates agent delivery; it does not approve a pull request or replace independent
project tests.

## Release `0.8.0`: Standardization and adoption

1. Publish an implementation-independent Outcome Brief 1.0, Checkpoint 1.0, and Delivery 2.1
   specification site.
2. Position Brief-Spec precisely among adjacent standards:
   - AGENTS.md: repository instructions;
   - Agent Skills: portable capabilities/instructions;
   - MCP: agent-to-tool/data connection;
   - A2A/handoffs: agent-to-agent transfer;
   - Task-Spec: authorized task and independent acceptance;
   - Brief-Spec: agent-to-human epistemic handoff and verified delivery.
3. Conform the portable root plugin to Agent Plugins 1.0 while retaining only the host-native files
   proven necessary by live tests.
4. Recruit three external pilot teams across at least two organizations.
5. Obtain one independent emitter and one independent verifier.
6. Publish a transparent compatibility and conformance dashboard generated from repository receipts,
   not invasive telemetry.
7. Establish governance: schema change process, compatibility policy, security response, conformance
   appeal/revocation, and maintainer ownership.
8. Submit the handoff/verification layer to an appropriate open standards venue only after public
   conformance evidence exists. AAIF is a candidate, not an assumed destination.
9. Evaluate optional DSSE/in-toto attestations only for a named workflow that requires producer
   identity.
10. Decide the future of PDF, audio, lifecycle enforcement, and each adapter from measured usage and
    maintenance cost.

## `1.0` definition

`1.0` is not a feature-count milestone. It requires all of the following:

- Outcome Brief and Checkpoint semantics frozen;
- status-first human rendering validated by the paired study;
- harmful misclassification and abstention metrics published;
- claim/evidence lifecycle semantics stable;
- offline verification safe by default;
- immutable public schemas plus compound offline bundle;
- at least two independent implementations passing conformance vectors;
- Codex and Claude lifecycle-certified, plus at least one additional certified harness;
- exact-SHA release authorization and artifact equality proven in production;
- public package installation and rollback proven on macOS, Linux, and Windows;
- three external teams complete real pilots;
- no critical/high security findings open;
- governance and migration policy published;
- legacy `briefspec` removal decision backed by usage/migration evidence;
- Task-Spec and research-provenance boundaries documented and tested;
- a public negative-results section explaining what Brief-Spec does not improve.

## Compatibility policy through `0.x`

Write only canonical forms; continue reading legacy forms.

| Canonical write surface | Legacy read surface retained through `0.x` | `1.0` decision |
| --- | --- | --- |
| `brief-spec` CLI | `briefspec` CLI | Remove only with migrator and usage evidence |
| `brief_spec` import | `briefspec` import | Same |
| `BRIEF_SPEC_HOME` | `BRIEFSPEC_HOME` | Same |
| `~/.local/state/brief-spec` | legacy state directory | Transactional migration required |
| `brief-spec:*` new markers | `briefspec:*` Outcome/Checkpoint markers | Outcome/Checkpoint 1.0 may retain historical markers permanently |
| canonical schema namespace | old IDs and local aliases | Old published IDs remain resolvable |
| `brief_spec.renderers` | `briefspec.renderers` | Remove only after plugin inventory |

Do not add another spelling, marker family, environment variable, state directory, or entry-point
group.

## Security threat model and release tests

| Threat | Required control | Release test |
| --- | --- | --- |
| Malicious URL evidence | Offline default, explicit consent, public-address validation each hop | SSRF matrix and zero-request assertion |
| Zip bomb/path escape | Pre-extraction limits, safe member validation | Ratio, count, size, traversal, symlink fixtures |
| Renderer plugin execution | No-plugin default, allowlist/version check | Hostile entry point never loads |
| Modified user skill overwrite | Receipt/hash ownership | Modified file survives setup/doctor/rollback |
| Wrong host auto-detection | Explicit precedence table | All mixed environment combinations |
| Forged classification metadata | Hook sidecar or reported downgrade | Marker cannot upgrade origin/confidence |
| Irrelevant passing proof | Claim/evidence IDs and lifecycle policy | Adversarial wrong-proof fixtures |
| Release from untested tag | Exact-SHA CI authorization artifact | Failed-SHA publication dry run blocks |
| Schema takeover/drift | Controlled immutable namespace and offline bundle | Old checksums and third-party validators |
| Receipt tampering | Canonical/manifest/delivery digest chain | Mutated byte and substituted receipt rejection |
| Hook availability failure | Fail open and one repair only | Injected exceptions and loop tests |
| Secret persistence | Bounded hashed state, no prompt content | State/privacy fixtures and redaction scans |

## Product evaluation program

### What to measure locally without telemetry

Add an explicit `brief-spec pilot export` command that emits only consented aggregate counters and
scenario IDs:

- classification origin/confidence/type;
- explicit overrides;
- checkpoint offered/accepted/dismissed;
- validation result;
- delivery completion result;
- verification level achieved;
- timing entered by the participant;
- evidence-open result entered by the participant.

Never export prompts, transcripts, source code, tool results, authentication data, raw paths, or
session tokens. The command is off by default and writes locally.

### Decision rules

- If status/action speed improves but evidence inspection falls, the release fails for false
  confidence.
- If type profiles do not improve comprehension, keep classification as metadata and simplify the
  visible profile layer.
- If automatic checkpoints are dismissed frequently, keep `suggest` as the only default and leave
  `enforce` experimental.
- If adapter maintenance exceeds the value observed on a host, retain portable skills and demote the
  native lifecycle layer.
- If audio/PDF do not affect accessibility, completion, or decision quality, keep them frozen
  optional packages.
- If the five-status vocabulary repeatedly fails real cases, change it before `1.0`; do not add team-
  specific status vocabularies afterward.

## Golden user journeys

### Journey A — First verified handoff in five minutes

1. Install immutable `brief-spec` from PyPI.
2. Run detected-host setup for Codex or Claude.
3. Run doctor/probe.
4. Perform one review task.
5. See Status, Outcome, and Human action first.
6. Open one proof locator.
7. Export HTML/JSON.
8. Verify offline.

### Journey B — Task-Spec-authorized implementation

1. Task-Spec emits a credential-free, digest-bound handoff.
2. A harness performs the task.
3. Brief-Spec emits the type-aware explanation and Outcome Brief.
4. Delivery links the upstream TaskHandoff digest.
5. Brief-Spec verifies the artifact and reports Task-Spec acceptance as unknown.
6. Task-Spec POST gate validates and accepts/rejects.
7. A new Brief-Spec projection may display the acceptance receipt without changing the original
   agent claim.

### Journey C — Research with Exa, Tavily, and Firecrawl

1. Research tool exports provider results.
2. Brief-Spec normalizes provenance offline.
3. A research Outcome Brief links material claims to normalized evidence IDs.
4. Private/expired sources remain visibly classified.
5. JSON/HTML/ZIP carry identical claim/provenance semantics.
6. Offline verification checks structure and hashes; consented network verification checks public
   reachability/content separately.

### Journey D — Cross-harness comparison

1. One scenario runs in Codex and Claude.
2. Each produces its own natural-language delivery.
3. Conformance checks stable vocabulary, field order, evidence semantics, lifecycle state, and
   verification behavior.
4. Model wording may differ; unsupported semantic divergence is adjudicated, not hidden by hashes.
5. Each host receives an expiring conformance receipt.

## Work breakdown and dependency order

| ID | Work item | Depends on | Exit evidence |
| --- | --- | --- | --- |
| ULT-001 | Correct verification record and public URLs | None | Truth-boundary check catches old drift |
| ULT-002 | Classifier negation, margin, confidence, subject gating | None | Named adversarial regressions pass |
| ULT-003 | Authoritative classification sidecar | ULT-002 | Forged marker downgrade test passes |
| ULT-004 | Offline-first SSRF-safe resolver | None | Security matrix passes with zero default requests |
| ULT-005 | Archive/file resource bounds | None | Bomb/size/path fixtures fail safely |
| ULT-006 | Renderer trust boundary | None | Unknown plugin never loads |
| ULT-007 | Receipt-based modified-file preservation | None | Modified skill survives setup/fix/rollback |
| ULT-008 | Runtime precedence decision table | None | Mixed-host environment matrix passes |
| ULT-009 | Status-first Markdown/HTML/PDF | None | First-viewport and backward-parser tests pass |
| ULT-010 | Canonical schema namespace/compound bundle | Account domain decision | AJV/Python validate without private repo |
| ULT-011 | Exact-SHA CI authorization | Hosted CI restored | Failed SHA cannot publish |
| ULT-012 | Maturity tiers and conformance receipts | None | Docs/CLI/receipt states agree |
| ULT-013 | Hermetic host-inventory suite | None | Bare/all-host PATH lanes pass |
| ULT-014 | `0.5.0` hosted/live gate | ULT-001–013 | Exact-SHA authorization artifact |
| ULT-015 | Public build-once release | ULT-014 + account gates | GitHub/PyPI digests match |
| ULT-016 | Published global/project rollout | ULT-015 | Doctors, project drift, rollback green |
| ULT-017 | Natural-prompt corpus | ULT-002 | Frozen corpus report |
| ULT-018 | Apex paired pilot | ULT-015, ULT-009 | Published aggregate results |
| ULT-019 | Claim/evidence delivery 2.1 | ULT-018 design findings | Adversarial lifecycle fixtures pass |
| ULT-020 | Locator grammar 2.0 | Real pilot locator sample | ≥95% eligible locator-open success |
| ULT-021 | Task-Spec upstream bridge | ULT-019 | DONE/ACCEPTED separation E2E passes |
| ULT-022 | Research provenance normalizers | ULT-019 | Exa/Tavily/Firecrawl golden imports |
| ULT-023 | Public schema/conformance vectors | ULT-019–022 | Cross-language validators agree |
| ULT-024 | Harness conformance command | ULT-012, ULT-023 | Expiring machine-readable receipts |
| ULT-025 | Out-of-tree adapter protocol | ULT-024 | External fixture adapter passes without core patch |
| ULT-026 | Minimal work-item projection | Two live subagent fixtures | Parent/child truth invariants pass |
| ULT-027 | CI verification recipes | ULT-023–024 | Brief-Spec validates itself on PR fixture |
| ULT-028 | Public mini-spec and positioning | ULT-023 | Independent reader can implement contract |
| ULT-029 | Independent verifier/emitter | ULT-028 | Two implementations pass vectors |
| ULT-030 | Governance and `1.0` migration | ULT-018, ULT-029 | Published policies and release gate |

## Recommended first pull-request sequence

Keep changes reviewable and independently reversible.

1. **PR 1 — Truth correction:** docs drift, README username/link fixes, current CI run, maturity wording,
   truth-boundary checker skeleton.
2. **PR 2 — Classification honesty:** negation, abstention margin, confidence cap, subject gating,
   regression corpus renaming.
3. **PR 3 — Classification provenance:** sidecar/decision ID, reported fallback, rule-ID preservation.
4. **PR 4 — Verification security:** offline default, consented public network policy, SSRF tests.
5. **PR 5 — Resource safety:** archive/member/file bounds and machine diagnostics.
6. **PR 6 — Installation/runtime safety:** modified-file preservation, runtime precedence, hermetic
   discovery tests.
7. **PR 7 — Renderer boundary:** no-plugin default, official allowlist/version checks, hostile plugin
   test.
8. **PR 8 — Status-first experience:** Markdown/HTML/PDF order, viewport/accessibility snapshots,
   legacy parse compatibility.
9. **PR 9 — Schema portability:** canonical IDs, offline bundle, third-party validation, differential
   tests.
10. **PR 10 — Exact-SHA release authorization and conformance tiers:** CI artifact, tag block,
    receipts, generated verification record.

Only after those merge and hosted/account gates pass should `v0.5.0` be tagged.

## Explicit non-goals through `1.0`

- no hosted Brief-Spec cloud service;
- no automatic telemetry or transcript upload;
- no second brain, memory graph, or automatic Nexo/Obsidian ingestion;
- no agent orchestrator, task scheduler, approval engine, or truth score;
- no default model-based or network classifier;
- no new primary work types or user-defined type marketplace;
- no new built-in harness before the adapter protocol and conformance receipts;
- no new renderer formats such as DOCX, slides, video, or EPUB;
- no plugin marketplace owned by Brief-Spec;
- no breaking removal of legacy `0.x` interfaces without migration evidence;
- no proprietary provenance/signature ontology;
- no release shortcut that bypasses exact-SHA hosted evidence;
- no claim that a structural doctor probe is a real host lifecycle run;
- no claim that deterministic bytes prove semantic truth.

## Risks and mitigations

| Risk | Consequence | Mitigation |
| --- | --- | --- |
| False confidence from polished cards | Users inspect less evidence | Claim links, status/lifecycle separation, pilot false-confidence gate |
| Classifier misroutes explanation | Trust erosion and wrong reading order | Abstention, inferred confidence cap, explicit override, natural corpus |
| Host API drift | Silent adapter breakage | Expiring conformance receipts and adapter version policy |
| Single maintainer | Release and security bottleneck | Generated gates, public vectors, governance, second implementation |
| Compatibility duplication | Permanent maintenance tax | One canonical write surface and explicit `1.0` decision |
| Private/public split | No adoption or external criticism | Public exact-release boundary and anonymous install gate |
| Renderer dependencies | Supply-chain and cross-platform burden | Optional packages, no-plugin core verification, usage-based investment |
| Schema/domain instability | Old artifacts become unverifiable | Immutable registry plus offline compound bundle |
| Network resolver abuse | Internal network access | Offline default and SSRF-grade public-address policy |
| “Standard” claimed too early | Ecosystem credibility loss | Require independent consumer/implementation before `1.0` |
| Task-Spec semantic overlap | Confused authority boundaries | Explicit DONE versus ACCEPTED rendering and digest bridge |
| Research provider drift | Import breakage or unverifiable sources | Versioned offline normalizers and raw-provider fixture corpus |

## Success dashboard without surveillance

Publish only aggregate, reproducible project evidence:

- public install success and time-to-first-handoff;
- exact-SHA CI matrix status;
- conformance receipts by host/version and expiry;
- classifier corpus metrics and abstention;
- pilot timing/correctness/false-confidence results;
- evidence-open success by locator kind;
- delivery verification accept/reject matrix;
- rollback exactness across OS;
- public schema and vector conformance implementations;
- external adopters/contributors who opt to be named;
- maintenance time per adapter and renderer.

Do not publish vanity download counts as proof of value. Downloads, stars, and installs are adoption
signals; they are not evidence that a Brief-Spec handoff is correct or useful.

## Final acceptance for the Ultimate project

The project earns the “Ultimate” label when a stranger can:

1. find one public canonical identity;
2. install immutable bytes anonymously;
3. produce the same bounded contract in multiple harnesses;
4. recognize status, action, and proof faster without increased false confidence;
5. verify a delivery offline without executing commands, plugins, or network requests;
6. resolve exactly what each claim's evidence supports;
7. distinguish agent-reported completion from local, live, hosted, published, and independently
   accepted states;
8. validate artifacts with a non-Python implementation;
9. install, upgrade, repair, and roll back without losing unrelated files;
10. understand the limits from the artifact itself rather than from maintainer context.

That is a stronger and more defensible destination than “supports every harness and download.” It
turns Brief-Spec from a sophisticated private tool into an open trust contract that can survive any
single model, host, renderer, or maintainer.

## Source review manifest

| Review file | SHA-256 |
| --- | --- |
| `output/anthropic-claude-opus-5.md` | `77ac961c577b8a34f09c9cb1e1a57603e5d7f4082a109cdc745029e03a500e96` |
| `output/deepseek-deepseek-v4-flash.md` | `b914d701c29635b97d38bbbaad4cfa442ab5a10267f73235ac8b01d6f6b1c566` |
| `output/deepseek-deepseek-v4-pro.md` | `305402c7f714d6d6840296c6579df8a864d697c05e1f733e02b6cb37bf4a8dd8` |
| `output/moonshot-k3.md` | `9d9b5eb6e6fa2f5ebfd746f1d524d72447f9d0e77a4c3b8da895969344081a10` |
| `output/openai-gpt-5.md` | `cb6337fdccf5c80e252e69574f695af74338930b1df24527246299a4f851086c` |
| `output/openrouter-xiaomi-mimo-v2-5.md` | `e5f69f59512c224c82dfe010c332ed618a6bb3228ba046ed8033ba08c99a0b0a` |
| `output/tencent-hy3.md` | `56a20288b8251307ae16bb53b8ed8c9e115cf4d38b0f88a357a1f1bb8d66abae` |
| `output/xai-grok-4.6.md` | `2c21eb47c2d31588848808c5a099480a6c75f812dc8754dc9f2cdf6484ad533b` |
| `output/z-ai-glm-5-2.md` | `ba46a1b7b56cd8411d9fbff760871fa4984ad8a3aac99b2972c1ce244491e4f9` |

## Primary ecosystem references checked

- [Agent Skills specification](https://agentskills.io/specification) — confirms the portable
  `SKILL.md` directory model and progressive disclosure.
- [Agent Plugins Specification 1.0.0](https://agent-plugins.org/specification) — current Working Draft;
  confirms required `$schema` and `name`, optional portable metadata, closed top-level fields, and
  namespaced client extensions.
- [Linux Foundation AAIF announcement](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)
  — confirms MCP, goose, and AGENTS.md as founding contributions and the neutral-governance
  opportunity. It does not prove AAIF interest in Brief-Spec.

<!-- brief-spec:typed:v1 type=planning subject=codebase confidence=high origin=inferred classified_at=2026-08-13T14:41:48.867754Z profile=1.0 -->
### Goal

Turn nine independent reviews and direct repository verification into one executable program for
making Brief-Spec a public, human-validated, secure, cross-harness handoff standard.

### Decisions

Keep `0.5.0` as the next public version, freeze breadth, fix the trust and release defects before
tagging, measure human value in `0.6.0`, make conformance the ecosystem product in `0.7.0`, and make
independent implementation and governance prerequisites for `1.0`.

### Approach

Correct the current truth boundary and reproduced defects first; publish exact tested bytes second;
then add claim-linked evidence, Task-Spec/research provenance bridges, public schemas, conformance
vectors, and external adapters only behind measurable gates.

### Sequence

`0.5.0-RC2 trust correction → public 0.5.0 → 0.6 human evidence and semantic integrity → 0.7
conformance → 0.8 standardization/adoption → 1.0 stable open contract`.

### Gates

No publication without exact-SHA hosted CI, safe offline verification, honest classifier behavior,
status-first rendering, correct maturity labels, anonymous installation, digest equality, and
rollback. No `1.0` without public human evidence, independent implementations, immutable schemas,
and governance.

<!-- briefspec:outcome:v1 -->
## Outcome Brief

Status: REVIEW
Outcome: Every review in `output/` has been synthesized, the trust-correction implementation is locally green, all five required live hosts pass, and exact candidate bytes are installed globally and in the intentional project overrides.
Human action: Restore exact-SHA hosted CI, complete the three PyPI Trusted Publishers and visibility decision, then separately authorize commit, tag, and publication when those account gates are green.

Proof:
- [direct/pass kind=test] `uv run pytest --cov=briefspec --cov-report=term-missing` — 469 tests passed at 86.25% coverage
- [direct/pass kind=command] `uv run python scripts/verify-release.py --truth-boundary` — 403 source release checks passed
- [direct/pass kind=file] `release/live-e2e-evidence.json` — Codex 8/8, Claude 8/8, OMP 4/4, Grok 4/4, and Kimi 4/4 authorized against the source fingerprint
- [direct/pass kind=file] `.briefspec/ultimate-release-candidate-dist/release-manifest.json` — exact final wheel/sdist hashes retained
- [direct/info kind=url] `https://github.com/luanmorenommaciel/brief-spec/actions/runs/31708342030` — exact candidate CI jobs were rejected before executing steps

Gaps:
- The plan does not itself restore GitHub billing, change repository visibility, register PyPI publishers, authorize publication, or run human participants.
- Public `0.5.0`, hosted exact-SHA validation, and the authorized network OpenAI audio smoke remain incomplete.

Next:
- Freeze the locally green candidate, satisfy the account-owned release gates, then run the hosted build-once publication sequence.
- Pre-register the natural-prompt corpus and Apex pilot before collecting any results.

Open:
- Whether the owner is ready to authorize the commit/tag/public-release sequence after hosted CI and Trusted Publishing pass.
- Whether the optional OpenAI speech smoke should be authorized before publication or remain explicitly unverified.
- Whether the paired pilot supports keeping type profiles visible by default.
<!-- /briefspec -->
<!-- /brief-spec -->
