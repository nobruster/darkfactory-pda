---
id: T-20260827-type-05-ingest
title: Type 05 ingest → landing (five-file; HALF_UP at parser; zero Parquet on DF-SOURCE-005)
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
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/model.py
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/parser.py
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/schema.py
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/writer.py
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/handler.py
source_note: "ADR 0001–0005, 0003 Decimal; contracts/types/05-merchant-fee-assessment/; HALF_UP; keep DF-SOURCE-005 0.99"
created: 2026-08-27T12:00:00Z
tags: [type-05, ingest, landing, half-up]
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
signed_off_at: 2026-08-29T00:22:34Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:21Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:eb10b1420f31e42400fc892c3b727c38ec3ad32a77cfd8976a407eea9de49302
accepted_tier: 2
accepted_attempt_id: c8119e15-abcc-5f4d-a889-cbbfba9121de
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:eb10b1420f31e42400fc892c3b727c38ec3ad32a77cfd8976a407eea9de49302
acceptance_record_digest: sha256:46614b0af61c4baeab54025e73bf6cd92e93d76ca5a0fca56122e8b2736b52ae
---

# Type 05 ingest → landing (five-file; HALF_UP at parser; zero Parquet on DF-SOURCE-005)

> **Why:** Same SWE lane as Type 01. Locale CSV and `HALF_UP` are
> type-specific. Keep declared assessed **0.99**. Do not rewrite
> `expected/`. Do not create an empty Type 05 package.

## Context

Type 05 is built from `contracts/types/05-merchant-fee-assessment/` alone — legacy is the referee,
never the teacher. Type 01 proved the shape: five files, Decimal money, privacy
at the parser, landing Parquet first.

`DF-SOURCE-005` is a source lie. Legacy keeps the declaration and refuses the
batch; modern must do the same and write **zero** Parquet.

## Goal

Author (and later execute) one Type 05 five-file package so
`valid-minimal` and `rounding-half-up` may emit `modern/landing/`
Parquet, fee = `gross × rate ÷ 100` rounded once with **`HALF_UP`**,
and `DF-SOURCE-005` emits **zero** Parquet
(`SOURCE_CONTROL_ASSESSED_FEE_MISMATCH`). Frozen trees forbidden. No
product files while `signed_off: false`.

## Behavior

- **B-1** — Same as Type 01: five-file, Decimal never float, privacy at
  parse, landing Parquet not SFTP.
- **B-2** — Type-specific: semicolon CSV, decimal comma; **`HALF_UP`**
  at the parser (Python default `HALF_EVEN` is forbidden here).
- **B-3** — `DF-SOURCE-005` / `B202607230000405` source assessed **0.99**
  vs calculated **1.00**. Keep 0.99. Refuse. Zero Parquet. Do not rewrite
  `contracts/` `expected/`.
- **B-4** — No empty `05-merchant-fee-assessment/` folder. No Java import.

## Success Criteria

`eval_3` **executes** the package against the contract fixtures, so it is RED
before the work exists and GREEN only when the artifact actually runs.

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/cvg/tasks/T-20260827-type-05-ingest.md"
PKG="$ROOT/modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment"

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
PKG = ROOT / "modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment"
MAIN = ROOT / "contracts/types/05-merchant-fee-assessment/main"
sys.path.insert(0, str(ROOT / "modern/ingestion/src"))
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")

spec = importlib.util.spec_from_file_location("t05_handler", PKG / "handler.py")
mod = importlib.util.module_from_spec(spec); sys.modules["t05_handler"] = mod
spec.loader.exec_module(mod)

def run(fixture, landing):
    out = mod.process(MAIN / fixture, landing_root=landing)
    return out.as_dict() if hasattr(out, "as_dict") else dict(out)

with tempfile.TemporaryDirectory() as tmp:
    landing = pathlib.Path(tmp)
    d = run("valid-minimal.csv", landing)
    assert d["status"] == "succeeded", d
    c = d["controls"]
    assert c["computed_net_amount" if "computed_net_amount" in c else list(c)[0]] is not None, c
    assert list(landing.rglob("*.parquet")), "no landing Parquet for valid-minimal"

with tempfile.TemporaryDirectory() as tmp:
    landing = pathlib.Path(tmp)
    d = run("df-source-005.csv", landing)
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
    description: HALF_UP at parser; DF-SOURCE-005 keep 0.99 zero Parquet; freeze fence
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: No empty Type 05 folder while unsigned; present parser is HALF_UP Decimal
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-4]
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

Additive. Revert with `git rm -r modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment`.

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

- **Don't rewrite `expected/` to match `HALF_EVEN`.** That is `MODERN_DEFECT` on the lakehouse leaf.
- **Don't create an empty Type 05 package.** Five files or nothing.
- **Don't repair 0.99.**

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
