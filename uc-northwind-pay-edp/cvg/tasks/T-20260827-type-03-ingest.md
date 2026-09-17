---
id: T-20260827-type-03-ingest
title: Type 03 ingest → landing (five-file package; zero Parquet on DF-SOURCE-003)
status: ready
format_version: 3
profile: standard
effort: L
budget_iterations: 15
agent: claude
parent: docs/seams.md
depends_on: []
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/model.py
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/parser.py
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/schema.py
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/writer.py
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/handler.py
source_note: "ADR 0001–0005, 0002 five-file; contracts/types/03-payment-slip-settlement/; keep DF-SOURCE-003 198.49"
created: 2026-08-27T12:00:00Z
tags: [type-03, ingest, landing]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "docs/consensus.md signed; Type 01 seam 1 unchanged"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:22:28Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:17Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:da8ae5a6cf1f2ac1b3282f00bde335f63fe2a2863b5c50f22e6af2542df0b5ea
accepted_tier: 2
accepted_attempt_id: b7d09629-0ebe-5e5f-9ac7-27431eaebf06
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:da8ae5a6cf1f2ac1b3282f00bde335f63fe2a2863b5c50f22e6af2542df0b5ea
acceptance_record_digest: sha256:87f6e436c5cfc0d23b4b57aeae05fd5d509d0ecac7dcd35a6011aa26ef66489a
---

# Type 03 ingest → landing (five-file package; zero Parquet on DF-SOURCE-003)

> **Why:** Same SWE lane as Type 01. 240-byte paired `A`/`B` lots are
> type-specific. Keep declared **198.49**. Do not create an empty type folder.

## Context

Type 03 is built from `contracts/types/03-payment-slip-settlement/` alone — legacy is the referee,
never the teacher. Type 01 proved the shape: five files, Decimal money, privacy
at the parser, landing Parquet first.

`DF-SOURCE-003` is a source lie. Legacy keeps the declaration and refuses the
batch; modern must do the same and write **zero** Parquet.

## Goal

Author (and later execute) one Type 03 five-file package so
`valid-minimal` may emit `modern/landing/` Parquet and `DF-SOURCE-003`
emits **zero** Parquet (`SOURCE_CONTROL_NET_MISMATCH`). Decimal. Privacy
at the parser. Frozen trees forbidden. No product files while
`signed_off: false`.

## Behavior

- **B-1** — Same as Type 01: five-file, Decimal, privacy at parse,
  landing Parquet not SFTP, lie refused with zero Parquet.
- **B-2** — Type-specific: `PAYSLIPSET03` `.rem`, 240-byte paired
  segments; `DF-SOURCE-003` / `B202607230000205` declares net **198.49**
  vs rows **198.50**.
- **B-3** — No Java import. No empty `03-payment-slip-settlement/` folder.

## Success Criteria

`eval_3` **executes** the package against the contract fixtures, so it is RED
before the work exists and GREEN only when the artifact actually runs.

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/cvg/tasks/T-20260827-type-03-ingest.md"
PKG="$ROOT/modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement"

eval_1() {
  grep -q 'modern/landing/' "$SPEC" || return 1
  grep -q 'zero Parquet' "$SPEC" || return 1
  grep -q 'Decimal' "$SPEC" || return 1
  awk '
    BEGIN { sec="" }
    /^---$/ { n++; next }
    n==1 && $0 ~ /^(touches_paths|creates_paths):/ { sec=$1; next }
    n==1 && sec != "" && $0 ~ /^[^[:space:]-]/ { sec="" }
    n==1 && sec != "" && $0 ~ /^[[:space:]]*-[[:space:]]*(legacy|contracts|gen|infra)\// { bad=1 }
    END { exit bad ? 1 : 0 }
  ' "$SPEC" || return 1
}

eval_2() {
  for f in model.py parser.py schema.py writer.py handler.py; do
    test -f "$PKG/$f" || return 1
  done
  ! grep -qE 'from[[:space:]]+legacy|import[[:space:]]+java|legacy\.processor' "$PKG"/*.py || return 1
  ! grep -qE 'float\(|np\.float|dtype=float' "$PKG"/parser.py || return 1
  grep -q 'Decimal' "$PKG/parser.py" || return 1
}

# EXECUTES the artifact. Fails closed when the package is absent.
eval_3() {
  test -x "$ROOT/modern/.venv/bin/python" || return 1
  test -f "$PKG/handler.py" || return 1
  cd "$ROOT" || return 1
  ./modern/.venv/bin/python - <<'PYEOF'
import importlib.util, os, pathlib, sys, tempfile
ROOT = pathlib.Path.cwd()
PKG = ROOT / "modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement"
MAIN = ROOT / "contracts/types/03-payment-slip-settlement/main"
sys.path.insert(0, str(ROOT / "modern/ingestion/src"))
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")

spec = importlib.util.spec_from_file_location("t03_handler", PKG / "handler.py")
mod = importlib.util.module_from_spec(spec); sys.modules["t03_handler"] = mod
spec.loader.exec_module(mod)

def run(fixture, landing):
    out = mod.process(MAIN / fixture, landing_root=landing)
    return out.as_dict() if hasattr(out, "as_dict") else dict(out)

with tempfile.TemporaryDirectory() as tmp:
    landing = pathlib.Path(tmp)
    d = run("valid-minimal.rem", landing)
    assert d["status"] == "succeeded", d
    c = d["controls"]
    assert c["computed_net_amount" if "computed_net_amount" in c else list(c)[0]] is not None, c
    assert list(landing.rglob("*.parquet")), "no landing Parquet for valid-minimal"

with tempfile.TemporaryDirectory() as tmp:
    landing = pathlib.Path(tmp)
    d = run("df-source-003.rem", landing)
    assert d["status"] != "succeeded", d
    assert not list(landing.rglob("*.parquet")), "the lie produced Parquet"
print("eval_3 OK")
PYEOF
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Leaf names five-file landing, keep 198.49 zero Parquet, freeze fence
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Absent package allowed only while unsigned; present package is five-file Decimal no Java
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-3]
    terminal: true
    expected_duration_sec: 5
  - id: eval_3
    description: EXECUTES the package — valid-minimal emits landing Parquet; the source lie emits zero Parquet
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: true
    expected_duration_sec: 30

retry_policy:
  max_iterations: 15
  circuit_breaker_no_progress: 3
  on_terminal_failure: park_with_context

agent_contract:
  version: 2
  read: [intent, behavior, contract, guardrails, operations]
  produce:
    - code
  required_tools: [git, bash]
  timeout_minutes: 45
  sandbox_type: host
  output_artifacts: []
  mcp_dependencies: []
  emit:
    - pass
    - fail
    - retry_with_reason
    - parked_with_context
  backend_metadata: {}
```

## Exit Check

```bash
eval_1 && eval_2 && eval_3
```

## Rollback Plan

Additive. Revert with `git rm -r modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement`.

---

## Observability Hooks

Watch the landing Parquet SHA-256 and the refusal path: the source lie must
record its rejection code with zero Parquet written.

---

## Open Questions

(none — the contract fixes the layout, the money rule and the refusal code.
Anything ambiguous is a `CONTRACT_AMBIGUITY` to raise, never a guess to encode.)

---

## Anti-Patterns

- **Don't pair segments in Dagster.** Don't repair 198.49. Don't create an empty type folder.

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
