# Pass 7 · Bind — freeze the execution contract

**Mission:** turn one sealed spec into an enforceable execution contract:
what may be written, which evidence is pinned, what this host can actually
enforce. Fail closed on anything the host cannot honor.

**Inputs:** a sealed spec from the `cvg ready` frontier (ready AND all
dependencies done — never bind past the frontier).

**Procedure:**
1. Attest the host once per session: `cvg doctor runtime-contract`
   → `DOCTOR_RUNTIME_CONTRACT=OK` (or `DEGRADED` — read what it can't
   enforce before proceeding).
2. `cvg bind --task <spec>` → writes the execution profile + portable path
   guards + engine adapter manifests under `cvg/execution/`, hash-binds the
   spec and its evidence → `CHECK_RUNTIME_CONTRACT=PASS`.
3. Before dispatch (or after any pause): `cvg bind --check --task <spec>` —
   the genuinely read-only freshness recheck.

**Boundaries:** the write fence (`.cvg/gate.yaml`) can never be widened by a
task — if the work needs a path the fence forbids, that's a human
conversation, not an edit. `cvg gate --path <p>` answers what the fence
allows.

**Exit:** `CHECK_RUNTIME_CONTRACT=PASS`, profile present in
`cvg/execution/`.

**Hands off to:** Pass 8 (The Loop).
