---
leg: swimlane-checkout-leg-03
tech: stripe
swimlane: swimlane-checkout
parent: swimlane-checkout.plan.md
status: proposed
spec_ref: [R-2]
depends_on: [swimlane-checkout-leg-01]
type: leg
---

# swimlane-checkout-leg-03-stripe — charge and write the order

> Part of swimlane **checkout** ([swimlane-checkout.plan.md](swimlane-checkout.plan.md)).
> Plan altitude only.

## Responsibility

Charge the validated cart and write the `order.*` record, so that a paid order is
published for fulfillment — and nothing is published unless payment succeeded.

## Proves (acceptance criteria — Given/When/Then; no evals)

- Given a validated cart, when payment succeeds, then exactly one `order.*` row is published.
- Given a declined payment, when checkout runs, then no order is published.

## Independence

Provable alone against a validated-cart fixture and a payment sandbox; leg-01 is its
only inbound edge.

## Consumes / produces

- Consumes: a validated-cart signal (leg-01).
- Produces: the `order.*` published contract.

## Appetite

small — one charge path + one order write.

## Yields at Pass 5B (named units, not specified here)

- the charge call and its success/decline handling.
- the idempotent order-write on payment success.

## Re-verify when

The payment provider changes, or the `order.*` contract shape changes.
