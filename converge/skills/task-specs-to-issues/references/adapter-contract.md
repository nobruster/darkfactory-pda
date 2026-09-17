# Adapter contract — the pluggable tracker backend

The tracker is a **pluggable backend behind one CLI**. `register.sh` and the
future Manager never speak GitHub, Linear, or Jira directly — they call
`scripts/adapters/<tracker>.sh <verb> ...`. Swapping trackers is a `--tracker`
flag, never a code change. This is the same "port with interchangeable adapters"
shape the repo uses for `postgres → duckdb → dbt → MCP`: the seam is the
contract, not the vendor.

## The two-method spine (what the loop needs)

The loop reads a board and writes a result. Everything else is registration
plumbing. The irreducible surface is two methods:

| Method | Who calls it | What it does |
|--------|--------------|--------------|
| **read ready** — `adapter list-ready` | the loop / Manager | emit the issues with **no open `blocked-by`** — the work that is safe to pull now. One id/number per line. |
| **write result** — `adapter write-result --issue N --status pass\|fail [--pr URL] [--reason TEXT]` | Pass 8 `task-loop` | record the eval outcome: a green eval closes the issue (with the linked PR); a red eval leaves it open with a failure comment. |

## The six verbs (registration adds three, the gate adds one)

Registration (`register.sh`) needs three more verbs on top of the spine, and the
verify gate needs one read-only listing. Every adapter implements the **same six**:

| Verb | Signature | Contract |
|------|-----------|----------|
| `preflight` | `adapter preflight` | Assert the backend is reachable/authenticated. Exit `0` ok, `1` with a one-line remediation on failure. **Called before any write** so we never half-register. |
| `upsert` | `adapter upsert --id ID --title T --body-file F [--label L ...]` | Find-by-id-key **else** create. Idempotent. Echoes the resulting issue number/id on stdout; human notes (`created …` / `updated …`) go to stderr. |
| `link` | `adapter link --from ID --to ID` | Set a `blocked-by` from FROM's issue to TO's issue (resolving each spec id → issue). Idempotent — re-linking is a no-op. |
| `list-ready` | `adapter list-ready` | (spine) issues with no open blocker. |
| `list-issues` | `adapter list-issues` | (gate) EVERY registered issue as `extid<TAB>ref`, keyed on the spec id its marker carries. Read-only; backs `verify-registration.sh`'s 1:1 parity check (count · orphan · missing · double-registration). An issue carrying the marker-label but no marker is skipped. |
| `write-result` | `adapter write-result --issue N --status pass\|fail …` | (spine) the loop's write side; **not used during registration**. |

### stdout / stderr discipline

- **stdout is the return channel.** `upsert` prints the issue id and nothing
  else on stdout; `list-ready` prints ids one per line. `register.sh` captures
  stdout, so any diagnostic MUST go to stderr.
- **stderr is for humans + the run log.** Adapters emit `created #N (id)` /
  `updated #N (id)` / `linked …` on stderr; `register.sh` greps its captured
  adapter log for `^created `/`^updated ` to report the created-vs-updated split.
- **Exit non-zero on any failure.** `register.sh` runs under `set -euo pipefail`
  and aborts the whole run on the first adapter error — half a board is worse
  than none.

## Idempotency is per-adapter, keyed on the spec `id`

Every verb that mutates keys on the spec `id`. See
[`idempotency-keys.md`](./idempotency-keys.md) for how each backend carries it:

- **github** — an HTML marker `<!-- task-spec: ID -->` in the issue body + a
  `task-spec` label; lookup greps the marker.
- **linear** — the native `externalId` field; lookup filters on it.
- **jira** — a `task-spec:<id>` label + a `[task-spec:<id>]` summary tag; lookup
  is JQL on the label.

## Backend status

| Adapter | preflight | upsert | link | list-ready | list-issues | write-result | Notes |
|---------|-----------|--------|------|------------|-------------|--------------|-------|
| `github.sh` | live | live | live | live | live | live | pure `gh` + `jq`; blocked-by is a task-list line in a `### Blocked by` body section. |
| `linear.sh` | live | live | live | live | live | live | GraphQL over `curl`; blocked-by is a native `issueRelation type: blocks`. `upsert` returns the human identifier (`ENG-42`). All network calls isolated in `_linear_gql*`. |
| `jira.sh` | live | code-complete¹ | code-complete¹ | code-complete¹ | code-complete¹ | code-complete¹ | REST v3 shapes complete incl. **runtime Done-transition resolution** (`.to.statusCategory.key=="done"`); write verbs gated behind `TSI_JIRA_ENABLE=1` until validated against a live project. |
| `fake.sh` | live | live | live | live | live | live | **test-only, no network** — on-disk store under `$TSI_FAKE_STORE`, deterministic `FAKE-N` ids. The reference adapter and the backend for `tests/test-register.sh`; never a real board. |

¹ *code-complete* = the request shapes are fully written and self-consistent, but
the write verbs are held behind `TSI_JIRA_ENABLE=1` until they have been run once
against a live Jira project. Promote by validating, then dropping the guard.

**Adapter-specific helper verbs** (beyond the universal six): `linear.sh` adds
`teams` (list `key<TAB>name<TAB>uuid`) and `resolve-team` (a team KEY like `CVG`
→ its UUID). These power the one-secret setup — `LINEAR_TEAM_ID` accepts a team
**key or UUID**, and `cvg setup tracker linear` discovers/records the team so the
user only ever exports the API key. They don't change the six-verb contract.

## Why an adapter and not a library

The spec is the floor; the board is a **shadow** of it (exactly as Postgres is
the floor under `raw.*`). If the board and `tasks/*` ever disagree on what the
work is, the spec wins and the board is re-registered — the projection is
one-way. Because the board is disposable and re-derivable, the backend that
holds it is a detail behind this contract, and the day the team moves trackers
is the day someone writes one more `adapters/<new>.sh` with these six verbs.

## Adding a tracker (the recipe)

The core (`register.sh` / `verify-registration.sh`) is **tracker-agnostic** — it
speaks only the six verbs. Supporting a new backend is one new file, no core
change. This is deliberately the opposite of shipping a dozen half-built
backends: **thin adapters behind one agnostic core** beats broad-but-shallow
(the same lesson production multi-tracker tools like *spectryn* encode — 13
trackers, one ports-and-adapters core). Recipe:

1. **Copy `adapters/fake.sh`** — it is the smallest COMPLETE adapter (~130 lines,
   no network) and the clearest template for the six verbs, the stdout/stderr
   discipline, and the dispatch block.
2. **Pick the idempotency carrier** (see `idempotency-keys.md`): a native
   external-id field (best), else a label + a body/description marker. `upsert`
   MUST look up by it before creating.
3. **Map the dependency edge** to the tracker's native "blocks / blocked-by"
   relation (or, if none exists, a greppable convention like the GitHub
   task-list line). `link --from X --to Y` sets X *blocked-by* Y.
4. **`preflight`** asserts auth/reachability and exits non-zero with a one-line
   remediation — this is what keeps a run from half-registering.
5. **Exit 0 on success, always** — including `list-ready` with an empty result
   (a trailing false `[[ … ]] && echo` must not leak a non-zero status, or a
   caller doing `list-ready > f || …` will discard the output).
6. **Add the tracker name** to the `--tracker` allow-list in `register.sh` and
   `verify-registration.sh`, then prove it offline against `test-register.sh`'s
   shape (point `TSI_*` env at a sandbox, or add a fake-style store).

### Documented extension slots (not yet shipped)

Shipped today: `github`, `linear`, `jira` (gated), `fake` (test). These are the
common next backends — each is a ~130-line file following the recipe above; none
is stubbed in-tree, so the surface stays lean and honest:

| Tracker | Idempotency carrier | Blocked-by relation |
|---------|---------------------|---------------------|
| **GitLab** issues | issue description marker + label | linked issues, `blocks` type |
| **Azure DevOps** work items | a tag + a field marker | `Predecessor/Successor` link |
| **Asana** tasks | external-id (`external.gid`) | dependencies (`addDependencies`) |
| **ClickUp** tasks | a custom field or tag | task `waiting_on` dependency |
| **Shortcut** stories | external-id field | story links, `blocks` |
| **Notion** DB pages | a `task-spec id` property | a relation property |

Adding any of these is a pull request against this contract, not a redesign.
