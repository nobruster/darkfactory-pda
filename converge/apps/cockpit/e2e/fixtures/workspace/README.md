---
title: Checkout proving workspace
owner: payments-stream
---

# Checkout proving workspace

This fixture demonstrates how Converge turns a validated cart into a paid order
without inventing execution or settlement evidence.

## What is present

| Surface | Observed evidence |
|---|---|
| Decompose | One checkout swimlane with two ordered legs |
| Work | No Task-Spec queue yet |
| Runs | No attempts yet |
| Docs | This hash-bound README |

```text
cart.* -> validate -> charge -> order.*
```

See the [operator guide](docs/operator-guide.md) for the evidence boundary.
