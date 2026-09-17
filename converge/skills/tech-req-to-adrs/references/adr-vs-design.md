# ADR vs. Design — the Pass 2 no-drift boundary

Pass 2 records **terrain**: what already IS, or what MUST hold. Pass 3 decides
what to **build**. The single failure mode of this pass is an ADR that quietly
designs. This reference shows the boundary with worked examples and the rule for
splitting a mixed record.

## The one-line test

> Could this sentence have been true *before* anyone decided how to solve the
> problem? If yes, it is grounding (Pass 2). If it only becomes true once you
> choose a solution, it is design (Pass 3).

A grounding statement describes the world. A design statement changes it.

## Grounding vs. design, side by side

| Grounding ADR (Pass 2 — keep here) | Design statement (Pass 3 — move out) |
|---|---|
| Payments reference orders on `order_id`; it is the only orders↔payments key. | Build a `fct_payments` table keyed on `order_id`. |
| `ordered_at` / `paid_at` are `TIMESTAMPTZ`; the natural date grain is UTC. | Add a `date_day` dimension truncating `paid_at` to UTC midnight. |
| Revenue means *paid* payments; order `total_amount` is intent, not cash. | Implement `revenue_paid` as `sum(amount) where status='captured'`. |
| `_control.*` is a facilitator fence that never lands into `raw.*`. | Create a reconciliation model that diffs `_control` against `raw`. |

The left column cites a schema line or an observed run and would read the same to
any engineer. The right column presupposes a chosen solution shape — that is Pass
3's job, and pinning it here would rob Pass 3 of the freedom to plan.

## Splitting a mixed ADR

When a draft says *"payments join orders on `order_id`, so build a payments fact
table keyed on it,"* split it:

1. **Keep the fact.** `0001-payments-join-on-order-id`: *Payments reference orders
   on `order_id` (`REFERENCES orders(order_id)`); no other key exists.* Evidence:
   the schema line. Consequence: *any Pass 3 plan must join on `order_id` only.*
2. **Move the build.** The "payments fact table keyed on it" clause is a Pass 3
   plan item. Delete it from the ADR; it will re-appear as a `swimlanes/*.plan` step.

The bundled `scaffold-adr.sh --check` greps for head-of-line build-verbs
(Build/Create/Implement/Add/Design/…) precisely to catch step 2 leaking back in.

## Why the boundary pays off

- Pass 3 stays **free to plan** because Pass 2 never pre-committed a design.
- Pass 2 stays **falsifiable** because every record is a checkable fact, not a
  preference.
- A reviewer can trust `docs/adrs/` as ground truth without re-deriving it from a
  session that no longer exists.
