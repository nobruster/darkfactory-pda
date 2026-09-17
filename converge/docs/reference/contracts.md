# Contracts

The machine-readable boundary between Converge and everything that consumes it.
An existing schema is never edited in place. A version is retired only once
nothing validates against it.

| File | Contract | Consumed by |
|---|---|---|
| [`cli-command-matrix.json`](../../contracts/cli-command-matrix.json) | `ConvergeCLICommandMatrix/v1` | all 60 public CLI forms |
| [`cli-command-matrix-v1.schema.json`](../../contracts/cli-command-matrix-v1.schema.json) | schema for the matrix | `scripts/check-docs.py` |
| [`converge-cli-result-v1.schema.json`](../../contracts/converge-cli-result-v1.schema.json) | `ConvergeCLIResult/v1` | every `--json` invocation |
| [`converge-composition-receipt-v1.schema.json`](../../contracts/converge-composition-receipt-v1.schema.json) | `ConvergeCompositionReceipt/v1` | `cvg compose materialize` |
| [`ui/v3/workspace-snapshot.schema.json`](../../contracts/ui/v3/workspace-snapshot.schema.json) | `WorkspaceSnapshot/3.0` | `cvg snapshot`, Cockpit |

`dispatch_authorized` on the composition receipt is a schema `const` of
`false`. Materialization cannot authorize dispatch.

Every public form accepts global `--json` and `--dry-run` in any position.
`--json` emits one `ConvergeCLIResult/v1` document, preserves the exit code,
strips ANSI, and reports `changed` and `dry_run`.
