---
id: T-20260827-type-04-ingest
title: Type 04 ingest → landing (five-file package; zero Parquet on DF-SOURCE-004)
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
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/model.py
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/parser.py
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/schema.py
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/writer.py
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/handler.py
source_note: "ADR 0001–0005, 0002 five-file; contracts/types/04-ted-transfer-settlement/; keep DF-SOURCE-004 999.99"
created: 2026-08-27T12:00:00Z
tags: [type-04, ingest, landing]
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
signed_off_at: 2026-08-29T00:22:31Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:19Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:24807f3563313f135c2dbd31e921c4b74bcf91f69a2fd30708f54625cf065d8e
accepted_tier: 2
accepted_attempt_id: 62ede1b3-cb2b-52a0-8de9-f622d0e1cce6
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:24807f3563313f135c2dbd31e921c4b74bcf91f69a2fd30708f54625cf065d8e
acceptance_record_digest: sha256:31c44591424d2240f3f1a1ef50b010a0f948f1e8f4cbc937b5ef72c98fce5364
---

# Type 04 ingest → landing (five-file package; zero Parquet on DF-SOURCE-004)

> **Why:** Same SWE lane as Type 01. `.dat` is not enough to pick this
> parser (Type 01 is overpunch card). Keep declared **999.99**.

## Context

Type 04 is built from `contracts/types/04-ted-transfer-settlement/` alone — legacy is the referee,
never the teacher. Type 01 proved the shape: five files, Decimal money, privacy
at the parser, landing Parquet first.

`DF-SOURCE-004` is a source lie. Legacy keeps the declaration and refuses the
batch; modern must do the same and write **zero** Parquet.

## Goal

Author (and later execute) one Type 04 five-file package so
`valid-minimal` may emit `modern/landing/` Parquet and `DF-SOURCE-004`
emits **zero** Parquet (`SOURCE_CONTROL_NET_MISMATCH`). Decimal. Privacy
at the parser. Frozen trees forbidden. No empty type folder. No product
files while `signed_off: false`.

## Behavior

- **B-1** — Same as Type 01: five-file, Decimal, privacy at parse,
  landing Parquet not SFTP, lie refused with zero Parquet.
- **B-2** — Type-specific: `TED_SETTLE04` heterogeneous fixed-width
  `H/D/R/T`; `DF-SOURCE-004` / `B202607230000305` declares net **999.99**
  vs rows **1000.00**.
- **B-3** — No Java import. No empty `04-ted-transfer-settlement/` folder.

## Success Criteria

`eval_3` **executes** the package against the contract fixtures, so it is RED
before the work exists and GREEN only when the artifact actually runs.

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/cvg/tasks/T-20260827-type-04-ingest.md"
PKG="$ROOT/modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement"

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
PKG = ROOT / "modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement"
MAIN = ROOT / "contracts/types/04-ted-transfer-settlement/main"
sys.path.insert(0, str(ROOT / "modern/ingestion/src"))
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")

spec = importlib.util.spec_from_file_location("t04_handler", PKG / "handler.py")
mod = importlib.util.module_from_spec(spec); sys.modules["t04_handler"] = mod
spec.loader.exec_module(mod)

def run(fixture, landing):
    out = mod.process(MAIN / fixture, landing_root=landing)
    return out.as_dict() if hasattr(out, "as_dict") else dict(out)

with tempfile.TemporaryDirectory() as tmp:
    landing = pathlib.Path(tmp)
    d = run("valid-minimal.dat", landing)
    assert d["status"] == "succeeded", d
    c = d["controls"]
    assert c["computed_net_amount" if "computed_net_amount" in c else list(c)[0]] is not None, c
    assert list(landing.rglob("*.parquet")), "no landing Parquet for valid-minimal"

with tempfile.TemporaryDirectory() as tmp:
    landing = pathlib.Path(tmp)
    d = run("df-source-004.dat", landing)
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
    description: Leaf names five-file landing, keep 999.99 zero Parquet, freeze fence
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

Additive. Revert with `git rm -r modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement`.

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

- **Don't dispatch Type 04 because the extension is `.dat`.** Type 01 is a different `.dat`.
- **Don't repair 999.99.** Don't create an empty type folder.

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
