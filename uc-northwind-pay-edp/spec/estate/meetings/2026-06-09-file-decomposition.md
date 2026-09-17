# File decomposition — Java stays, you rebuild beside it

**Date:** 2026-06-09  
**Type:** Tech Sync  
**Confidence:** 0.88

## Attendees

Helena Dias · Rafael Costa · Marina Alves

## Executive Summary

The live path remains SFTP raw → Java sanitize → SFTP csv → COPY →
procedures → reporting. The modernization plant is a second reader of
the **same raw bytes**. It must not call Java and must not reuse the
stored procedures to invent an answer.

## Key Decisions

| # | Decision | Owner | Status |
|---|---|---|---|
| D1 | One handler per type, five files: model, parser, schema, writer, handler | Helena | Approved |
| D2 | Exact Decimal. No float money. | Rafael | Approved |
| D3 | Quarantine is batch-scoped | Marina | Approved |

## Architecture

```text
customer drop (this folder)
  → understand / decide
  → independent parser
  → sanitized Parquet
  → Bronze / Silver / Gold
  → compare to expected/ and to a live legacy observation
```

## Open Questions

| # | Question | Context |
|---|---|---|
| Q1 | Do unused columns on Rafael’s table dumps belong in Gold? | He said “most of those were for a report that died.” |
