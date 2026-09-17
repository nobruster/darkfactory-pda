#!/bin/bash
# test-cvg-snapshot.sh — canonical WorkspaceSnapshot 3.0 contract.
# Proves the Cockpit reads one deterministic, offline, fail-closed CLI model:
# lane-aware method state, canonical task frontier, runtime/receipt provenance,
# typed authorization, artifact references without bytes, and uniform JSON.
# bash 3.2-safe. Python is stdlib-only. Uses product-neutral repository fixtures.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CVG="$ROOT/bin/cvg"
T=0
F=0
ok()  { T=$((T + 1)); printf 'ok    %s\n' "$1"; }
bad() { T=$((T + 1)); F=$((F + 1)); printf 'FAIL  %-42s %s\n' "$1" "$2"; }

WS="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/cvg-snapshot.$$")"
trap 'rm -rf "$WS" 2>/dev/null || true' EXIT
mkdir -p \
  "$WS/.cvg" \
  "$WS/cvg/docs/brd" \
  "$WS/cvg/docs/tech-spec" \
  "$WS/cvg/docs/adrs" \
  "$WS/cvg/swimlanes" \
  "$WS/cvg/tasks/done" \
  "$WS/cvg/tasks/parked" \
  "$WS/cvg/execution" \
  "$WS/cvg/loop" \
  "$WS/cvg/receipts"

cp "$ROOT/templates/workspace/INDEX.md" "$WS/cvg/INDEX.md"
cp "$ROOT/skills/task-to-runtime-contract/templates/gate.yaml" "$WS/.cvg/gate.yaml"
cp "$ROOT/skills/idea-to-brd/tests/fixtures/golden-signed-brd.md" \
  "$WS/cvg/docs/brd/snapshot.md"
cp "$ROOT/skills/brd-docs-to-tech-req/tests/fixtures/golden-signed-tech-spec.md" \
  "$WS/cvg/docs/tech-spec/snapshot.md"
cp -R "$ROOT/skills/reqs-to-swimlane-plans/tests/fixtures/good/." \
  "$WS/cvg/swimlanes/"
# Pass 4's frozen compatibility token belongs in every reviewed PRD. The Pass 3
# fixture intentionally omits it, so this end-to-end snapshot fixture adds the
# owner-approved handoff before the objection log stamps the live plan hashes.
sed -i.bak '1a\
FORK: B (task-driven) — every leg has a cheap runnable eval.
' "$WS/cvg/swimlanes/swimlane-checkout/swimlane-checkout.plan.md"
rm -f "$WS/cvg/swimlanes/swimlane-checkout/swimlane-checkout.plan.md.bak"
cp "$ROOT/tests/fixtures/T-20260602-golden.md" \
  "$WS/cvg/tasks/T-20260602-golden.md"
sed -i.bak 's/^signed_off: false$/signed_off: true/' \
  "$WS/cvg/tasks/T-20260602-golden.md"
rm -f "$WS/cvg/tasks/T-20260602-golden.md.bak"

cat > "$WS/README.md" <<'EOF'
# Snapshot fixture

The project README is visible as hash-bound Cockpit evidence.
EOF
printf '%s\n' '%PDF-1.4 fixture document' > "$WS/cvg/docs/guide.pdf"
mkdir -p "$WS/docs"
printf '%s\n' '%PDF-1.4 project handbook' > "$WS/docs/handbook.pdf"

cat > "$WS/cvg/docs/CONTEXT.md" <<'EOF'
# CONTEXT — pinned vocabulary

- **capture**: moving source rows into the analytical lane unchanged.
- **gold**: the modelled layer a consumer is allowed to read.
EOF

cat > "$WS/cvg/docs/adrs/0000-context.md" <<'EOF'
---
adr: "0000"
status: accepted
date: 2026-07-29
ground: brownfield
converge_pass: 2
spec_ref: "R-1"
supersedes: ""
superseded_by: ""
deciders: "owner"
---

# 0000 — Context: the ground we stand on

## Terrain

Brownfield: an operational database already serves the application.

## Given surface

Orders and payments are durable operational records.

## Build surface

The analytical lane: capture, transform, and serve.

## Spec

The signed technical specification under cvg/docs/tech-spec/.
EOF

cat > "$WS/cvg/docs/adrs/0001-payments-link.md" <<'EOF'
---
adr: "0001"
status: accepted
date: 2026-07-29
ground: brownfield
converge_pass: 2
spec_ref: "R-1"
supersedes: ""
superseded_by: ""
deciders: "owner"
---

# 0001 — payments link to orders on order_id

## Context

A planner would otherwise guess how payments attach to products.

## Decision

`payments.order_id` is the only column linking payments to orders. No
`payments.product_id` exists in this schema.

## Rejected reading

That payments carried a product reference directly. The column is absent.

## Evidence

```sh
printf '%s\n' 'payment_id order_id amount status'
```

observed: payment_id, order_id, amount, status, and created_at.

## Consequences

Product attribution travels through orders.
Re-verify when: the payments table gains or loses a column.
EOF

# This derived projection deliberately lies: canonical Task-Spec frontmatter
# must remain the work authority.
cat > "$WS/cvg/tasks/_state.yaml" <<'EOF'
schema_version: 1
last_rebuilt: 1970-01-01T00:00:00Z
tasks:
stats:
  total: 99
  ready: 0
  in_progress: 0
  blocked: 0
  done: 99
  parked: 0
EOF
: > "$WS/cvg/tasks/_metrics.jsonl"
python3 "$ROOT/skills/sketch-plans-adversarial-review/tests/gen-log.py" \
  "$WS/cvg/swimlanes" unresolved >/dev/null

srun() {
  (
    cd "$WS" &&
      CVG_HOME="$ROOT" CVG_PROJECT_ROOT="$WS" "$CVG" "$@"
  ) 2>/dev/null
}

echo "== cvg snapshot — WorkspaceSnapshot 3.0 =="

FULL="$(srun --json snapshot)"
if printf '%s' "$FULL" | python3 -c "import json,sys
d=json.load(sys.stdin)
s=d['data']['snapshot']
assert d['ok'] is True and d['command']=='snapshot'
assert d['changed'] is False and d['dry_run'] is False
assert set(d['data'])=={'snapshot'}
assert s['schemaVersion']=='3.0' and s['source']=='workspace'
assert __import__('re').fullmatch(r'ws3_[0-9a-f]{32}',s['snapshotId'])
assert s['project']['lane']=='FULL'
assert s['method']['activePassId']=='pass-4'
assert [p['gate']['ok'] for p in s['method']['passes'][:5]]==[True,True,True,True,False]
assert s['method']['passes'][6]['status']=='optional'
assert s['review']['unresolvedCount'] > 0
assert s['authorization']['state']=='blocked'
assert s['authorization']['nextPassId']=='pass-4'
assert s['authorization']['command']=='cvg review --check'
assert s['authorization']['mutation']=='non_mutating'
assert s['authorization']['dryRunSupported'] is True
assert s['authorization']['enabled'] is True
assert s['work']['stats']['total']==1 and s['work']['stats']['ready']==1
assert s['work']['frontier']['taskIds']==['T-20260602-golden']
d=s['decomposition']
assert d['availability']=='available'
assert [lane['id'] for lane in d['swimlanes']]==['swimlane-checkout']
lane=d['swimlanes'][0]
assert lane['thread'] is True and lane['risk']=='high' and lane['owner']=='payments-stream'
assert lane['seam']['inputContract']=='cart.*' and lane['seam']['outputContract']=='order.*'
assert lane['legIds']==['swimlane-checkout-leg-01','swimlane-checkout-leg-02']
assert [leg['order'] for leg in d['legs']]==[1,2]
assert d['legs'][1]['dependsOn']==['swimlane-checkout-leg-01']
assert [(edge['source'],edge['target']) for edge in d['edges']]==[('swimlane-checkout-leg-01','swimlane-checkout-leg-02')]
assert all(record['artifactIds'] for record in [*d['swimlanes'],*d['legs']])
paths={a['path']:a for a in s['artifacts']}
assert {'README.md','cvg/docs/guide.pdf','cvg/docs/CONTEXT.md','docs/handbook.pdf'} <= set(paths)
assert {paths[p]['id'] for p in ('README.md','cvg/docs/guide.pdf','cvg/docs/CONTEXT.md','docs/handbook.pdf')} <= set(s['project']['artifactIds'])
generic_documents=('README.md','cvg/docs/guide.pdf','docs/handbook.pdf')
assert all(paths[p]['provenance']['truthClass']=='observed' for p in generic_documents)
recognized_converge_artifacts=('cvg/docs/CONTEXT.md','cvg/docs/tech-spec/snapshot.md')
assert all(paths[p]['provenance']['truthClass']=='canonical' for p in recognized_converge_artifacts)
failed=[x for x in s['signals'] if x['kind']=='gate' and x.get('entity',{}).get('id')=='pass-4']
assert len(failed)==1 and failed[0]['severity']=='error'
assert {'workspace-control-plane','git','signing','engines','path-fence','consensus-record','tasks','execution','receipts','runtime-enforcement','plugin-parity','tracker-config'} <= {x['id'] for x in s['health']['checks']}
assert all('position' not in p for p in s['method']['passes'])
assert all('content' not in a and 'bytes' not in a for a in s['artifacts'])
assert all(not a['path'].startswith('/') and '..' not in a['path'].split('/') for a in s['artifacts'])
" 2>/dev/null; then
  ok "FULL lane holds THE BARRIER with typed read model"
else
  bad "FULL lane contract" "envelope, gate, authorization, or safety surface drifted"
fi

SID1="$(printf '%s' "$FULL" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['snapshot']['snapshotId'])")"
OBS1="$(printf '%s' "$FULL" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['snapshot']['observedAt'])")"
sleep 1
FULL2="$(srun snapshot --json)"
SID2="$(printf '%s' "$FULL2" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['snapshot']['snapshotId'])")"
OBS2="$(printf '%s' "$FULL2" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['snapshot']['observedAt'])")"
if [ -n "$SID1" ] && [ "$SID1" = "$SID2" ] && [ "$OBS1" != "$OBS2" ]; then
  ok "snapshotId is stable while observedAt changes"
else
  bad "canonical snapshot digest" "snapshotId included observation time or flag order"
fi

printf '\n' >> "$WS/cvg/tasks/T-20260602-golden.md"
SID3="$(srun --json snapshot | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['snapshot']['snapshotId'])")"
if [ "$SID3" != "$SID2" ]; then
  ok "canonical evidence bytes change snapshotId"
else
  bad "snapshot evidence digest" "canonical task mutation did not change the digest"
fi

# Once Consensus closes but no Task-Spec exists, the exact Pass 5 frontier is
# the newly added read-only preview. Cockpit must not skip straight to a
# mutating `tasks new` recommendation.
mv "$WS/cvg/tasks/T-20260602-golden.md" "$WS/T-20260602-golden.hold"
python3 "$ROOT/skills/sketch-plans-adversarial-review/tests/gen-log.py" \
  "$WS/cvg/swimlanes" good >/dev/null
PASS5_GATE="$(srun --json review --check)"
PASS5="$(srun --json snapshot)"
if printf '%s' "$PASS5" | python3 -c "import json,sys
s=json.load(sys.stdin)['data']['snapshot']
assert s['method']['activePassId']=='pass-5'
assert s['method']['passes'][5]['gate']['command']=='cvg tasks plan'
assert s['work']['availability']=='empty'
assert s['authorization']['state']=='allowed'
assert s['authorization']['nextPassId']=='pass-5'
assert s['authorization']['command']=='cvg tasks plan'
assert s['authorization']['mutation']=='non_mutating'
assert s['authorization']['dryRunSupported'] is True
" 2>/dev/null; then
  ok "Pass 5 authorizes the read-only task preview before creation"
else
  PASS5_DETAIL="$(printf '%s' "$PASS5" | python3 -c "import json,sys
s=json.load(sys.stdin)['data']['snapshot']
print('active=%r work=%r command=%r mutation=%r' % (
  s['method']['activePassId'], s['work']['availability'],
  s['authorization']['command'], s['authorization']['mutation']))
" 2>/dev/null)"
  PASS5_GATE_DETAIL="$(printf '%s' "$PASS5_GATE" | python3 -c "import json,sys
d=json.load(sys.stdin)
print('gate_ok=%r gate_verdict=%r gate_output=%r' % (
  d['ok'], d['verdict'], d.get('data',{}).get('output')))
" 2>/dev/null)"
  bad "Pass 5 preview frontier" "${PASS5_DETAIL:-snapshot skipped}; ${PASS5_GATE_DETAIL:-gate unavailable}"
fi
mv "$WS/T-20260602-golden.hold" "$WS/cvg/tasks/T-20260602-golden.md"
python3 "$ROOT/skills/sketch-plans-adversarial-review/tests/gen-log.py" \
  "$WS/cvg/swimlanes" unresolved >/dev/null

# NORMAL deliberately omits Capture, Decompose, and Consensus. Their evidence
# remains observable, but those ceremonies cannot become hidden blockers.
printf 'lane=NORMAL\n' > "$WS/.cvg/config"
NORMAL="$(srun --json snapshot)"
if printf '%s' "$NORMAL" | python3 -c "import json,sys
s=json.load(sys.stdin)['data']['snapshot']
statuses={p['order']:p['status'] for p in s['method']['passes']}
gates={p['order']:p['gate']['ok'] for p in s['method']['passes']}
gate_signals={x.get('entity',{}).get('id') for x in s['signals'] if x['kind']=='gate'}
assert s['project']['lane']=='NORMAL'
assert s['method']['activePassId']=='pass-7'
assert statuses=={0:'skipped',1:'complete',2:'complete',3:'skipped',4:'skipped',5:'complete',6:'optional',7:'active',8:'waiting'}
assert gates[1] is True and gates[2] is True
assert all(gates[i] is None for i in (0,3,4,5,6,7,8))
assert gate_signals=={'pass-1','pass-2'}
assert s['authorization']['state']=='allowed'
assert s['authorization']['nextPassId']=='pass-7'
assert s['authorization']['command']=='cvg bind --check --profile <profile>'
assert s['decomposition']['availability']=='available'
assert not any(i['code'] in {'PASS_GATE_BLOCKED','REVIEW_UNRESOLVED'} for i in s['issues'])
" 2>/dev/null; then
  ok "NORMAL lane skips omitted ceremonies without hiding evidence"
else
  bad "NORMAL lane contract" "lane order, skipped passes, or authorization drifted"
fi

# Populate the optional domains with a bound run, durable checkpoint/handoff,
# and a receipt whose task/profile digests are both current.
RUN_DIR="$WS/cvg/execution/T-20260602-golden"
LOOP_DIR="$WS/cvg/loop/T-20260602-golden"
mkdir -p "$RUN_DIR" "$LOOP_DIR"
cat > "$RUN_DIR/execution-profile.yaml" <<'EOF'
{
  "schema": "cvg.execution-profile.v1",
  "task": {
    "id": "T-20260602-golden"
  },
  "enforcement": {
    "primary_runtime": "codex",
    "assurance": "supervised"
  }
}
EOF
cat > "$LOOP_DIR/state.env" <<'EOF'
ITER=2
STRIKES=1
TOKENS_USED=345
STARTED_AT=1785790000
ELAPSED_PRIOR=45
LAST_FINGERPRINT=fixture
EOF
cat > "$LOOP_DIR/HANDOFF.md" <<'EOF'
# Handoff

Resume from the verified checkpoint.
EOF
TASK_SHA="$(shasum -a 256 "$WS/cvg/tasks/T-20260602-golden.md" | awk '{print $1}')"
PROFILE_SHA="$(shasum -a 256 "$RUN_DIR/execution-profile.yaml" | awk '{print $1}')"
cat > "$WS/cvg/receipts/T-20260602-golden.json" <<EOF
{
  "schema": "cvg.execution-receipt.v1",
  "task_id": "T-20260602-golden",
  "result": "pass",
  "task_spec": {
    "path": "cvg/tasks/T-20260602-golden.md",
    "sha256": "$TASK_SHA"
  },
  "execution_profile": {
    "path": "cvg/execution/T-20260602-golden/execution-profile.yaml",
    "sha256": "$PROFILE_SHA"
  },
  "evaluation": {
    "output_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "path_policy": "pass"
  },
  "runtime": {
    "agent": "fixture",
    "branch": "fixture"
  },
  "recorded_at": "2026-08-03T12:00:00Z",
  "generated_by": "task-loop"
}
EOF

SETTLED="$(srun --json snapshot)"
if printf '%s' "$SETTLED" | python3 -c "import json,sys
s=json.load(sys.stdin)['data']['snapshot']
assert s['method']['activePassId'] is None
assert s['authorization']=={
  'state':'complete','nextPassId':None,'command':None,
  'rationale':'The Converge descent is complete for the selected lane.',
  'blockingIssueIds':[],'mutation':'none','dryRunSupported':False,'enabled':False
}
assert s['execution']['availability']=='available' and len(s['execution']['runs'])==1
r=s['execution']['runs'][0]
assert r['taskId']=='T-20260602-golden' and r['state']=='settled'
assert r['attempt']==2 and r['budgetIterations']==15
assert r['runtime']=={'primaryRuntime':'codex','assurance':'supervised'}
assert r['checkpoint']['strikes']==1 and r['checkpoint']['tokensUsed']==345
assert r['checkpoint']['elapsedSeconds']==45 and r['checkpoint']['artifactId']
assert r['terminal']=={'result':'pass','recordedAt':'2026-08-03T12:00:00Z'}
assert r['handoffArtifactId'] and r['profileArtifactId']
assert s['receipts']['availability']=='available' and len(s['receipts']['items'])==1
receipt=s['receipts']['items'][0]
assert receipt['integrity']=='verified' and receipt['freshness']=='current'
assert receipt['bindings']['task']['matches'] is True
assert receipt['bindings']['executionProfile']['matches'] is True
assert receipt['bindings']['evaluationOutputSha256']=='a'*64
assert receipt['bindings']['pathPolicy']=='pass'
assert receipt['provenance']=={'generatedBy':'task-loop','postHoc':False}
assert any(x['kind']=='receipt' and x['severity']=='success' for x in s['signals'])
" 2>/dev/null; then
  ok "runtime checkpoint and current receipt retain provenance"
else
  bad "runtime and receipt contract" "non-empty lifecycle domains drifted"
fi

printf '\n' >> "$RUN_DIR/execution-profile.yaml"
STALE="$(srun --json snapshot)"
if printf '%s' "$STALE" | python3 -c "import json,sys
s=json.load(sys.stdin)['data']['snapshot']
r=s['receipts']['items'][0]
assert r['integrity']=='mismatch' and r['freshness']=='stale'
assert r['bindings']['task']['matches'] is True
assert r['bindings']['executionProfile']['matches'] is False
issues=[i for i in s['issues'] if i['code']=='RECEIPT_INTEGRITY_MISMATCH']
assert len(issues)==1 and issues[0]['severity']=='blocking'
" 2>/dev/null; then
  ok "stale receipt is typed and never presented as current"
else
  bad "receipt freshness" "profile drift did not invalidate the receipt"
fi

printf 'lane=normal\n' > "$WS/.cvg/config"
INVALID="$(srun --json snapshot)"
INVALID_RC=$?
if [ "$INVALID_RC" -eq 2 ] \
  && printf '%s' "$INVALID" | python3 -c "import json,sys
d=json.load(sys.stdin)
assert d['ok'] is False and d['exit_code']==2
assert d['error']['code']=='USAGE_ERROR'
assert 'invalid lane' in d['error']['message']
" 2>/dev/null; then
  ok "invalid configured lane fails closed in the JSON envelope"
else
  bad "strict lane validation" "invalid lane was accepted or not enveloped"
fi

# The typed projection supports both the legacy *.plan.md filenames above and
# the canonical directory layout. Broken and ambiguous DAGs fail closed.
printf 'lane=FULL\n' > "$WS/.cvg/config"
mv "$WS/cvg/swimlanes" "$WS/legacy-swimlanes"
mkdir -p "$WS/cvg/swimlanes"
cp -R "$ROOT/skills/reqs-to-swimlane-plans/tests/fixtures/good-lane/." \
  "$WS/cvg/swimlanes/"
CANONICAL="$(srun --json snapshot)"
if printf '%s' "$CANONICAL" | python3 -c "import json,sys
s=json.load(sys.stdin)['data']['snapshot']
d=s['decomposition']
assert d['availability']=='available'
assert d['swimlanes'][0]['artifactIds'] and all(x['artifactIds'] for x in d['legs'])
leg=next(x for x in d['legs'] if x['id']=='swimlane-checkout-leg-02')
assert leg['proves'][0]=='Given a validated cart, when payment succeeds, then exactly one order.* row is published for fulfillment.'
assert leg['produces']==['the order.* published contract, with its payment outcome preserved for fulfillment.']
assert any(i['code']=='DECOMPOSITION_PARENT_MISMATCH' for i in s['issues'])
" 2>/dev/null; then
  ok "canonical decomposition preserves wrapped prose without trusting stale parent links"
else
  bad "canonical decomposition" "canonical lane/leg layout was not projected"
fi

sed -i.bak 's/depends_on: \[swimlane-checkout-leg-01\]/depends_on: [swimlane-missing-leg-09]/' \
  "$WS/cvg/swimlanes/checkout/leg-02-stripe.md"
rm -f "$WS/cvg/swimlanes/checkout/leg-02-stripe.md.bak"
DANGLING="$(srun --json snapshot)"
if printf '%s' "$DANGLING" | python3 -c "import json,sys
s=json.load(sys.stdin)['data']['snapshot']
assert s['decomposition']['availability']=='unavailable'
assert s['decomposition']['swimlanes']==[]
assert s['decomposition']['legs']==[]
assert s['decomposition']['edges']==[]
assert any(i['code']=='DECOMPOSITION_DEPENDENCY_DANGLING' for i in s['issues'])
assert not any(
  record.get('entity',{}).get('kind') in {'swimlane','leg'}
  for record in [*s['issues'],*s['artifacts']]
)
" 2>/dev/null; then
  ok "dangling leg dependency makes decomposition unavailable"
else
  bad "dangling decomposition dependency" "unknown leg edge was accepted"
fi
sed -i.bak 's/depends_on: \[swimlane-missing-leg-09\]/depends_on: [swimlane-checkout-leg-01]/' \
  "$WS/cvg/swimlanes/checkout/leg-02-stripe.md"
rm -f "$WS/cvg/swimlanes/checkout/leg-02-stripe.md.bak"

mkdir -p "$WS/swimlanes"
cp -R "$ROOT/skills/reqs-to-swimlane-plans/tests/fixtures/good-lane/." \
  "$WS/swimlanes/"
AMBIGUOUS="$(srun --json snapshot)"
if printf '%s' "$AMBIGUOUS" | python3 -c "import json,sys
s=json.load(sys.stdin)['data']['snapshot']
assert s['decomposition']=={'availability':'unavailable','swimlanes':[],'legs':[],'edges':[]}
assert any(i['code']=='DECOMPOSITION_TREE_AMBIGUOUS' for i in s['issues'])
" 2>/dev/null; then
  ok "multiple non-empty decomposition trees fail closed"
else
  bad "ambiguous decomposition trees" "producer silently chose a tree"
fi

if printf '%s' "$FULL" | python3 -c "import json,sys
s=json.load(sys.stdin)['data']['snapshot']
schema=json.load(open('$ROOT/contracts/ui/v3/workspace-snapshot.schema.json'))
assert set(schema['required'])==set(s)
assert schema['properties']['schemaVersion']['const']==s['schemaVersion']
assert schema['properties']['source']['enum']==['workspace','fixture']
" 2>/dev/null; then
  ok "checked-in schema matches the emitted top-level surface"
else
  bad "WorkspaceSnapshot schema" "schema is invalid or top-level keys drifted"
fi

if "$CVG" help | grep -q '^  snapshot ' \
  && CVG_HOME="$ROOT" "$CVG" agent-context | python3 -c "import json,sys
d=json.load(sys.stdin)
rows=[c for c in d['commands'] if c['name']=='snapshot']
assert len(rows)==1 and rows[0]['mutating'] is False
" 2>/dev/null; then
  ok "snapshot is discoverable and classified non-mutating"
else
  bad "snapshot discovery" "help or agent-context contract is missing"
fi

echo
if [ "$F" -eq 0 ]; then
  echo "PASS — all $T rows green."
  exit 0
fi
echo "FAIL — $F of $T rows red." >&2
exit 1
