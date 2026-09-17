---
leg: swimlane-checkout-leg-02
tech: stripe
swimlane: swimlane-checkout
parent: _lane.md
status: proposed
spec_ref: [R-2]
depends_on: [swimlane-checkout-leg-01]
type: leg
---

# Charge and write the order

## Responsibility

Charge the validated cart and write `order.*`, publishing nothing when payment
fails.

## Proves

- Given a validated cart, when payment succeeds, then exactly one order is published.
- Given a declined payment, when checkout runs, then no order is published.

## Consumes / produces

- Consumes: the validated-cart signal from leg 01.
- Produces: the `order.*` contract.
