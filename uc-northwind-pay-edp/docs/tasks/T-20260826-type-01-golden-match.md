---
id: T-20260826-type-01-golden-match
title: Attach golden-match to Type 01 modern observations
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: docs/seams.md
depends_on:
  - T-20260826-type-01-gold
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/validation/attach_type01.py
source_note: "ADR 0011; do not rewrite validation/golden-match/golden_match.py"
created: 2026-08-26T18:00:00Z
tags: [type-01, golden-match]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 01 Gold rebuilds from landing"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: any
signed_off: false
signed_off_by: (none)
signed_off_at: (none)
accepted: false
accepted_by: (none)
accepted_at: (none)
evidence_refs: []
---

# Attach golden-match to Type 01 modern observations

> **Why:** Unresolved golden-match is not Gold. The referee already
> exists. Attach observations. Do not add a tolerance.

## Goal

Run three cases and write `evidence/modern/`:

1. `valid-minimal` — both questions yes.
2. `DF-SOURCE-001` — `CONFIRMED_SOURCE_DEFECT`, no Gold, keep 173.44.
3. `malformed` — classified terminal, no invented artifacts.

Zero unexplained differences.

## Behavior

- **B-1** — Attach uses `validation/golden-match/golden_match.py` unchanged.
- **B-2** — `valid-minimal` resolved against contract and legacy observation.
- **B-3** — Source lie classified `CONFIRMED_SOURCE_DEFECT`; no Gold file invented.
- **B-4** — Malformed classified; no Parquet / Gold artifacts.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
ATTACH="$ROOT/modern/validation/attach_type01.py"
REF="$ROOT/validation/golden-match/golden_match.py"

eval_1() {
  test -f "$ATTACH" || return 1
  grep -q 'golden_match' "$ATTACH" || return 1
  ! grep -q 'tolerance' "$ATTACH" || return 1
  grep -q 'CONFIRMED_SOURCE_DEFECT' "$REF" || return 1
}

eval_2() {
  python3 - "$ROOT" <<'PY'
import json, os, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1])
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")
subprocess.check_call([sys.executable, str(root / "modern/scripts/run_type01_gold.py")], cwd=root)
subprocess.check_call([sys.executable, str(root / "modern/validation/attach_type01.py")], cwd=root)
packet = root / "evidence/modern"
happy = json.loads((packet / "B202607230000001" / "golden-match.json").read_text())
assert happy["resolved"] is True, happy
assert happy["unexplained_count"] == 0
assert happy["checks"].get("legacy_matches_contract") is True or happy["checks"].get("contract_reconciliation") is True
lie = json.loads((packet / "B202607230000004" / "golden-match.json").read_text())
classes = {d["classification"] for d in lie["differences"]}
assert "CONFIRMED_SOURCE_DEFECT" in classes, lie
assert lie["unexplained_count"] == 0
assert not list((root / "modern/landing").rglob("*B202607230000004*.parquet"))
mal = json.loads((packet / "B202607230000003" / "golden-match.json").read_text())
assert mal["checks"].get("modern_produced_no_parquet") is True
assert not (packet / "B202607230000003" / "parquet-file.sha256").exists()
print("golden-match ok")
PY
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Attach script uses the referee and adds no tolerance
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Three cases classified; valid-minimal resolved; lie has no Gold
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-3, B-4]
    terminal: true
    expected_duration_sec: 90
```

## Exit Check

```bash
eval_1 && eval_2
```

## Anti-Patterns

- **Don't edit the referee.** Don't net the two questions.
- **Don't classify CONFIRMED_LEGACY_DEFECT tonight.** That's Friday.
- **Don't invent Parquet for a refusal.**

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
