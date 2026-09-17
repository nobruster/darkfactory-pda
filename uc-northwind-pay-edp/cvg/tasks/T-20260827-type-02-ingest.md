---
id: T-20260827-type-02-ingest
title: Type 02 ingest → landing (five-file package; zero Parquet on DF-SOURCE-002)
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
  - modern/ingestion/src/northwind_pay/types/02-instant-payment-events/model.py
  - modern/ingestion/src/northwind_pay/types/02-instant-payment-events/parser.py
  - modern/ingestion/src/northwind_pay/types/02-instant-payment-events/schema.py
  - modern/ingestion/src/northwind_pay/types/02-instant-payment-events/writer.py
  - modern/ingestion/src/northwind_pay/types/02-instant-payment-events/handler.py
source_note: "ADR 0001–0005, 0002 five-file; contracts/types/02-instant-payment-events/; keep DF-SOURCE-002 173.44"
created: 2026-08-27T12:00:00Z
tags: [type-02, ingest, landing]
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
signed_off_at: 2026-08-29T00:22:25Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:14Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:43cef5f4f7d2d182309916a026d0903bbae84a70f177cf23d43699cac75a0744
accepted_tier: 2
accepted_attempt_id: 5537667e-1f4f-5980-8419-b88c58c72d98
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:43cef5f4f7d2d182309916a026d0903bbae84a70f177cf23d43699cac75a0744
acceptance_record_digest: sha256:b0c2537c69fd8623216464d652fa8f42ab48768c0b129cf787ff4a941219e657
---

# Type 02 ingest → landing (five-file package; zero Parquet on DF-SOURCE-002)

> **Why:** Same SWE lane as Type 01. Pipe-delimited PIX is type-specific.
> The lie keeps **173.44**. Do not create an empty type folder.

## Context

Type 02 is the PIX instant-payment lane. The legacy plant already processes it
and is the referee, never the teacher: the modern package is built from
`contracts/types/02-instant-payment-events/` alone. Type 01 proved the shape —
five files, Decimal money, privacy at the parser, landing Parquet first.

`DF-SOURCE-002` (`B202607230000105`) is a source lie: the trailer declares net
**173.44** while the events sum to **173.45**. Legacy keeps the declaration and
refuses the batch. Modern must do the same and write **zero** Parquet.

## Goal

Author (and later execute) one Type 02 five-file package
(`model → parser → schema → writer → handler`) so `valid-minimal`
may emit landing Parquet under `modern/landing/` and `DF-SOURCE-002`
emits **zero** Parquet (`SOURCE_CONTROL_NET_MISMATCH`). Decimal. Privacy
at the parser. Do not write `legacy/`, `contracts/`, `gen/`, or `infra/`.
Do not write product files while `signed_off: false`.

## Behavior

- **B-1** — Same as Type 01: SFTP raw + checksum + manifest-last; first
  write is `modern/landing/` Parquet; Decimal never float; privacy dies
  at parse; refuse the lie with zero Parquet.
- **B-2** — Type-specific: `PIX_EVENTS01`, UTF-8 pipe-delimited `.txt`;
  tokenize payer/payee documents; `DF-SOURCE-002` /
  `B202607230000105` declares net **173.44** vs events **173.45**.
- **B-3** — No Java import. No empty `02-instant-payment-events/` folder.

## Success Criteria

Each criterion is a runnable bash function returning 0 (pass) or non-zero (fail).
`eval_3` **executes** the package against the contract fixtures, so it is RED
before the work exists and GREEN only when the artifact actually runs.

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/cvg/tasks/T-20260827-type-02-ingest.md"
FINDING="$ROOT/contracts/types/02-instant-payment-events/main/expected-df-source-002-finding.yaml"
PKG="$ROOT/modern/ingestion/src/northwind_pay/types/02-instant-payment-events"

eval_1() {
  grep -q 'model → parser → schema → writer → handler' "$SPEC" || return 1
  grep -q 'modern/landing/' "$SPEC" || return 1
  grep -q '173.44' "$SPEC" || return 1
  grep -q 'zero Parquet' "$SPEC" || return 1
  grep -q 'Decimal' "$SPEC" || return 1
  grep -q 'SOURCE_CONTROL_NET_MISMATCH' "$FINDING" || return 1
  grep -q '173.44' "$FINDING" || return 1
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
import importlib.util, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[0] if False else pathlib.Path.cwd()
PKG = ROOT / "modern/ingestion/src/northwind_pay/types/02-instant-payment-events"
MAIN = ROOT / "contracts/types/02-instant-payment-events/main"
sys.path.insert(0, str(ROOT / "modern/ingestion/src"))
import os
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")

spec = importlib.util.spec_from_file_location("t02_handler", PKG / "handler.py")
mod = importlib.util.module_from_spec(spec); sys.modules["t02_handler"] = mod
spec.loader.exec_module(mod)

with tempfile.TemporaryDirectory() as tmp:
    landing = pathlib.Path(tmp)
    # 1) valid-minimal must publish landing Parquet with the contract's net
    out = mod.process(MAIN / "valid-minimal.txt", landing_root=landing)
    d = out.as_dict() if hasattr(out, "as_dict") else dict(out)
    assert d["status"] == "succeeded", d
    assert d["controls"]["computed_net_amount"] == "173.45", d
    assert list(landing.rglob("*.parquet")), "no landing Parquet for valid-minimal"

with tempfile.TemporaryDirectory() as tmp:
    landing = pathlib.Path(tmp)
    # 2) the source lie must keep 173.44 and publish ZERO Parquet
    out = mod.process(MAIN / "df-source-002.txt", landing_root=landing)
    d = out.as_dict() if hasattr(out, "as_dict") else dict(out)
    assert d["status"] != "succeeded", d
    assert d["controls"]["declared_net_amount"] == "173.44", d
    assert not list(landing.rglob("*.parquet")), "the lie produced Parquet"
print("eval_3 OK")
PYEOF
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Leaf names five-file landing, keep 173.44 zero Parquet, freeze fence
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Package is five-file, Decimal, no Java import, no binary float
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-3]
    terminal: true
    expected_duration_sec: 5
  - id: eval_3
    description: EXECUTES the package — valid-minimal emits landing Parquet at net 173.45; DF-SOURCE-002 keeps 173.44 and emits zero Parquet
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-3]
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

Additive. Revert with `git rm -r modern/ingestion/src/northwind_pay/types/02-instant-payment-events`.
Never revert a frozen tree to make a gate pass.

---

## Observability Hooks

Watch the landing Parquet SHA-256 and the refusal path: `DF-SOURCE-002` must
record `SOURCE_CONTROL_NET_MISMATCH` with zero Parquet written.

---

## Open Questions

(none — the contract fixes the layout, the money rule and the refusal code.
Anything ambiguous is a `CONTRACT_AMBIGUITY` to raise, never a guess to encode.)

---

## Anti-Patterns

- **Don't port Java.** Don't use float. Don't repair 173.44.
- **Don't create an empty type-02 folder.** Five files or nothing.
- **Don't recut Type 01 seam 1.**

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
