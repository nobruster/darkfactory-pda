# Contributing

Brief-Spec is intentionally small: host agents synthesize; the core normalizes, schedules, validates,
and installs.

## Development

```bash
uv sync --dev
uv run ruff check .
uv run pytest
uv run python scripts/run-pilot.py
uv build
```

Run the release verifier and both plugin validators before submitting a change:

```bash
uv run python scripts/verify-release.py
python ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
claude plugin validate . --strict
```

Add tests for every behavior change. Adapter fixtures must not contain credentials or private
transcripts. Preserve the distinction between structural, synthetic, local-runtime, and live-cloud
evidence.
