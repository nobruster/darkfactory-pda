---
leg: swimlane-checkout-leg-01
tech: fastapi
swimlane: swimlane-checkout
parent: _lane.md
status: proposed
spec_ref: [R-1]
depends_on: []
type: leg
---

# Validate the cart

## Responsibility

Confirm the cart is purchasable so no order is created from an invalid cart.

## Proves

- Given an empty cart, when checkout is requested, then no order is created.
- Given an out-of-stock item, when checkout is requested, then validation fails.

## Consumes / produces

- Consumes: `cart.*`.
- Produces: a validated-cart signal for leg 02.
