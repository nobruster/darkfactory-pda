# Dependency graph — `depends_on` → `blocked-by`

The graph that lived in the repo (`depends_on` in each spec's frontmatter) must
live on the board (as `blocked-by` links) so the loop can compute "ready" — an
issue with no open blocker — **without reading `tasks/`**. This doc is the exact
mapping, the cycle rule, and this repo's canonical build order.

## The edge mapping

Frontmatter carries dependencies as a **YAML inline list**:

```yaml
depends_on: [T-20260625-silver-conform, T-20260625-bronze-views]
depends_on: []        # a root — no dependency
```

Each element becomes **one `blocked-by` link**:

```text
spec X depends_on [A, B]   ⇒   issue(X) blocked-by issue(A)
                                issue(X) blocked-by issue(B)
```

Direction, stated three ways so it is unambiguous:

- **A must be built before X.**
- **X is blocked by A** (X cannot start until A is done).
- **On the tracker:** GitHub — a `blocked by #A` task-list line on X's issue;
  Linear — `issueRelation { issueId: A, relatedIssueId: X, type: blocks }` (A
  *blocks* X); Jira — an issue link `A "Blocks" X` (X "is blocked by" A).

**No extra links, no missing links.** The gate asserts
`count(blocked-by links) == count(depends_on edges)`.

## Parsing the inline list (bash-3.2-safe)

`_parse.sh`'s `tsi_depends_on` flattens `[a, b]` to a space-separated id list
with pure `sed`/`tr` — no arrays, no `mapfile`:

```text
depends_on: [T-a, T-b]  → strip [ ]  → split on ,  → trim  → "T-a T-b"
depends_on: []          → ""          (a root)
```

Callers iterate it with an unquoted `for dep in $(tsi_depends_on "$f")`, which
is safe because task ids never contain whitespace.

## Cycle detection (Kahn peel)

A `depends_on` loop is a **spec bug (Pass 5), not a board state** — registration
refuses the whole run rather than write a graph the loop could never drain.
`register.sh` and `verify-registration.sh` both run Kahn's algorithm over the
signed-off subgraph, held entirely in newline-delimited scratch files:

1. A node is a **root** when it has no remaining `depends_on` edge (never appears
   in column 1 of the live edge list).
2. Emit all current roots (sorted, stable), drop them from the node set, and
   remove edges whose **target** is now emitted (that dependency is satisfied).
3. Repeat. If a pass finds **no root while nodes remain**, the remaining nodes
   form a cycle → print them as evidence and exit `1`.

The emission order is exactly the **build order** (dependencies first), which is
the order `register.sh` upserts issues so a `blocked-by` target always exists
before the link that points at it.

## Dangling-edge rule

Every `depends_on` target must itself be a **signed-off** spec. A dependency on
an un-gated or unknown id means the `blocked-by` link would point at an issue
that was never created. Both scripts hard-stop with `blocked-by target not
found for T-x` — the fix is upstream: sign off + register the dependency, or
correct the stale `depends_on`.

## This repo's canonical build order

Seven specs, one lane per dbt/serving layer. The signed-off subset is what
actually registers; the full graph is:

```text
bronze-views                     depends_on []                         ← root
   └─ silver-conform             depends_on [bronze-views]
        ├─ gold-marts            depends_on [silver-conform]
        └─ gold-freshness        depends_on [silver-conform]
              └─ gold-atomic-publish  depends_on [gold-marts, gold-freshness]
                    └─ api-fastapi    depends_on [gold-marts, gold-freshness, gold-atomic-publish]
                          └─ mcp-tools depends_on [api-fastapi]
```

As a linear build order (dependencies first):

```text
bronze-views → silver-conform → { gold-marts, gold-freshness }
             → gold-atomic-publish → api-fastapi → mcp-tools
```

Edge count when all seven are signed off, counted straight off the real
frontmatter: **9 blocked-by links** — silver:1, gold-marts:1, gold-freshness:1,
gold-atomic-publish:2, api-fastapi:3 (`[gold-marts, gold-freshness,
gold-atomic-publish]`), mcp-tools:1. `register.sh` derives this count from the
specs themselves, so the number always tracks the actual `depends_on` fields
rather than any prose. The **ready set** (no open blocker) at full registration
is exactly
`[bronze-views]` — the single root the loop pulls first. Today only
`bronze-views` is `signed_off: true`, so registration writes **one** issue with
**zero** links and a ready set of `[bronze-views]`; the other six are skipped and
reported until they pass the safe-to-delegate gate (Pass 5).
