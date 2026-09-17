# 12 · Execute — golden-match attach

- Slide: Execute 10–12 (Hands-On **slice d · gold**) — tile 12
- Slice: **D · Gold**
- Who: instructor first, then every seat
- Next: Task-Mesh Show (no file), Thursday queue, Debrief · In hand, then [`13-research.md`](13-research.md)

Attach [`validation/golden-match/golden_match.py`](../../validation/golden-match/golden_match.py). Do **not** rewrite it for slack. Two questions, never netted. Evidence is gitignored — open in the **terminal**.

## Prompt (verbatim)

```text
Attach golden-match to Type 01 modern observations.
Do not edit validation/golden-match/golden_match.py.
Do not add a tolerance.

Run three cases:
1. valid-minimal — both questions yes (legacy observation AND contract).
2. DF-SOURCE-001 / df-source-001 — classification CONFIRMED_SOURCE_DEFECT. No Gold. Keep 173.44. Zero Parquet already proved.
3. malformed — classified. No invented artifacts.

Write the packet under evidence/modern/ (terminal, not Git).
Zero unexplained differences.
```

## Proof

| Case | Look up |
|---|---|
| `valid-minimal` | Both questions **yes** |
| `DF-SOURCE-001` | `CONFIRMED_SOURCE_DEFECT` · no Gold · 173.44 kept |
| malformed | Terminal code · no invented files |

A green dbt run with an unresolved difference is a **failed** night.

## If fail

Tolerance added → revert. Gold “fixed” to 173.45 on the lie → tear it out. `CONFIRMED_LEGACY_DEFECT` tonight → wrong; that class is Friday. Unresolved → not shippable; do not serve; park with an owner.

If this worktree has **no** live `control.batches` row, `compare_rejection(..., legacy_final_status=None)` **returns before** it classifies declared vs computed. Do **not** rewrite `golden_match.py`. Either observe a real legacy terminal, or attach `CONFIRMED_SOURCE_DEFECT` from modern controls using the referee’s `Difference` type. Record `legacy_terminal_comparison_skipped_by_request` loudly.
