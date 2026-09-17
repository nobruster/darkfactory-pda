# Grounding checklist — run-and-reconcile the brownfield

Pass 2 grounds by *running* the real source, not summarizing a doc. This is the
protocol behind Step 2. Every ADR you write in Step 3 must trace to something you
observed here.

The steps below are stated as portable principles. Adapt each command to your
stack: substitute your build/ingest step, your data store, your source schema,
and your transform/serving layers. A single worked example (a dbt/warehouse
project) is shown in labeled fenced blocks so the shape is concrete — treat it as
*one illustration*, not the required stack.

## 1. Bring the terrain up and populate it

Start the real source and run the project's data-prep command so there is
something live to observe. Whatever the stack, the goal is: a running source and
freshly-ingested data in the store your pipeline actually reads.

> **Example — a dbt/warehouse project:**
>
> ```bash
> make up            # start the source (e.g. Postgres; schema auto-applied on first boot)
> $SEED_CMD          # generate clean, correlated fixture data
> $LAND_CMD          # ingest source -> your data store (full refresh)
> ```
>
> Here the ingest step copies each source entity into raw/source tables in the
> project's warehouse via a read-only connection, and credentials never enter the
> connection string. Your stack's ingest will differ; the property to preserve is
> *a faithful, repeatable full refresh into the store you query*.

## 2. Reconcile parity (source → store)

For each entity, the source count and the ingested count must match after a clean
full refresh. Compare the count in the source against the count in the store your
pipeline reads.

> **Example — a dbt/warehouse project:**
>
> ```bash
> # source
> make psql   # then: SELECT count(*) FROM public.orders;
> # ingested
> $QUERY_STORE "SELECT count(*) FROM raw.raw_orders;"
> ```

- **Match** → ingestion is faithful; record the parity as evidence if a spec claim
  depends on it.
- **Mismatch** → do NOT hand-wave it. Either the ingest is stale (re-run your
  data-prep command) or a defect changed rows mid-run. A persistent, explained
  mismatch is itself a grounding fact (e.g. *which failure modes survive into your
  raw/source tables*) and deserves its own ADR.

## 3. Inventory what layers actually exist

Enumerate the schemas / datasets / namespaces present in your data store and
confirm which layers exist versus which are still absent. Whatever the pipeline is
*supposed* to build, verify what is actually there today.

> **Example — a dbt/warehouse project:**
>
> ```bash
> $QUERY_STORE "SELECT DISTINCT table_schema FROM information_schema.tables;"
> ```
>
> If the raw/source schema is the **only** analytical layer — no transform or
> output layer yet — that absence is a fact Pass 3 relies on: it is what Pass 3
> builds. Record the absence as deliberately as you record the presence.

## 4. Interrogate the schema against the spec

Read the source schema file (the DDL/definition your source is created from) and
pin the facts that bite a planner if wrong. At minimum resolve these three, in
whatever terms your data model uses:

- **Join** — identify the sole seam(s) between the entities a claim depends on:
  the foreign keys and cardinality that make a join correct. Getting the join wrong
  silently double-counts or drops rows.
- **Grain** — identify the timestamp/partition types and their timezone/precision.
  Do not assume a local zone or a coarser grain than the data carries.
- **Metric** — pin which column defines a contested business term (e.g. does
  "revenue" resolve against a *settled/paid* status or against an *intended* amount).
  Decide and record which.

> **Example — a dbt/warehouse project:** the sole orders↔payments seam is
> `payments.order_id → orders(order_id)`; `orders` also joins `customers` and
> `products`. Timestamps are `TIMESTAMPTZ`, so any date grain is UTC. "Revenue"
> resolves against `payments.status` (paid/captured), not `orders.total_amount`
> (intent).

## 5. Note the fence

If the project carries a facilitator-only or out-of-band dataset — an answer key,
an audit log, injected-incident records, anything the analytics pipeline is *not*
meant to read — record where it lives and confirm it never leaks into the layers
your pipeline queries. Note it explicitly so no downstream pass mistakes it for a
business table.

> **Example — a dbt/warehouse project:** an `_control.injected_incidents` table
> lives in a separate `_control` schema, written only when injection runs with a
> record flag. The analytics pipeline reads the business schema only, and
> `_control.*` never lands into the raw/source tables.

## Output

You now have the 3–4 observed facts for Step 3. Each becomes one
`docs/adrs/NNNN-<slug>.md` via `scaffold-adr.sh`, with its evidence line copied
from what you ran here.
