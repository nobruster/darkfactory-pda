# Attack Playbook — how the adversary refutes a swimlane plan

Converge Pass 4 (Consensus), Steps 1–2. This is the lens a *different* model
(`--adversary`, default `codex`) attacks the Pass 3 plans through. The author is
Claude; the same model reviewing its own plans produces agreement, not
consensus. If the adversary is unavailable, fall back to a fresh same-model
session with **no memory** of writing the plans — weaker, but still not
self-review in the same context.

The output of this playbook is a ranked objection list feeding Step 3 (SHARPEN),
where each objection is FIXED in a plan or ACCEPTED with a named owner.

## Output contract & dispatch (v0.4.0 — CLI-dispatchable, cross-family, structured)

When run through `cvg review --adversary <engine>`, this playbook is the framed
`--system-prompt-file`, and the invariants tighten:

- **Cross-family, not just a brand.** The adversary must be a **different model
  family** than the author (Claude = anthropic): `codex` (openai), `kimi`
  (moonshot), or `gemini` (google) — never another anthropic model, because
  self-preference bias is measured and family-correlated. Same-model-fresh-context
  is the explicitly-weaker last resort.
- **Attack per swimlane, then per leg.** Pass 3 is now `swimlanes/<seam>/`
  (a lean PRD + one file per leg). Attack each leg file independently; tag every
  objection with its `swimlane` (and `leg` where applicable).
- **Emit the stamped objection-log JSON**, conforming to
  [`objection-log.schema.json`](objection-log.schema.json) — your engine/model/
  **family**, the input **sha256 hashes** you were handed (provenance), and
  `objections[]` (id, severity, rank, attack_class, swimlane/leg, location,
  evidence, cites). You **attack and log**; you do **not** write the FIX or choose
  the fork — those are the author's and the human's. `verdict ∈ PASS|REVISE`.
- **Bound the loop (≤ 3 rounds)**; stop when 0 open critical/high remain — a
  further round only dresses nitpicks as findings.

The gate (`scripts/check-consensus-gate.sh`) validates that JSON's structure +
provenance (it re-hashes the live plans), never the prose — so "a different model
attacked the real plans" is auditable, not grep-spoofable.

## The stance: default to refuted

A merely-plausible plan step is **not** "fine". The adversary's job is to state
*why a step might be wrong*, per plan, or the objection stands. Silence is not
passing. Frame the adversary as a skeptical principal engineer who did **not**
write these plans and is paid to find what bites at build time — not to bless.

Three rules the adversary holds:

1. **One plan at a time.** Refutation is per-plan and ranked by build-time
   damage, so the cheapest-to-kill wrong idea dies first — at the plan, before
   any component, output, or interface exists.
2. **Cite the section.** Every objection names the specific plan section it
   attacks (e.g. the section that defines a lane's output, or the section
   describing the interface this layer consumes). An objection with no citation
   is not actionable.
3. **Lower altitude, do not invert it.** Pass 4 hardens what Pass 3 sketched.
   No new files, no new scope. A "requirement" that appears here is drift — log
   it as an open question and push it back up the chain (Pass 1/2/3).

Demand the **5–7 highest-leverage objections**, ranked by build-time damage.

## The refutation prompt (hand this to the adversary)

Give the adversary two things: the refutation stance, and the ground truth of
*your* stack (data stores, build/transform steps, output contract, serving
layer, and any hard invariants such as single-writer constraints or timezone
rules). Fill the bracketed slots from your project — do not ship the example
stack below as if it were the user's.

> You are a skeptical principal engineer. You did NOT write the plan below and
> your job is to REFUTE it, not bless it. Default to refuted: for every step you
> cannot prove wrong, state precisely why it *might* be wrong at build time.
>
> Stack context (ground truth you attack through):
> `<the source → prep → transform → output → serving pipeline for THIS project>`.
> `<where the data lives; e.g. $DATA_STORE>`. `<the ingest/build step and what
> it produces — which tables/columns/lineage stamps, and whether it preserves
> defects for a later cleaning stage>`. `<any concurrency invariant, e.g.
> single-writer>`. `<what the serving layer is allowed to read, and what it must
> never read below>`.
>
> Return the 5–7 highest-leverage objections, ranked by build-time damage. Each
> objection MUST cite a specific plan section and say what breaks if it ships
> unchanged. Do not propose new scope; if you find a missing requirement, flag
> it as an open question, do not add it.

Run it **once per plan** — one plan file at a time, never on two plans at once.

> **Example — a DuckDB/dbt warehouse project.** The stack context might read:
> "Postgres → DuckDB → dbt medallion (bronze/silver/gold) → FastAPI + MCP
> serving. The warehouse is the project's DuckDB file. The ingest step ATTACHes
> Postgres and lands it into raw tables with defects intact and lineage stamps
> (`_ingested_at`, `_source_watermark`, `_schema_drift`). DuckDB is
> single-writer. Serving reads the gold layer read-only, never below gold." And
> the two per-plan runs are the warehouse/transform plan, then the serving plan.
> Substitute your own stack's shape here.

## The bite list — what actually bites YOUR stack at build time

Pattern-5 domain intelligence: a mature pass already knows where *its* stack
breaks and points the adversary at those seams first. The bite categories below
are generic; under each, one clearly-labeled example shows the shape of a real
bite so you can hunt the equivalent in your own stack.

### 1. Brownfield assumptions about the source/raw contract

If your ingest step lands **defects intact** — cleaning is a later stage's job,
not the landing's — attack any plan step that assumes something unproven about
the raw columns, the lineage stamps, or the real value domains. Common shapes:

- **Freshness/lineage stamps.** A plan that trusts a stamp to mean more than it
  does (a "landed" clock is not an "event" clock).
- **Deduplication key.** A dedup keyed on a column the source does not actually
  make unique per business event.
- **Canonical vocabulary.** A plan that reads a status/category/label straight
  off raw that the source never emits — it must be a *derived* value via an
  owner-gated mapping, not invented.
- **Type fidelity.** Money/precision types silently recast; timezone-aware
  timestamps mishandled.

> **Example — the raw layer of a DuckDB/dbt project.**
>
> - **Dedup:** a `duplicate_order` injector re-inserts the latest order verbatim
>   with a *new* `order_id`, so `order_id` stays unique while the duplicate row
>   survives. Any dedup keyed on `order_id` is wrong — it must dedup on a
>   business signature.
> - **Canonical vocab:** `orders.status` is `placed/shipped/delivered/returned/
>   cancelled` — there is **no** raw `fulfilled` status. A plan reading a
>   `fulfilled_rate` straight off raw has invented a status; it must be a derived
>   metric via an owner-gated status→health map.
> - **Types:** `DECIMAL` money never recast to float; timestamps stay tz-aware.

### 2. Build order — nothing built before what it reads

When the build graph is the contract (a DAG-driven transform tool, a dependency
order between layers), attack any inversion:

- An output layer materialized before the layer that conforms it; a conformed
  layer before the layer that types it; any transform model before its source
  lands.
- A serving endpoint or tool built before the output it reads exists.
- The ingest step and the transform step **overlapping** when the store is
  single-writer — prep, then transform, never concurrent. Readers may run
  concurrently with the one writer.

> **Example — DuckDB + dbt.** Gold materialized before silver conforms it;
> silver before bronze types it; any dbt model before its raw source lands; an
> MCP tool built before its mart exists; `make land` and `dbt run` overlapping
> when DuckDB is single-writer.

### 3. Cross-lane interface — the output → serving contract

The seam that most often gaps at build time is where one lane publishes a
contract and another consumes it:

- A serving endpoint that needs an output column the producing lane never emits
  (the classic: the consumer reads a column the producer's plan never lists).
- The consumer *declaring* output columns instead of *consuming* them. The
  output contract is owned by the producing component via a schema declaration;
  a column does not exist for the consumer until the producer has committed it
  with a type. Attack any consumer plan that names columns the producer never
  promised.
- **Atomic generation.** Mid-transform, one endpoint could read a refreshed
  output while another reads the stale one — inconsistent cross-endpoint
  answers. The fix is a shared per-generation run id; the consumer binds to the
  latest *fully-published* generation. Attack any "no serialization needed"
  claim.
- **Freshness clock.** A single "landed" timestamp measures ingest cadence — it
  can report "fresh" while the newest business event is old/late-arriving. A
  freshness output needs to carry **both** clocks (landed and event) and expose
  the lag between them. Attack any freshness output that exposes only one.
- **Boundary type conversions.** A type that is safe inside the transform SQL
  but trips a downstream consumer at the language boundary (e.g. a tz-aware
  timestamp that must be cast to text/epoch before a client library accepts it).
  Attack the query core where this bites, not the transform layer where it is
  safe.

> **Example — a dbt gold layer feeding FastAPI + MCP.** Serving reads
> `gold.customer_revenue` but the medallion plan only emits
> `gold_revenue_by_category`; serving names columns the gold `schema.yml` never
> promised; endpoints diverge mid-`dbt run` without a shared `_gold_run_id`; a
> freshness mart exposes only `_ingested_at` and not
> `event_to_reportable_lag = _ingested_at − max(<event_ts>)`; tz-aware
> timestamps trip DuckDB's pytz requirement in the FastAPI/MCP query core
> (dbt SQL is safe).

## Step 2 — grounding (drift vs. spec + decision records)

The plans answer to the authoritative spec and any recorded decisions (e.g.
`docs/tech-spec-*` and `docs/adrs/*` if the project keeps them), not the author
model's memory. For each plan, list every drift as:

`plan section ↔ spec/decision-record section ↔ the conflict`

citing **both** sides. Hunt four drift shapes:

- **Uncovered claim** — the plan says it covers a requirement it does not.
- **Out-of-scope build** — it builds something the spec marked out-of-scope, or
  a metric never asked for.
- **Decision-record violation** — it contradicts a recorded decision (for
  example, an ADR pinning a single-writer constraint, or a strict layering
  order between transform stages).
- **Number disagreement** — a freshness target, latency budget, or success
  metric that differs from the spec (e.g. a p95 window the plan invented).

If no decision records exist, ground against the spec alone and log
"decision records absent" as a **blocking** open question — never fabricate
decision-record content.

## From objection to resolution (feeds Step 3)

Every objection surfaced here ends in exactly one of:

- **FIX** — the relevant plan is revised **in place** to resolve it. The diff on
  the plan file is the record. Reference the objection id (e.g. C3) where the
  fix lands so the gate can see one resolution per objection.
- **ACCEPT** — recorded as a known risk with a **named owner** and the reason to
  proceed (e.g. `ACCEPT — owner: data-eng — reason: single-writer store under
  concurrent load is out of demo scope`).

Nothing is silently dropped. The gate
(`scripts/check-consensus-gate.sh`) refuses to pass if any logged objection has
no resolution or any accepted risk has no owner.
