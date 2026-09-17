# Operator guide

The Cockpit is an observation surface. A visible plan is not proof that its work
ran, passed review, or settled.

## Reading the checkout seam

1. `cart.*` is the inbound contract.
2. validation must complete before payment.
3. `order.*` is published only after payment succeeds.

> Empty execution and receipt views are expected in this fixture.
