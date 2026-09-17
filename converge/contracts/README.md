# Contracts

The machine-readable boundary between Converge and everything that consumes it.
A contract changes only by adding a new version directory — an existing schema
is never edited in place, because a consumer may be validating against it. A
version is retired only once nothing validates against it; `ui/v1` and `ui/v2`
were removed on that basis, and remain recoverable from git history.

| File | Contract | Consumed by |
|---|---|---|
| `cli-command-matrix.json` | `ConvergeCLICommandMatrix/v1` | source of truth for all 60 CLI forms; `docs/reference/cli.md` is generated from it |
| `cli-command-matrix-v1.schema.json` | schema for the above | `scripts/check-docs.py` |
| `converge-cli-result-v1.schema.json` | `ConvergeCLIResult/v1` | every `--json` invocation |
| `converge-composition-receipt-v1.schema.json` | `ConvergeCompositionReceipt/v1` | `cvg compose materialize` |
| `ui/v3/workspace-snapshot.schema.json` | `WorkspaceSnapshot/3.0` | `cvg snapshot`, Cockpit |

`docs/reference/cli.md` is regenerated from the matrix. Edit the matrix and
run `python3 scripts/render-cli-reference.py`, then `make check-docs`.
