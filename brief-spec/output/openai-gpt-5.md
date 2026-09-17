# Brief-Spec Independent Review — GPT-5

## Reviewer context

- **Provider and model:** OpenAI, GPT-5. The provider/model identity comes from available runtime metadata; it was not inferred from repository content.
- **Harness or interface:** Codex.
- **Date:** 2026-08-13, America/Sao_Paulo.
- **Repository URL:** Requested URL: `https://github.com/luanmorenommaciel/briefspec`. Git and authenticated GitHub metadata resolve it to the canonical private repository `https://github.com/luanmorenommaciel/brief-spec`.
- **Branch and commit inspected:** `main` at [`4adf20412028aa858a982c2149c3622327efa11a`](https://github.com/luanmorenommaciel/brief-spec/commit/4adf20412028aa858a982c2149c3622327efa11a), committed 2026-08-13T14:05:31Z.
- **Latest release observed:** [`v0.2.0`](https://github.com/luanmorenommaciel/brief-spec/releases/tag/v0.2.0), published 2026-07-31T20:40:31Z at tag commit `7ffe275b0c56358d7f0b13abe8a2363bfe61086a`. The release has no attached assets. No `0.5.0` tag or release was observed.
- **Materials available:** Authenticated GitHub repository metadata, releases, tags, actions, issues, pull requests, and the clean local checkout of the same default-branch commit; README, changelog, packaging metadata, architecture/compatibility/configuration/delivery/installation/verification/theory documentation, skills, schemas, both Python import surfaces, renderers, tests, scripts, pilot fixtures, and workflows. Existing files under `output/` were neither read nor incorporated.
- **Research providers used:** Native web search against current first-party sources; authenticated GitHub CLI/API; direct DNS/HTTP probes for declared schema and package endpoints. Retrieved 2026-08-13. No Exa, Tavily, or Firecrawl research was performed in this review.
- **Working-tree state:** `[direct]` The local checkout was clean and exactly matched `origin/main` at inspection time.
- **Source authority:** `[direct]` GitHub `main` and the local checkout were byte-aligned at the same commit, so GitHub `main` is authoritative for implemented source and the local checkout supplied line-level inspection. The published product remains `v0.2.0`; the `0.5.0` code on `main` is not treated as an equivalent published release.
- **Important limitations:** The repository is private, discussions are disabled, and there were no open issues or pull requests. No completed human pilot results are committed. The ignored live-host/release artifacts referenced by `docs/verification.md` are not independently reproducible from the repository alone. I did not rerun the test suite because the review contract authorized exactly one write, the designated review file; this review distinguishes repository-recorded local validation from validation executed during this review.

### State boundary at retrieval

| State | Review conclusion |
| --- | --- |
| Proposed | `[proposal]` Everything recommended in this review. |
| Implemented | `[direct]` Candidate `0.5.0` source is committed on GitHub `main`, including type profiles, delivery schema 2.0, eight harness definitions, renderers, installers, and release workflows. |
| Locally validated | `[direct]` The committed verification record reports 414 tests, 86.86% branch coverage, 348 source checks, 417 wheel checks, deterministic bundles, browser/PDF/audio checks, and clean-room installs. These results were observed as repository records, not rerun here. |
| Live-host validated | `[direct]` The repository records smoke passes for Codex, Claude Code, OMP, and Kimi, and a hold for Grok. It explicitly says the full matrix remains open. |
| Hosted-CI validated | `[direct]` Not for `4adf204…`. [Run 31708342030](https://github.com/luanmorenommaciel/brief-spec/actions/runs/31708342030) failed before any job step executed. This is infrastructure evidence, not a test failure and not hosted validation. |
| Published | `[direct]` Only GitHub release `v0.2.0` is published. Direct PyPI JSON endpoint checks for `brief-spec`, both renderer distributions, and `briefspec` returned HTTP 404 on 2026-08-13. |

## Executive verdict

Brief-Spec has crossed the line from a formatting convention into a compact protocol stack: local work-type routing, human handoff contracts, a canonical machine envelope, deterministic projections, evidence resolution, delivery receipts, and reversible harness installation. Its most original idea is not “better summaries.” It is a stable epistemic handoff that preserves what is done, what needs a human, what proves it, and what remains unknown across incompatible coding-agent runtimes.

The engineering foundations are unusually disciplined for an early project. Deterministic rendering, transaction-safe installation, compatibility migration, bounded state, and explicit publication boundaries deserve protection.

The project’s primary risk is now proof debt, not missing capability. The human-value thesis is supported by theory and synthetic fixtures, not completed user evidence. “Verified” currently conflates adapter tests, synthetic probes, smoke runs, and full host conformance. A `DONE` delivery needs only one passing proof item, even if it is unrelated to the outcome. Network evidence resolution also lacks an SSRF-grade boundary. Meanwhile, candidate scope has expanded by 9,917 inserted lines since `v0.2.0`, while current hosted CI executes zero steps and no `0.5.0` package is published.

The next release should add almost no breadth. It should make claim-to-evidence linkage enforceable, make verification offline-safe by default, certify only Codex and Claude against one paired live matrix, and measure whether engineers identify status, action, and proof faster and more accurately. If that steel thread does not show material human benefit, the standardization thesis should be narrowed before `1.0`.

## What Brief-Spec has become

`[derived]` The strongest mental model is **an epistemic presentation compiler for agent work**.

The input is not the model’s hidden reasoning or the whole transcript. The input is a bounded handoff written by the host agent: an explanation shaped for one work type plus either an Outcome Brief or a Session Checkpoint. Brief-Spec parses that bounded region into one canonical object, preserves source and evidence metadata, renders it into human and machine formats, and can verify successively stronger properties of the result.

```text
heterogeneous agent work
        ↓ host-specific lifecycle adapter
bounded, type-aware explanation
        ↓ stable human contract
canonical delivery object
        ↓ deterministic projection
Markdown · JSON · HTML · ZIP · optional PDF/audio
        ↓ independent checks
structure · evidence resolution · rendering · delivered bytes
```

That model is more defensible than “a universal agent UI.” Brief-Spec does not control how an agent reasons, what tools it has, or whether its claim is true. It controls the semantic shape of the final transfer of responsibility. The fixed slots—status, outcome, human action, proof, gaps, next, open—reduce re-parsing. Type profiles preserve meaningful variation between review, debugging, planning, research, and other work. Checkpoints support re-entry without claiming to be durable memory.

`[direct]` The implementation already reflects this compiler model: the bounded Markdown contract is parsed once; delivery schema 2.0 contains classification, ordered explanation sections, the legacy brief, provenance, artifacts, and work items; core renderers derive from that object; the ZIP manifest binds rendered files to the canonical hash; and the delivery receipt binds destination bytes. [`docs/delivery.md`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/delivery.md#L1-L53)

`[derived]` What Brief-Spec has not yet become is a standard. A standard requires independently usable schemas, conformance profiles, more than one implementation or at least independent consumers, governance, and evidence that the contract solves a repeated user problem. Today it is a strong single-project protocol candidate.

## Strongest foundations to protect

### 1. Truth boundaries are part of the product, not release prose

`[direct]` The product distinguishes `DONE`, `REVIEW`, `DECIDE`, `BLOCKED`, and `FAILED`; requires proof and explicit gaps; and repeatedly states that syntax, local validation, live-host behavior, hosted CI, and publication are not equivalent. The current README separates source candidate `0.5.0` from public release `0.2.0`, and the verification record separates five evidence boundaries. [`README.md`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/README.md#L24-L45), [`docs/verification.md`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/verification.md#L1-L24)

`[derived]` This is the trust nucleus. It is more valuable than any renderer or adapter because it prevents presentation polish from upgrading an unsupported claim.

### 2. One canonical object drives every projection

`[direct]` Markdown, JSON, and offline HTML are deterministic core renderings; required ZIP members are regenerated from embedded canonical JSON during verification; manifests include per-file hashes and a canonical hash; receipts remain outside the archive to avoid self-reference. [`src/briefspec/bundle.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/bundle.py#L148-L270), [`src/briefspec/verification.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/verification.py#L119-L230)

`[derived]` This prevents format-specific summaries from drifting semantically and makes independent byte verification possible. Keep “one object, many views” as a hard architectural invariant.

### 3. Installation is ownership-aware and reversible

`[direct]` The installer preflights foreign files, merges hooks, records hashes in receipts, snapshots all managed paths, restores exact bytes and modes on failure, makes multi-runtime setup transactional, and preserves modified/shared files on uninstall. Failure-path tests cover partial writes, pre-existing hook restoration, locally modified skills, nested-directory hooks, shared receipts, and malformed configuration. [`src/briefspec/installers.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/installers.py#L55-L158), [`tests/test_installer_failure_paths.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/tests/test_installer_failure_paths.py#L35-L121)

`[derived]` Cross-harness tools live in high-conflict configuration surfaces. Receipt-based ownership and rollback are differentiating safety properties and should remain stricter than host-native installers when the two conflict.

### 4. Privacy is bounded by construction

`[direct]` Session state stores counters, timestamps, classifications, hashes, and repair state—not raw prompts, tool results, assistant responses, or transcript contents. Transcript access is limited to the final 256 KiB and rejects symlinks; hook input is bounded to 1 MiB; hooks fail open. [`docs/architecture.md`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/architecture.md#L80-L110), [`src/briefspec/adapters/base.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/adapters/base.py#L88-L119)

`[derived]` Preserve the absence of a Brief-Spec cloud service and automatic transcript ingestion. It keeps the protocol inspectable and makes enterprise adoption easier to reason about.

### 5. Stable core semantics coexist with type-aware reading experiences

`[direct]` Eight work types have fixed explanation orders, while one unchanged Outcome Brief and three checkpoint modes remain the terminal contract. Explicit and host-supplied classifications take precedence; ambiguous inference falls back; sticky classification changes only on override or clear pivot. Legacy untyped briefs migrate in memory to `general + general`. [`src/briefspec/work_types.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/work_types.py#L60-L146), [`src/briefspec/delivery.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/delivery.py#L335-L415)

`[derived]` This is a good balance: predictable terminal semantics without forcing debugging, review, research, and operations into identical prose.

## Findings

### 1. Passing evidence is not bound to the claim it allegedly proves

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** Delivery validation accepts `DONE` when any proof item has `result=pass` and `basis` of `direct` or `derived`. It does not establish that the proof supports the outcome, a particular explanation claim, or the declared lifecycle state. Evidence items have no stable IDs and claims have no evidence references. [`src/briefspec/delivery.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/delivery.py#L541-L577)
- **Why it matters:** A formatter can reject missing proof while accepting irrelevant proof. That creates a dangerous “verified-looking” artifact whose bytes and shape are valid but whose central claim is unsupported. The stronger Brief-Spec’s presentation becomes, the more important calibration becomes.
- **Recommended response:** `[proposal]` Add stable evidence IDs and a minimal `claims[]` layer that links each material claim to evidence IDs and one explicit lifecycle state: proposed, implemented, locally validated, live-host validated, hosted-CI validated, or published. Preserve Outcome Brief status as workflow state; do not overload it with artifact lifecycle state. Require every `DONE` outcome claim to have at least one direct passing link and reject contradictory or weaker evidence.
- **What would verify the recommendation:** An adversarial fixture set in which irrelevant tests, stale commits, wrong repositories, locally passing checks presented as hosted checks, and published claims backed only by source code are all rejected; a human study should also show no increase in time-to-status.

### 2. Online evidence resolution is not safe enough for untrusted artifacts

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** At `resolved` level, any non-`private` `http` or `https` locator is sent a `HEAD` request with redirects handled by the standard URL opener. The code does not reject loopback, link-local, RFC 1918, private IPv6, non-public DNS answers, redirect-to-private targets, or DNS rebinding. The tests model a “private” URL only through the artifact’s self-declared `access` field. [`src/briefspec/verification.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/verification.py#L292-L317), [`tests/test_delivery_edge_cases.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/tests/test_delivery_edge_cases.py#L262-L297)
- **Why it matters:** Verifying a downloaded delivery can cause requests into the verifier’s network. This is an SSRF-class boundary even when requests use `HEAD` and no credentials are deliberately attached.
- **Recommended response:** `[proposal]` Make resolved verification offline by default. Require explicit `--consent-network`; resolve and validate every address and redirect hop; deny loopback/private/link-local/multicast/metadata ranges for IPv4 and IPv6; cap redirects, response headers, and total requests; and never let an artifact’s `access` declaration determine network safety. Consider separating `url-declared`, `url-publicly-reachable`, and `content-hash-matched` results.
- **What would verify the recommendation:** Unit and integration tests for literal and DNS-resolved private addresses, alternate integer/IPv6 forms, redirects, proxy variables, rebinding simulations, timeouts, and offline behavior; an independent security review of the resolver.

### 3. The core user-value thesis has not been tested with completed human evidence

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** The Apex pilot is explicitly synthetic, contains five fixtures, and supplies an empty results template. The design theory says the complete interaction has not been validated in a controlled human study. No completed pilot data is committed. [`pilots/apex/README.md`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/pilots/apex/README.md#L1-L22), [`docs/theory.md`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/theory.md#L28-L39)
- **Why it matters:** Brief-Spec’s primary promise is lower reading and re-entry cost. Contract tests, screenshots, and render hashes cannot demonstrate that outcome. Without user evidence, renderer breadth and adapter count optimize a hypothesis rather than a demonstrated job.
- **Recommended response:** `[proposal]` Make a paired, blinded, task-level usability/conformance pilot a release gate. Compare ordinary handoffs with Brief-Spec handoffs on correct status/action identification, proof opening, time, false confidence, and user preference. Publish anonymized aggregate results and the protocol, not transcripts.
- **What would verify the recommendation:** A preregistered pilot with natural tasks, multiple engineers, paired harness outputs, confidence intervals, failure examples, and an explicit threshold that can hold the release.

### 4. Release automation can publish without proving that the exact candidate passed the full CI matrix

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** The current `main` CI run for `4adf204…` failed with zero steps in every job. Separately, `release.yml` triggers directly on any `v*` tag and does not depend on a successful CI workflow for the exact tag SHA. Its build job runs source verification and package checks, but not the full OS/Python matrix, core tests, browser E2E, or renderer smoke jobs. The repository also reports that branch protection/rulesets are unavailable on its present private-plan configuration. [CI run](https://github.com/luanmorenommaciel/brief-spec/actions/runs/31708342030), [`.github/workflows/release.yml`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/.github/workflows/release.yml#L1-L52)
- **Why it matters:** Human policy currently prevents a tag, but the automation does not enforce the stated gate. A mistaken or compromised tag push can advance to a draft release and trusted PyPI publication without full candidate CI evidence.
- **Recommended response:** `[proposal]` Make publication consume an attested artifact from a successful CI run for the exact immutable SHA, or duplicate all required release gates in the release workflow. Protect the PyPI environment with a required reviewer, constrain release tags, and fail when the source commit is not the tested commit. Keep build-once and published-byte verification.
- **What would verify the recommendation:** A dry-run release from an intentionally failed CI SHA must be blocked; a successful exact-SHA run must produce one artifact digest used unchanged by GitHub and PyPI; a restart test must not rebuild or substitute bytes.

### 5. “Verified harness” is an overloaded maturity label

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** Compatibility documentation and the registry call Codex, Claude, OMP, Grok, and Kimi “verified.” The verification record simultaneously places Grok on hold and says the full five-host type/presentation matrix remains open. `doctor --probe` executes the bundled hook synthetically and explicitly does not prove host discovery or authenticated execution. [`docs/compatibility.md`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/compatibility.md#L14-L25), [`docs/verification.md`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/verification.md#L75-L95)
- **Why it matters:** Users need to know whether files can be installed, hooks parse a fixture, the host discovers them, the host executes a lifecycle, semantics match another harness, and the result was tested at a named version. One label cannot carry all six meanings.
- **Recommended response:** `[proposal]` Replace maturity adjectives with an executable capability receipt: install, discover, hook-execute, classify, terminal-repair, export, verify, rollback, version, observed-at, and limitations. A marketing tier may be derived only from the receipt. Mark Grok as partial until its hold clears.
- **What would verify the recommendation:** The compatibility table is generated from retained, sanitized conformance receipts; every displayed check has a reproducible scenario and expiry policy; a host-version change invalidates rather than silently preserves certification.

### 6. The canonical schemas are packaged but not independently retrievable

- **Severity:** high
- **Evidence label:** `[direct]`
- **Observation:** Schema IDs and absolute references use `https://brief-spec.dev/schemas/...`, but `brief-spec.dev` did not resolve during this review. Repository tests succeed by preloading every schema into an in-memory registry, and the release verifier skips URL references when checking local targets. [`schemas/brief-spec-delivery.schema.json`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/schemas/brief-spec-delivery.schema.json#L1-L20), [`tests/test_schema_contracts.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/tests/test_schema_contracts.py#L16-L38), [`scripts/verify-release.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/scripts/verify-release.py#L434-L455)
- **Why it matters:** A cross-harness standard must be consumable without importing Brief-Spec’s Python package or copying its private repository. Unresolvable IDs weaken independent validation, schema caching, and long-term artifact interpretation.
- **Recommended response:** `[proposal]` Publish immutable versioned schema resources and checksums under a controlled domain, plus a self-contained compound schema bundle for offline use. Keep stable IDs immutable; add content negotiation only if necessary. Test validation both with no network and through the public registry.
- **What would verify the recommendation:** Fresh validators in at least Python, JavaScript, and one non-Python/JS implementation validate canonical examples using the public IDs; an offline bundle resolves every reference; old IDs remain byte-stable.

### 7. Classification quality evidence is structurally circular

- **Severity:** medium
- **Evidence label:** `[direct]`
- **Observation:** The reported 160-prompt corpus is generated from exactly eight hand-written templates, one per class, with only an integer changed 20 times. Those templates contain the same keywords used by the regex classifier. The test therefore measures deterministic rule execution, not classification on natural or adversarial prompts. [`tests/test_work_types.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/tests/test_work_types.py#L24-L70), [`src/briefspec/work_types.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/work_types.py#L167-L213)
- **Why it matters:** Wrong type selection changes the entire reading order. Real prompts often combine implementation, debugging, review, research, and release intent; multilingual and terse prompts are absent.
- **Recommended response:** `[proposal]` Keep the local deterministic classifier, but evaluate it on a held-out, de-identified, naturally occurring corpus double-labeled by humans. Measure ambiguity/abstention separately. Include mixed-intent, negation, quoted instructions, terse requests, non-English prompts, pivots, and explicit overrides.
- **What would verify the recommendation:** Per-class precision/recall/F1 on a frozen external corpus; inter-rater agreement; calibration of high/medium/low confidence; a maximum harmful-misroute rate; and regression cases that cannot be edited merely to satisfy the current rules.

### 8. Harness extensibility is declarative at the capability layer but centralized at the lifecycle layer

- **Severity:** medium
- **Evidence label:** `[direct]`
- **Observation:** `HarnessAdapter` provides a useful capability record, but installation, hook rendering, diagnosis, CLI output, and special cases remain distributed across core `if runtime` branches. The adapter registry falls back to a common normalizer for five runtimes rather than isolating each native contract. Renderer extension is a true entry-point protocol; harness extension is not. [`src/briefspec/harnesses.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/harnesses.py#L12-L117), [`src/briefspec/adapters/registry.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/adapters/registry.py#L10-L25)
- **Why it matters:** Every new host expands the trusted core and multiplies ownership, event, path, shell, and rollback cases. That is the opposite of the low-maintenance standard Brief-Spec wants to become.
- **Recommended response:** `[proposal]` Freeze new built-in harnesses. Extract a versioned adapter protocol with declared paths, event mappings, render-decision rules, installation operations, security boundaries, and conformance fixtures. Keep only a small certified reference set in core.
- **What would verify the recommendation:** One out-of-tree adapter passes install/discovery/event/rollback conformance without changes to core; malformed adapters cannot write outside declared roots or claim unsupported capabilities.

### 9. Multi-agent support is representational, not end-to-end

- **Severity:** medium
- **Evidence label:** `[direct]`
- **Observation:** The event model recognizes subagent start/stop, and delivery schema 2.0 can carry `work_items` with parent IDs and activities. `process_event` does not translate subagent events into a work ledger, and `new_delivery` includes work items only when a caller supplies them. The browser E2E script injects a fixture manually. [`src/briefspec/models.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/models.py#L45-L53), [`src/briefspec/delivery.py`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/delivery.py#L288-L332)
- **Why it matters:** “Multi-agent activity” in the canonical schema may be read as a shipped lifecycle feature when it is currently a caller-populated representation. Automatically accumulating all subagent activity would also threaten the project’s bounded-state and privacy principles.
- **Recommended response:** `[proposal]` Do not build an orchestrator. Define a minimal host-supplied work-item projection with explicit freshness, parentage, result reference, and omission semantics. Only persist activity already exposed by the host and selected for the bounded handoff.
- **What would verify the recommendation:** Paired parent/subagent scenarios on two hosts show equivalent activities without transcript storage; stale and missing events remain explicit; the main task remains the only owner of the terminal brief.

### 10. Surface growth is outrunning product evidence and increasing cognitive load

- **Severity:** opportunity
- **Evidence label:** `[derived]`
- **Observation:** Since `v0.2.0`, `main` adds 9,917 lines across 105 files. The README is 592 lines and presents public/candidate installation, portable/native modes, eight harnesses, multiple policies, four core formats, two optional renderers, verification levels, state operations, and compatibility aliases. PDF and audio have substantial system-tool and verification surfaces, while their user benefit is unmeasured. [`README.md`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/README.md#L24-L83), [`packages/briefspec-renderer-pdf/pyproject.toml`](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/packages/briefspec-renderer-pdf/pyproject.toml#L5-L22)
- **Why it matters:** Brief-Spec exists to reduce reading cost, but adopting it currently requires understanding a large choice surface. Each optional format and host also consumes release, security, and compatibility budget.
- **Recommended response:** `[proposal]` Establish one five-minute golden path: install one immutable package, configure one of two certified harnesses, complete one task, open one HTML delivery, and verify it offline. Move compatibility, advanced formats, and native plugin alternatives behind progressive disclosure.
- **What would verify the recommendation:** Median clean-machine time-to-first-verified-handoff under five minutes; setup completion above 90%; no duplicate hooks; comprehension tests show users can explain public vs candidate and synthetic vs live without reading the architecture guide.

## Ten opportunities

### 1. Claim-linked evidence and lifecycle-state semantics

`[proposal]` Add stable claim/evidence IDs and require material claims to declare both evidence links and the strongest achieved lifecycle state. Keep workflow status separate.

- **User impact:** 5
- **Strategic leverage:** 5
- **Evidence confidence:** 5
- **Effort:** L
- **Risk:** medium
- **Suggested horizon:** next release

### 2. Offline-first, consented network verification

`[proposal]` Default `verify --level resolved` to local/Git checks; make public URL access an explicit, SSRF-hardened capability with precise result semantics.

- **User impact:** 5
- **Strategic leverage:** 5
- **Evidence confidence:** 5
- **Effort:** M
- **Risk:** medium
- **Suggested horizon:** next release

### 3. A real evidence-to-decision pilot

`[proposal]` Run a paired, blinded pilot on natural engineering tasks and publish aggregate time, correctness, proof-open, wrong-status, and trust results.

- **User impact:** 5
- **Strategic leverage:** 5
- **Evidence confidence:** 5
- **Effort:** M
- **Risk:** low
- **Suggested horizon:** next release

### 4. Executable harness conformance receipts

`[proposal]` Replace “verified/experimental” with timestamped, versioned, machine-readable capability results generated by live scenarios.

- **User impact:** 4
- **Strategic leverage:** 5
- **Evidence confidence:** 5
- **Effort:** M
- **Risk:** low
- **Suggested horizon:** next release

### 5. Public immutable schema registry and offline compound bundle

`[proposal]` Publish versioned schema IDs, checksums, canonical examples, migration vectors, and a no-network bundle usable by independent validators.

- **User impact:** 4
- **Strategic leverage:** 5
- **Evidence confidence:** 5
- **Effort:** M
- **Risk:** low
- **Suggested horizon:** next release

### 6. A single five-minute onboarding path

`[proposal]` Lead with one published install, Codex or Claude, suggest policy, one sample task, one HTML/JSON delivery, and one offline verification command.

- **User impact:** 5
- **Strategic leverage:** 4
- **Evidence confidence:** 4
- **Effort:** S
- **Risk:** low
- **Suggested horizon:** next release

### 7. Natural-prompt classification benchmark with abstention

`[proposal]` Replace template repetition as the quality claim with a frozen, double-labeled corpus and harmful-misroute metrics; keep deterministic rules as the implementation.

- **User impact:** 4
- **Strategic leverage:** 4
- **Evidence confidence:** 5
- **Effort:** M
- **Risk:** medium
- **Suggested horizon:** later `0.x`

### 8. Out-of-tree harness adapter SDK

`[proposal]` Turn lifecycle integration into a constrained adapter interface plus conformance kit, while retaining a small certified core set.

- **User impact:** 3
- **Strategic leverage:** 5
- **Evidence confidence:** 4
- **Effort:** XL
- **Risk:** high
- **Suggested horizon:** later `0.x`

### 9. Compatibility migration evidence, not only aliases

`[proposal]` Add inventory and migration reports showing who still uses `briefspec` paths, markers, schemas, and entry points; publish removal criteria before `1.0`.

- **User impact:** 3
- **Strategic leverage:** 4
- **Evidence confidence:** 4
- **Effort:** M
- **Risk:** medium
- **Suggested horizon:** later `0.x`

### 10. Optional signed delivery attestations

`[proposal]` After unsigned receipts prove useful, support an optional in-toto/DSSE-compatible attestation that binds canonical digest, renderer digests, producer identity, and verification policy without inventing a new cryptographic format.

- **User impact:** 3
- **Strategic leverage:** 4
- **Evidence confidence:** 3
- **Effort:** L
- **Risk:** high
- **Suggested horizon:** `1.0`

## Three highest-conviction bets

### Bet 1: Prove the human outcome before adding breadth

`[proposal]` Run the evidence-to-decision pilot and make its thresholds a release gate.

- **Why it dominates:** Every renderer, adapter, schema, and installer exists to reduce human re-parsing and preserve calibrated trust. If engineers are not faster or more accurate, no amount of surface completeness creates value. This bet decides whether the project should expand, simplify, or pivot.
- **User problem addressed:** “I received a long agent result and cannot quickly tell what happened, what needs me, or what proves it.”
- **Measurable outcome:** Compared with ordinary handoffs, lower median time to identify status/action/proof without lower correctness or evidence inspection; wrong-status rate at or below the release threshold; improved usefulness without increased false confidence.
- **What must be true before implementation:** A natural task corpus, a stable pilot protocol, privacy-safe collection, at least two harnesses producing comparable tasks, and predeclared hold criteria.

### Bet 2: Make verification semantically and network safe

`[proposal]` Bind claims to evidence, separate workflow status from lifecycle state, and make all network resolution explicit and hardened.

- **Why it dominates:** Brief-Spec’s strategic leverage is trust, not document generation. A beautiful deterministic artifact with irrelevant proof or unsafe resolution undermines the entire category.
- **User problem addressed:** “Can I tell exactly what this evidence supports, at which validation boundary, without the act of verification exposing my machine?”
- **Measurable outcome:** Zero accepted adversarial wrong-boundary fixtures; zero network requests without consent; 100% rejection of private-address and redirect bypass cases; no measurable regression in status-reading time.
- **What must be true before implementation:** A minimal claim model that does not become a general knowledge graph, migration rules from delivery 1.0/2.0, and a reviewed network-threat model.

### Bet 3: Make conformance the ecosystem product

`[proposal]` Certify a small reference set through executable receipts, then let adapters move out of core.

- **Why it dominates:** First-party sources show that skills are converging as a portable content format while hooks, plugins, subagents, and lifecycle behavior remain host-specific. Brief-Spec can become important by standardizing semantic output and proof of conformance, not by owning every host’s installation code forever. [Agent Skills specification](https://agentskills.io/specification), [Claude Code extension overview](https://code.claude.com/docs/en/features-overview), [GitHub Copilot customization overview](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/overview)
- **User problem addressed:** “Does this host really produce the same handoff semantics, and what exactly was tested?”
- **Measurable outcome:** Codex and Claude produce semantically equivalent canonical objects for the same scenario; receipts show every capability and limitation; a later external adapter can pass without a core patch.
- **What must be true before implementation:** Stable conformance scenarios, canonical equivalence rules, host-version capture, expiration rules, and a strict definition of “certified.”

## One contrarian bet

`[proposal]` **Freeze PDF, audio, and new harness work for one release; do not make them release-critical until the core handoff proves measurable user value.**

- **Strongest argument for it:** PDF/audio and five “verified” hosts create an impressive completeness story, but they add Playwright, Chromium, Poppler, `ffmpeg`, local speech, network speech, host-version drift, and matrix cost. None currently demonstrates the product’s central outcome. Removing them from the critical path concentrates scarce maintenance and research capacity on claim integrity, safe verification, onboarding, and real user evidence.
- **Strongest argument against it:** Spoken and downloadable experiences may be the differentiator for accessibility, mobile review, and long-session re-entry. Freezing them could make the product look like “just another Markdown schema” and lose learning about modalities that ordinary agent tools neglect.
- **Evidence needed to decide:** Format-level usage and completion rates; paired comprehension/listening tests; accessibility feedback; renderer-related setup failure rates; maintenance time per release; and evidence that PDF or audio changes a decision outcome rather than merely offering preference.

## What not to build

- `[proposal]` **No hosted second brain, transcript warehouse, or automatic knowledge ingestion.** It would erase the clean boundary between authoritative work, bounded presentation, and deliberate knowledge promotion.
- `[proposal]` **No agent orchestrator, task scheduler, or subagent control plane.** Represent host-supplied activity; do not compete with harness-native orchestration.
- `[proposal]` **No new built-in harness until the existing capability labels are replaced by conformance receipts and the current Grok hold is resolved or honestly downgraded.**
- `[proposal]` **No “AI truth score” or second-model judge.** It would add cost, privacy exposure, nondeterminism, and false authority. Validate links, bytes, states, and declared policies instead.
- `[proposal]` **No arbitrary custom primary work types before real corpus evidence shows the eight-type vocabulary is insufficient.** Open subject slugs already provide safe flexibility.
- `[proposal]` **No default network resolution of evidence.** Reachability is not truth, and untrusted locators are a security boundary.
- `[proposal]` **No proprietary provenance ontology or signature scheme.** Map to W3C PROV where useful and use in-toto/DSSE/SLSA-compatible attestation patterns if signatures become justified. [W3C PROV-O](https://www.w3.org/TR/prov-o/), [in-toto specifications](https://in-toto.io/docs/specs/), [SLSA verification guidance](https://slsa.dev/spec/v1.0/whats-new)
- `[proposal]` **No renderer zoo—DOCX, slide decks, video, custom themes—until format-level evidence proves demand.** Core JSON/Markdown/HTML/ZIP cover the standard’s essential roles.
- `[proposal]` **No breaking removal of legacy `briefspec` interfaces based only on code cleanliness.** Remove them only after migration inventory, explicit warnings, published tooling, and a strategic payoff justify the cost.
- `[proposal]` **No `1.0` based on feature count.** `1.0` should mean stable semantics, independently retrievable schemas, conformance governance, safe verification, migration confidence, and demonstrated user benefit.

## Proposed next-release steel thread

### Thesis

`[proposal]` A Brief-Spec delivery should let an engineer correctly identify the outcome state, required action, and supporting proof in under 15 seconds across two harnesses, then independently verify the local artifact without network access.

### User scenario

An engineer asks Codex and Claude Code to review the same bounded pull-request fixture. Each harness may reason and write differently. At completion, the engineer receives the same semantic handoff: review-specific explanation, terminal Outcome Brief, explicit lifecycle state for each material claim, and clickable evidence. The engineer opens the offline HTML, decides whether human review is required, opens proof, and runs a local verification command.

### Entry point

`[proposal]` One documented path after immutable package installation:

```text
brief-spec setup codex|claude --scope project
<perform normal review task>
brief-spec bundle handoff.md --output handoff.zip
brief-spec verify handoff.zip --level rendered --offline
```

No separate native-plugin path appears in the golden-path instructions.

### Classification behavior

`[proposal]` Use explicit or host pull-request context as `review + pull-request`. If only natural language is available, use the deterministic classifier and display its origin/confidence. Ambiguous mixed-intent prompts must fall back to `general` rather than silently choosing. Classification is sticky for the task and changes only on explicit override or clear pivot.

### Explanation behavior

`[proposal]` Use the existing review order—Scope, Verdict, Findings, Risk, Validation, Recommendation—followed by the unchanged Outcome Brief. Keep the first viewport limited to status, outcome, human action, achieved lifecycle state, unresolved count, and three evidence links. The full explanation remains available through progressive disclosure.

### Canonical data changes

`[proposal]` Introduce a narrowly scoped delivery `2.1`:

- Add `evidence_id` to proof, provenance, and artifact entries.
- Add `claims[]` with `claim_id`, `statement`, `lifecycle_state`, and `evidence_ids`.
- Define `lifecycle_state` as exactly: `proposed`, `implemented`, `locally_validated`, `live_host_validated`, `hosted_ci_validated`, or `published`.
- Add `verification_summary` containing requested level, achieved level, unresolved evidence count, and canonical verification time.
- Require `DONE` outcome claims to reference at least one direct passing item whose kind can support the declared state; publication requires a release/package locator, not a local test.
- Preserve Outcome Brief/Checkpoint 1.0 and accept delivery 1.0/2.0 through deterministic in-memory migration with explicit warnings.

Do not add arbitrary claim graphs, free-form state vocabularies, or model-generated confidence scores.

### Download or delivery changes

`[proposal]` Limit the steel thread to Markdown, canonical JSON, offline HTML, and ZIP. HTML provides stable anchors for each claim and evidence item, clear unresolved badges, and a copyable verifier command. ZIP verification regenerates every core projection from JSON and emits the claim/evidence verification summary. PDF and audio remain optional and outside the gate.

### Harnesses involved

`[proposal]` Codex and Claude Code only. Pin observed host versions in conformance receipts. OMP, Grok, Kimi, Copilot, Cursor, and Goose retain their existing status but cannot block or satisfy this release thesis.

### Security and privacy boundary

`[proposal]` No raw prompts, transcripts, tool inputs, tool outputs, credentials, or resume tokens enter the delivery. Local files must remain within the declared workspace; Git verification uses object lookup without checkout mutation; command evidence is never executed. URL evidence stays declared but unresolved in the default offline path. Network resolution requires explicit consent and the hardened public-network policy described in Finding 2.

### Automated tests

`[proposal]`

- Schema 2.1 meta-validation, canonical examples, and cross-language fixture validation.
- 1.0 and 2.0 migration, byte-stable 2.1 round trips, and no timestamp regeneration.
- Adversarial claim/evidence linkage and wrong-lifecycle-state fixtures.
- Offline-by-default and zero-request assertions.
- SSRF/redirect/DNS/IP/proxy test matrix for consented resolution.
- Equivalent Codex/Claude event fixtures and exact canonical-field comparison.
- Install, repeated setup, drift, rollback, uninstall, and nested-directory tests for only the two gated harnesses.
- HTML keyboard, mobile, print, evidence-anchor, and zero-external-request tests.
- Release workflow test that rejects a tag whose exact SHA lacks successful required CI evidence.

### Live acceptance test

`[proposal]` Run 12 natural review tasks through both Codex and Claude (24 handoffs) with at least six engineers. Randomize raw versus Brief-Spec presentation and harness order. Ask participants to identify status, human action, lifecycle state, and the best supporting evidence; then open the evidence and run offline verification. Retain only scenario IDs, timings, answers, versioned receipts, and aggregate ratings—no raw task content unless separately consented.

### Success metric

`[proposal]` Hold the release unless all are met:

- Median status/action identification time is at most 15 seconds and at least 25% faster than the raw-handoff baseline.
- Status/action correctness is at least 90%.
- Evidence-open success is at least 95% for locally accessible evidence.
- Wrong-lifecycle-state rate is at most 2%.
- Cross-harness semantic equivalence is at least 90% on required canonical fields.
- Offline bundle verification and installation rollback both succeed in 100% of acceptance runs.
- Trust calibration does not worsen: unsupported claims are not rated more trustworthy merely because they use Brief-Spec.

### Explicit exclusions

`[proposal]` No new harnesses, renderer work, cloud service, dashboard, telemetry backend, arbitrary work types, signed attestations, transcript ingestion, remote URL verification by default, or removal of legacy aliases.

## Evaluation plan

| Evaluation target | Method | Primary metric | Proposed release threshold | Failure interpretation |
| --- | --- | --- | --- | --- |
| Classification quality | Frozen, de-identified natural prompts; two human labels plus adjudication; mixed intent and non-English cases | Macro F1, per-class recall, harmful-misroute rate, abstention rate | Macro F1 ≥ 0.85; no class recall < 0.75; harmful misroute ≤ 3% | Rules do not generalize; expand fallback/explicit UX before vocabulary. |
| Explanation usefulness | Blinded paired comparison of raw and typed explanations on the same facts | Task-answer correctness and 1–5 usefulness | No correctness loss; median usefulness ≥ 4; ≥ 60% preference | Stable headings add boilerplate without improving decisions. |
| Time to identify status, action, and proof | Timed questions from first render; report median and p90 | Seconds to three correct answers | Median ≤ 15s and ≥ 25% faster than baseline; p90 ≤ 30s | Progressive disclosure or field order needs revision. |
| Evidence-open success rate | Ask participant to open the best evidence from HTML/CLI | Successful open / eligible attempts | ≥ 95% local/Git; unresolved URLs reported separately | Locators are not actionable even when structurally valid. |
| Wrong-status rate | Independent adjudicator compares declared workflow and lifecycle states with source evidence | Incorrect state / material claims | ≤ 2%; zero published claims backed only by local evidence | Core trust contract is unsafe; release holds. |
| Cross-harness semantic equivalence | Same scenario in pinned Codex/Claude; normalize allowed host metadata | Exact match on required fields plus adjudicated claim equivalence | ≥ 90% claim equivalence; 100% schema/state vocabulary match | Adapter semantics are not portable enough for certification. |
| Download completion | Instrument local acceptance runner, not product telemetry | Successful export/open / attempts; time and failure reason | ≥ 95% completion; median < 10s excluding optional tools | Delivery pipeline or onboarding remains too complex. |
| Delivery verification success | Verify pristine, tampered, stale, and unresolved bundles | True accept/reject; false accept rate | 100% pristine accept; 100% tamper reject; zero network by default | “Verified delivery” label is not defensible. |
| Installation and rollback reliability | Clean and dirty fixtures on macOS/Linux/Windows; injected failures | Exact byte/mode restoration; conflict preservation | 100% restoration and no foreign overwrite | Do not certify that host/OS combination. |
| User trust | Before/after trust rating plus evidence-inspection behavior and calibration questions | Calibration error, false-confidence delta, inspection rate | No false-confidence increase; evidence inspection not lower than baseline | Presentation is masking uncertainty; simplify or add friction. |

`[proposal]` Publish the evaluation protocol, corpus construction method, aggregate results, exclusions, and failed cases. Do not publish cherry-picked screenshots as adoption evidence. Use bootstrap confidence intervals for timing/correctness where sample size permits, and report sample size prominently.

## Roadmap recommendation

### Now

1. `[proposal]` Freeze feature breadth and declare the next release an evidence/conformance release.
2. `[proposal]` Fix the unsafe URL resolver boundary and switch to offline default.
3. `[proposal]` Reconcile every “verified” label with the actual live matrix; downgrade Grok or clear its hold.
4. `[proposal]` Repair hosted CI availability and bind publication to successful exact-SHA required checks.
5. `[proposal]` Publish immutable schemas and an offline compound bundle.
6. `[proposal]` Design the natural-task pilot and claim/evidence 2.1 migration before changing the schema.

**Now gate:** No tag until security tests, exact-SHA hosted CI, public schema resolution, and the two-harness acceptance protocol are green. Local results alone do not satisfy this gate.

### Next

1. `[proposal]` Ship delivery 2.1 claim/evidence links with backward-reading support for 1.0/2.0.
2. `[proposal]` Generate Codex and Claude conformance receipts from paired live scenarios.
3. `[proposal]` Run and publish the evidence-to-decision pilot.
4. `[proposal]` Replace the README’s candidate-first breadth with the five-minute immutable golden path.
5. `[proposal]` Publish identical core artifacts to GitHub and PyPI only after the pilot and technical gates pass.

**Next gate:** All steel-thread metrics pass; no critical/high unresolved resolver or claim-state defect; published bytes match the tested artifact; reinstall and rollback from published packages pass.

### Later

- **Later `0.x`:** `[proposal]` Build the natural-prompt classifier benchmark, migration inventory, and out-of-tree adapter protocol. Certify at most one additional harness through the new process. Evaluate whether PDF/audio produce measurable benefit before returning them to the release-critical matrix.
- **`1.0`:** `[proposal]` Freeze core Outcome Brief, Checkpoint, evidence-link, lifecycle-state, and conformance semantics only after at least two independent consumers validate the public schemas, compatibility migration is exercised on real installations, and governance/security processes exist.
- **Post-`1.0`:** `[proposal]` Consider optional signed attestations and broader ecosystem certification if unsigned delivery verification is used in real workflows and identity trust is a demonstrated need.

### Reject or defer

- `[proposal]` Reject cloud memory, orchestration, truth scoring, and automatic ingestion.
- `[proposal]` Defer additional formats, hosts, arbitrary types, and signatures until the current thesis and maintenance budget are measured.
- `[proposal]` Defer breaking legacy-interface removal until usage evidence and migration tooling exist.

### Dependency and gate map

```text
safe offline verifier ─┐
claim/evidence design ─┼─> delivery 2.1 fixtures ─> paired live conformance ─┐
public schema registry ┘                                                    ├─> human pilot ─> publish
hosted CI restored ───────> exact-SHA release gate ─────────────────────────┘

pilot fails ─> narrow/simplify the product, not expand the matrix
```

## Risks and failure modes

### Technical risks

- `[direct]` Host lifecycle contracts differ in event names, stdout semantics, project/user scope, plugin discovery, and stop control. A common event enum can hide behavior that is not actually equivalent.
- `[direct]` Deterministic core output depends on canonical timestamps and serialization; optional PDF/audio determinism also depends on browser, font, Poppler, speech, and codec behavior.
- `[derived]` Absolute schema IDs without a stable registry can strand old artifacts or force package-specific registries.
- `[derived]` Claim/evidence linking can become a graph platform if not kept minimal.
- `[derived]` Compatibility code can preserve inputs while accidentally changing warnings, rendering, or lifecycle behavior.

### Product risks

- `[unknown]` Stable fields may reduce re-parsing, but they may also train users to scan the card and stop inspecting source evidence.
- `[unknown]` Automatic checkpoints may interrupt more than they help in short or fast-moving sessions.
- `[derived]` Too many modes, formats, policies, scopes, and harnesses can recreate the cognitive load the product aims to remove.
- `[unknown]` Five status words and eight work types may not cover real team semantics, but expanding them without corpus evidence would worsen portability.

### Security and privacy risks

- `[direct]` Consented URL resolution currently permits requests to destinations based on untrusted locators without public-network enforcement.
- `[direct]` Hooks execute local code at privileged lifecycle boundaries; host trust controls remain essential and hooks are not a security boundary.
- `[derived]` Evidence labels, locators, Git revisions, local paths, and session references can reveal sensitive repository or organizational metadata even without raw transcripts.
- `[derived]` HTML/ZIP/PDF/audio are untrusted artifacts when received externally; parsers and optional system tools expand the attack surface.
- `[derived]` A hash-only receipt proves byte correspondence, not producer identity or authorization.

### Ecosystem risks

- `[external]` Portable Agent Skills are converging, but each host continues to expose distinct hooks, plugin structures, subagent behavior, and policy controls. Brief-Spec can be squeezed between a portable skill format and rapidly changing native UX. [Agent Skills](https://agentskills.io/home), [GitHub Copilot hooks](https://docs.github.com/en/copilot/reference/hooks-reference), [Kimi hooks](https://moonshotai.github.io/kimi-code/en/customization/hooks)
- `[derived]` Calling one implementation a “standard” before independent consumers exist may reduce credibility.
- `[derived]` A private repository with no open discussion surface cannot yet support transparent standard governance.

### Maintenance risks

- `[direct]` Eight harnesses, dual naming, two schema generations, two renderer entry-point groups, multiple installation modes, and three packages multiply release paths.
- `[derived]` Host-specific shell/path rules will drift faster than the core semantic contract.
- `[derived]` Optional renderers can consume disproportionate maintenance because their dependencies and output formats vary by operating system.

### Adoption risks

- `[direct]` The current public release is `0.2.0`; candidate docs describe `0.5.0`; PyPI packages are absent. A new user cannot follow the candidate’s canonical package path from an immutable public registry.
- `[derived]` The current README asks users to understand too much before their first success.
- `[unknown]` There is no repository-backed evidence of active external users, repeated usage, or willingness to install lifecycle hooks.
- `[derived]` Teams may reject enforced response structure if it adds visible boilerplate or conflicts with local reporting conventions.

### Supply-chain risks

- `[direct]` The core has no runtime Python dependencies and GitHub Actions are pinned to full SHAs, which reduces exposure.
- `[direct]` Optional PDF/audio packages introduce Playwright/Chromium and system multimedia/document tools; the release workflow uses trusted publishing and build attestations but is not bound to a successful full CI run.
- `[direct]` Published `v0.2.0` has no release assets, and its commit is unsigned; current `0.5.0` packages do not exist on PyPI.
- `[derived]` A future adapter marketplace would execute installation and hook logic and therefore needs stronger isolation, signing, and declared-write boundaries than renderer plugins.

## Open questions

1. `[unknown]` Which recurring user segment feels the re-parsing problem most acutely: solo developers, staff engineers supervising parallel agents, reviewers, incident responders, or team leads?
2. `[unknown]` Does Brief-Spec reduce decision time without reducing evidence inspection or increasing false confidence?
3. `[unknown]` Which fields are actually used after ten repeated exposures, and which become ritual boilerplate?
4. `[unknown]` Is `REVIEW` a terminal workflow state or a handoff state that teams will confuse with code review approval?
5. `[unknown]` Should one Outcome Brief support multiple material claims with different lifecycle states, or should the contract remain one-outcome-only?
6. `[unknown]` What evidence kind is sufficient for each lifecycle state, and who owns that policy: Brief-Spec, a project profile, or a conformance suite?
7. `[unknown]` How often does deterministic local classification select a harmful profile on real, mixed-intent, terse, or multilingual prompts?
8. `[unknown]` Do users want automatic checkpoints, manual checkpoints, or host-native compaction summaries supplemented only by an Outcome Brief?
9. `[unknown]` Which two harnesses should define the reference conformance profile after Codex and Claude, if any?
10. `[unknown]` Is multi-agent activity useful in the final handoff, or does it expose implementation detail that users do not need?
11. `[unknown]` Are PDF and audio accessibility requirements, sharing formats, or novelty features? Which usage outcome justifies their release cost?
12. `[unknown]` What compatibility window is acceptable before `briefspec` aliases can be removed, and how will actual usage be measured without invasive telemetry?
13. `[unknown]` Who will own schema governance, security response, compatibility decisions, and conformance certification if external adopters appear?
14. `[unknown]` Is a private repository intentional for the candidate phase, and if so, what is the planned path to independently inspectable standard development?
15. `[unknown]` What level of producer identity or signature is required beyond local byte receipts, and by which concrete customer workflow?

## Evidence ledger

| Evidence label | Repository locator or external source | Observation / publication date | What it proves | What it does not prove |
| --- | --- | --- | --- | --- |
| `[direct]` | [README truth boundary and product model](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/README.md#L21-L45) | Observed 2026-08-13 | Main calls itself candidate `0.5.0`, public release `0.2.0`, and standardizes handoff rather than reasoning. | That users obtain the claimed benefit. |
| `[direct]` | [Candidate package metadata](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/pyproject.toml#L5-L42) | Observed 2026-08-13 | Distribution is `brief-spec` 0.5.0, dependency-free at runtime, with canonical and legacy CLIs. | Publication or installability from PyPI. |
| `[direct]` | [GitHub `v0.2.0` release](https://github.com/luanmorenommaciel/brief-spec/releases/tag/v0.2.0) | Published 2026-07-31; observed 2026-08-13 | `v0.2.0` is the latest visible published GitHub release and has no attached assets. | Candidate `0.5.0` readiness. |
| `[direct]` | [Current main commit](https://github.com/luanmorenommaciel/brief-spec/commit/4adf20412028aa858a982c2149c3622327efa11a) | Committed 2026-08-13; observed 2026-08-13 | Exact revision reviewed and its GitHub/local alignment. | Hosted checks or publication. |
| `[direct]` | [Verification boundary record](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/verification.md#L8-L24) | Record updated 2026-08-12; observed 2026-08-13 | Repository explicitly separates source, local, live, hosted, and published states. | Independent reproduction of ignored local artifacts. |
| `[direct]` | [Recorded local checks](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/verification.md#L26-L73) | Record updated 2026-08-12; observed 2026-08-13 | Repository reports 414 tests, coverage, determinism, renderer checks, and clean-room artifacts. | That this review reran them or that hosted CI passed. |
| `[direct]` | [Recorded live-host matrix](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/docs/verification.md#L75-L95) | Record updated 2026-08-12; observed 2026-08-13 | Codex/Claude/OMP/Kimi smoke passes and Grok hold are explicitly recorded with versions. | Full type/presentation conformance or current behavior after host updates. |
| `[direct]` | [Current hosted CI run](https://github.com/luanmorenommaciel/brief-spec/actions/runs/31708342030) | Run 2026-08-13; observed 2026-08-13 | Every required job failed before executing steps; exact `4adf204…` is not hosted-CI validated. | A product defect; no test ran. |
| `[direct]` | [CI matrix](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/.github/workflows/ci.yml#L15-L197) | Observed 2026-08-13 | Intended OS/Python, plugin, hook, browser, PDF, audio, and clean-room coverage. | Actual execution for the candidate. |
| `[direct]` | [Release workflow](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/.github/workflows/release.yml#L1-L174) | Observed 2026-08-13 | Build-once, SHA sums, attestation, trusted publishing, PyPI digest verification, and staged GitHub release are implemented. | A dependency on full successful CI for the exact tag SHA. |
| `[direct]` | [Canonical delivery schema 2.0](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/schemas/brief-spec-delivery.schema.json#L1-L173) | Observed 2026-08-13 | Closed schema for source, classification, explanation, brief, provenance, artifacts, and work items. | Live availability of its `$id` or semantic truth of instances. |
| `[direct]` | [Local schema registry in tests](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/tests/test_schema_contracts.py#L16-L38) | Observed 2026-08-13 | Repository tests resolve schemas by loading all local documents. | Independent resolution through `brief-spec.dev`. |
| `[direct]` | `https://brief-spec.dev/` direct DNS/HTTP probe | Retrieved 2026-08-13 | The declared schema domain did not resolve in the review environment. | Permanent global unavailability; DNS can change. |
| `[direct]` | [Claim validation logic](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/delivery.py#L541-L577) | Observed 2026-08-13 | `DONE` requires some direct/derived passing proof, not a claim-specific proof link. | That agents routinely exploit the gap. |
| `[direct]` | [URL resolver](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/verification.py#L233-L317) | Observed 2026-08-13 | URL evidence can trigger `HEAD`; private access labels warn; commands are not executed. | SSRF-safe address/redirect enforcement; none is present in the inspected code. |
| `[direct]` | [Deterministic bundle implementation](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/bundle.py#L148-L270) | Observed 2026-08-13 | Core files, canonical hash, manifest, deterministic ZIP metadata, and external receipt template derive from one object. | Producer identity or underlying claim truth. |
| `[direct]` | [Bundle verification](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/verification.py#L119-L230) | Observed 2026-08-13 | Manifest sizes/hashes, canonical JSON, regenerated core outputs, offline HTML, and optional renderer checks are implemented. | That evidence referenced inside is true or accessible. |
| `[direct]` | [Installer transaction code](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/installers.py#L762-L919) | Observed 2026-08-13 | Managed assets, receipts, snapshots, rollback, and legacy migration are implemented per runtime. | Every real host upgrade/path combination. |
| `[direct]` | [Installer failure-path tests](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/tests/test_installer_failure_paths.py#L35-L121) | Observed 2026-08-13 | Foreign-file preflight and exact rollback failures are exercised. | Live behavior on all supported OS/host versions. |
| `[direct]` | [Harness registry](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/src/briefspec/harnesses.py#L120-L277) | Observed 2026-08-13 | Five hosts are labelled verified, three experimental, with declared capabilities. | That every declared capability passed a current live gate. |
| `[direct]` | [Classifier corpus](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/tests/test_work_types.py#L24-L70) | Observed 2026-08-13 | 160 cases are generated by repeating eight templates 20 times. | Natural-prompt classification quality. |
| `[direct]` | [Apex pilot](https://github.com/luanmorenommaciel/brief-spec/blob/4adf20412028aa858a982c2149c3622327efa11a/pilots/apex/README.md#L1-L22) | Observed 2026-08-13 | Pilot questions and thresholds exist; fixtures are explicitly synthetic. | Completed participant evidence. |
| `[direct]` | PyPI JSON endpoints for `brief-spec`, `brief-spec-renderer-pdf`, `brief-spec-renderer-audio`, and `briefspec` | Retrieved 2026-08-13 | All four endpoints returned HTTP 404 at retrieval. | Future availability or the existence of packages under different names. |
| `[external]` | [Agent Skills specification](https://agentskills.io/specification) | Retrieved 2026-08-13; publication date not stated | A portable `SKILL.md` directory format, metadata constraints, resources, and progressive disclosure are externally specified. | Uniform hooks, lifecycle, installation, or conformance across hosts. |
| `[external]` | [Claude Code extension overview](https://code.claude.com/docs/en/features-overview) | Retrieved 2026-08-13; publication date not stated | Claude distinguishes skills, hooks, subagents, teams, MCP, and plugins. | Brief-Spec integration quality. |
| `[external]` | [GitHub Copilot customization overview](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/overview) and [hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference) | Retrieved 2026-08-13; publication date not stated | Copilot exposes instructions, hooks, skills, agents, MCP, and plugins, with surface-specific hook behavior. | Candidate live conformance. |
| `[external]` | [Kimi plugins](https://moonshotai.github.io/kimi-code/en/customization/plugins.html) and [hooks](https://moonshotai.github.io/kimi-code/en/customization/hooks) | Retrieved 2026-08-13; publication date not stated | Kimi plugins package skills and hooks; hooks have a defined configuration and lifecycle mechanism. | That project-scope Brief-Spec hooks exist or all plugin behavior is stable. |
| `[external]` | [OMP skills](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md) | Retrieved 2026-08-13; live document | OMP discovers skills from multiple providers with explicit precedence/collision behavior. | Stable compatibility with the candidate’s specific extension code. |
| `[external]` | [Goose](https://block.github.io/goose/) | Retrieved 2026-08-13; publication date not stated | Goose supports skills, MCP extensions, recipes, subagents, and multiple providers. | Native lifecycle hooks suitable for Brief-Spec. |
| `[external]` | [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) | Published 2022-06-16; retrieved 2026-08-13 | The dialect used by Brief-Spec is a published JSON Schema specification with bundling/vocabulary mechanisms. | Availability or correctness of Brief-Spec’s own schema IDs. |
| `[external]` | [W3C PROV-O](https://www.w3.org/TR/prov-o/) | W3C Recommendation 2013-04-30; retrieved 2026-08-13 | A stable interoperable provenance model exists and supports domain specialization. | That Brief-Spec is PROV-compliant. |
| `[external]` | [SLSA v1 verification guidance](https://slsa.dev/spec/v1.0/whats-new) | SLSA 1.0 finalized 2023; retrieved 2026-08-13 | Provenance only mitigates relevant threats when verified against expectations. | That SLSA is the right format for human handoff evidence. |
| `[external]` | [CloudEvents](https://cloudevents.io/) | Retrieved 2026-08-13; publication date not stated | A common event envelope standard exists for cross-environment event description. | That coding harnesses emit CloudEvents or that adopting it would solve lifecycle semantics. |

## Final recommendation

ADVANCE WITH CONDITIONS

**Rationale:** `[derived]` Brief-Spec has a coherent and differentiated core: a bounded, type-aware, evidence-preserving handoff compiled into deterministic, verifiable deliveries. Its implementation discipline is ahead of its product evidence. The candidate should advance only by shrinking the next-release thesis to semantic evidence integrity, safe offline verification, exact-SHA release gates, two-harness conformance, and measurable human benefit.

**Single most important next action:** `[proposal]` Turn the next release into the two-harness evidence-to-decision steel thread and hold publication until its security, conformance, and human-outcome thresholds pass.

**Single most important thing to protect:** `[direct]` Protect the invariant that a Brief-Spec artifact can never become more authoritative than the evidence and validation boundary it represents.
