# Apex pilot

This is BriefSpec's first bounded experience pilot. The fixtures are synthetic; they test the
reading contract and must not be presented as evidence about the Apex repository itself.

## Questions

1. Can an engineer identify status, outcome, and required action in under 15 seconds?
2. Does every material claim retain an inspectable proof reference?
3. Does a checkpoint reduce re-orientation time without interrupting active work?
4. Does spoken mode remain understandable without reading paths or logs aloud?
5. Does one malformed handoff receive at most one repair request?

## Run

```bash
uv run python scripts/run-pilot.py
```

The runner validates every expected handoff against the executable BriefSpec contract. A human
pilot can then record timing and comprehension observations in an untracked copy of
`results-template.json`.
