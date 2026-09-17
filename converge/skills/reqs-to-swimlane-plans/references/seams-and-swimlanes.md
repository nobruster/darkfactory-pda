# Seams and swimlanes — finding the natural cut (by feature vs. by component)

Pass 3 splits a confirmed system into one **swimlane plan per seam**. This
reference is the protocol behind Step 1: how to find a seam that is real, name the
interface that lives on it, and refuse the ones that aren't.

## What a seam is

A seam is a **nameable interface** with a **one-way dependency** across it. Two
groups are separated by a real seam when:

1. You can point to the exact contract that crosses it — tables, columns, a
   function signature, an endpoint shape — not a vibe.
2. The dependency runs in **one direction**: one side *produces* the contract, the
   other *consumes* it. If the arrow points both ways, it is one lane, not two.
3. Each side could be built against a *frozen* version of that contract without
   watching the other side's internals.

> The one-line test: **can you name the interface?** If yes, it is a seam — cut
> there. If you can't, it is a hidden coupling — fold the lanes back together and
> keep looking.

## By feature OR by component — never an arbitrary slice

There are two honest ways to cut, and the architecture tells you which:

- **By component** — split where the *technology or responsibility* changes. The
  terrain changes at the point where one side stops *shaping* data or state and the
  next side starts *exposing* it. That change of responsibility is a component seam.
- **By feature** — split where two independent *capabilities* share nothing but a
  contract (e.g. "billing" vs. "notifications"). Cut per feature when the features
  don't stack into a pipeline.

A system that flows as a pipeline (prep → transform → publish → serve) is naturally
a **component** cut. A breadth-of-features product is naturally a **feature** cut.
What is never allowed is an arbitrary slice — "front half / back half", or "the big
models vs. the small ones" — that no interface backs.

## Worked example — a transform-then-serve pipeline (two lanes)

Concrete illustration only; your system's seams come from your own architecture.
Suppose a project ingests source data, transforms it into a set of published
output tables, and serves those tables through a read layer. The seam falls at the
published contract — *above* the raw/source data, *below* the serving surface:

```
source  ─┤ Component A · Transform ├─►  published  ─┤ Component B · Serve ├─►  answers
(given)   (the transform pipeline)      (the seam)    (the read/serving layer)
```

- **Component A · Transform** — the sole writer of the output tables. Consumes the
  source/raw tables, produces the published (output/contract) tables.
- **Component B · Serve** — the read-only consumer. Reads the published tables
  only, never below them. This is the serving layer (an API, an MCP tool, a report,
  etc.).
- **The seam is the published contract** — owned by A, consumed by B. A produces
  the output tables (and their column shapes); B binds to them. Naming this contract
  is what lets Pass 4 attack it and Pass 5 build both lanes against a frozen shape.

Two lanes is a *common shape*, not a rule and not a quota. The lane count is the
number of genuine seams the architecture reveals — no more, no fewer.

## The downstream lane names the exact interface it consumes

The seam is a contract, so the consuming lane must pin it precisely:

- The consuming lane names **which published tables and columns** (or which
  endpoints/fields) each part of it reads, and **never reaches below the contract**
  to read the producer's internals (intermediate tables, source data, upstream
  stores).
- Something that isn't in the upstream contract is a **new request to the upstream
  producer**, never a deeper read that bypasses the seam. That rule is what keeps
  the seam a hard boundary instead of a leaky suggestion.
- Because the consumer binds to a *frozen* contract shape, it can be planned in full
  while the producer's internals are still in flux — the seam decouples the two
  build efforts.

## False seams — fold them back

| Symptom | Why it's false | Fix |
|---|---|---|
| Two "lanes" that differ only in protocol/transport framing over the same core (e.g. an HTTP API and an MCP tool sharing one query core) | They share one core and differ only in framing | One lane, multiple transports over a shared core. Record the split-later condition: split only if one transport needs logic the other doesn't. |
| A lane you added to "balance" the diagram | No interface crosses into it | Delete it; its work belongs inside an existing lane. |
| A boundary you can describe but not name | The interface isn't pinned | Either name the exact tables/columns/signature (real seam) or fold the lanes (false seam). Fuzziness is the signal. |

## The seam's contract structure

A seam is only as good as the contract pinned on it. The field's hard-won rules
(consumer-driven contracts — Fowler/Robinson, Pact) apply verbatim:

1. **The producer owns the contract.** The upstream lane publishes the shape
   (the tables/columns, the endpoint, the signature); it is the sole writer.
2. **The consumer pins only what it actually reads** — the tolerant-reader
   rule. A contract that names elements nobody consumes is over-specified: it
   blocks evolution for data nobody uses. A field no consumer pins is
   demonstrably dead — the producer can change or drop it without ceremony.
3. **Both sides build against the frozen shape.** The contract is frozen at
   naming time so the consumer can be planned in full while the producer's
   internals are still in flux.
4. **Evolution is typed, not negotiated.** Additive changes (a new optional
   column/field/endpoint) are non-breaking. Renames, removals, and
   newly-required fields are BREAKING and need a coexistence window — the old
   shape stays live until every consumer has cut over. How the consumer learns
   of a change is stated in the plan (e.g. a consumer-driven contract test the
   producer must keep green).

## Output of Step 1

You leave Step 1 with: the list of lanes, the **dependency direction** between
them, and the **named interface** on each seam (the contract that crosses it). You
have *not* planned the contents yet — that is Step 2, one `swimlanes/<lane>.plan` per
seam via `scripts/new-plan.sh`.
