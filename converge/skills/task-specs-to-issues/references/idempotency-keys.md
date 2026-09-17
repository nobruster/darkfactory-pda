# Idempotency keys — how each tracker carries the spec `id`

Re-running `register.sh` **must not create duplicate issues**. Every adapter
carries the spec `id` on the issue as a durable, greppable key, looks the issue
up by that key first, and **updates in place** if found. This is the single
mechanism that makes the projection idempotent — "look up by id, update else
create." If the key is ever stripped, the next run creates a second issue
instead of updating; restoring the key repairs it (see the SKILL.md
Troubleshooting row on duplicate issues).

The key is always the spec `id` (e.g. `T-20260625-bronze-views`) verbatim — the
same string that appears in `depends_on`, so link resolution and upsert lookup
share one key space.

## GitHub — HTML marker + label

- **Carrier:** an HTML comment embedded in the issue body:
  ```
  <!-- task-spec: T-20260625-bronze-views -->
  ```
  It renders invisibly in Markdown, survives edits, and is trivially greppable.
  Plus a `task-spec` label so the whole registered set is one filter.
- **Lookup:** `gh issue list --label task-spec --state all --search "<marker> in:body" --json number,body`,
  then `jq` filters bodies that `contains` the exact marker and takes the first
  number. `--state all` means a **closed (done)** issue is still updated in
  place, never re-created.
- **Failure mode:** someone deletes the HTML comment from the body → the next
  lookup misses → a duplicate is created. Fix: paste the marker back into the
  original issue's body.

## Linear — an attachment with a unique URL

> **Correction (verified against the live API):** Linear has **no `externalId`
> field** on `Issue` / `IssueCreateInput` / `IssueFilter`. An earlier version of
> this adapter assumed one, and every call failed with *"Field 'externalId' is not
> defined by type 'IssueCreateInput'"*. The mechanism below is Linear's own
> documented pattern for stateless external integrations.

- **Carrier:** an **attachment** whose `url` is deterministic and unique per spec —
  `https://cvg.local/task-spec/<id>` by default (override the prefix with
  `TSI_LINEAR_MARKER_BASE`). Per Linear's docs: *"Attachment URL is used as an
  idempotent value if used in conjunction with the same issue id … you can also
  query an attachment, and the associated issue, by its URL."*
  ([linear.app/developers/attachments](https://linear.app/developers/attachments))
- **Lookup:** `attachmentsForURL(url: "<marker>") { nodes { issue { id } } }`
  returns the issue UUID; upsert then `issueUpdate`s it, else `issueCreate`s and
  immediately `attachmentCreate`s the marker so the *next* run resolves it.
- **Failure mode:** an issue created by hand (no marker attachment) → lookup
  misses → a duplicate is created. Fix: add an attachment with the marker URL to
  the hand-made issue. Deleting the attachment has the same effect as stripping
  the GitHub HTML marker.
- **Note:** because `attachmentsForURL` is workspace-wide, the marker is unique
  across teams — the spec id alone identifies the mirror.

## Jira — label + summary tag

- **Carrier:** a `task-spec:<id>` **label** (the machine key) plus a
  `[task-spec:<id>]` prefix on the **summary** (a human-visible echo). The label
  is what lookup keys on; the summary tag is redundancy for eyeballs.
- **Lookup:** JQL `project = KEY AND labels = "task-spec:<id>"` → the first
  issue key; upsert `PUT`s if found, else `POST`s a new issue carrying the label.
- **Status:** the Jira adapter is **code-complete but gated** — every verb is
  fully implemented (the lookup is real; the Done transition is resolved at
  runtime via `.to.statusCategory.key=="done"`), but write verbs stay behind
  `TSI_JIRA_ENABLE=1` until a maintainer validates the create/transition payloads
  against a live project.

## Invariants every adapter upholds

1. **One key per spec, one spec per key.** The id is unique in `tasks/`, so the
   key is unique on the board. Never fan-out (1 spec → 2 issues) and never merge
   (2 specs → 1 issue).
2. **Lookup before write.** Upsert always resolves the key first; create is the
   fallback, not the default.
3. **The key is stable across re-runs.** Editing a spec's title changes the
   issue title on the next run but **not** the key — so the same issue is
   patched, not duplicated. (SKILL.md Example 3.)
4. **Links resolve through the same key.** `link --from X --to Y` resolves both
   ids via the identical lookup, so the dependency graph and the issue set can
   never drift apart.
