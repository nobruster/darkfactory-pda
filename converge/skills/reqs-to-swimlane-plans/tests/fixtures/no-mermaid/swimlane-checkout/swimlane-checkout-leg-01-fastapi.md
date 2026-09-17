---
leg: swimlane-checkout-leg-01
tech: fastapi
swimlane: swimlane-checkout
parent: swimlane-checkout.plan.md
status: proposed
spec_ref: [R-1]
depends_on: []
type: leg
---

# swimlane-checkout-leg-01-fastapi — validate the cart

> Part of swimlane **checkout** ([swimlane-checkout.plan.md](swimlane-checkout.plan.md)).
> Plan altitude only.

## Responsibility

Confirm the cart is purchasable — items in stock, prices current — so that no order
is created from an invalid cart.

## Proves (acceptance criteria — Given/When/Then; no evals)

- Given an empty cart, when checkout is requested, then it is rejected with no order.
- Given an out-of-stock item, when checkout is requested, then validation fails.

## Independence

Buildable and provable alone: a validation endpoint over a cart fixture; leg-02 does
not gate it.

## Consumes / produces

- Consumes: `cart.*`.
- Produces: a validated-cart signal for leg-02.

## Appetite

small — one endpoint, one context window.

## Yields at Pass 5B (named units, not specified here)

- the validation endpoint and its stock/price checks.
- the empty-cart and out-of-stock rejection paths.

## Re-verify when

The cart contract changes, or stock is sourced differently.
