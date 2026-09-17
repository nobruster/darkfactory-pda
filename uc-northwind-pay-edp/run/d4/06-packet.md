# 06 · Packet + Type 01 hash

- Slide: Execute 05–06 (Hands-On **slice c · loop**) — tile 06
- Slice: **C · Loop**
- Who: instructor first, then every seat
- Next: [`07-type05-unattended.md`](07-type05-unattended.md) on Execute 07–08

Telemetry is the packet. Dagster is lineage — **not** the parser. Skip the hash look-up if Type 01 Gold is missing; the packet from tile 05 still counts.

## Prompt (verbatim)

```text
Look up the packet from the Type 01 leaf you just cranked (terminal, not Git).
Name: leaf, attempt, eval, exit, classification or skip, paths.

Look up evidence/loop/T-20260825-type-01-landing-parser.json (terminal, not Git).
Look up evidence/modern/B202607230000001/golden-match.json — both questions true.

If Type 01 Gold exists on disk:
- Direct rebuild from landing and orchestrated (Dagster) must hash the same Gold.
- Parsing does not move into the orchestrator.
If Dagster is not running, **say so and skip the hash** — do not stand up Dagster to look busy.

Do not serve unresolved Gold.
Do not write FastAPI unless the ADR for 0006 row 9 is signed and Gold is approved.
```

## Proof

Packet restatable with files closed. If Gold exists: direct and orchestrated **same hash**. Parsing still in the plant.

## If fail

No packet → go back to [`05-mesh-crank.md`](05-mesh-crank.md). Dagster that parses → **stop**. FastAPI on unresolved Gold → tear it up.
