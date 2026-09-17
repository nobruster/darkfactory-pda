# Swimlane · checkout

lane-meta: thread=yes · risk=high · owner=payments-stream

Component **A · Checkout** — turn a validated cart into a paid order.
Input contract: `cart.*`. Output contract: `order.*` (the seam the fulfillment lane consumes).

## Seam

Where this lane cuts: **above the cart, below the order contract.** `cart.*` is
given upstream; `order.*` is published downstream and is all the fulfillment
lane reads. One-way: checkout produces the order, fulfillment consumes it.

## Legs — index

| Leg | Responsibility | File |
|---|---|---|
| **leg-01-fastapi** | validate the cart is purchasable | [leg-01-fastapi.md](leg-01-fastapi.md) |
| **leg-02-stripe** | charge and write the order record | [leg-02-stripe.md](leg-02-stripe.md) |

## Dependencies

```text
cart.* -> leg-01 -> leg-02 -> order.*
```
