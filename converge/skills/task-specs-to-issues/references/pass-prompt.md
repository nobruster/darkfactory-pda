# Pass 6 · Register — specs ⇄ tracker board (opt-in)

**Mission:** project the sealed backlog onto a tracker board — one spec, one
issue, dependencies as blocked-by links — so humans and Managers watch the
same truth the repo holds.

**Inputs:** the sealed specs in `cvg/tasks/`. A connected tracker
(`cvg setup tracker linear|github|jira`; key via `cvg setup key`, which
stores it in the OS keychain — never the repo).

**Procedure:**
1. Preview first: `cvg register --dry-run` — read what would be created.
2. `cvg register` → `REGISTER=OK`. Re-runs upsert; they never duplicate.
   Each spec gets a `tracker_ref` receipt stamped back into it.
3. Gate the mapping: `cvg register --check` → `CHECK_REGISTER=OK`
   (1:1 parity, every `depends_on` one blocked-by link, no cycle, no
   un-gated spec leaked to the board).
4. File the board-mapping decisions → `cvg/brain/decisions/`.

**Boundaries:** the referee holds no tracker credentials — the adapter
authenticates itself. The board is a *projection*: the repo's specs remain
the source of truth, and `cvg ready` (repo-local) remains the dispatch
frontier.

**Exit:** `CHECK_REGISTER=OK`.

**Hands off to:** Pass 7 (Bind).
