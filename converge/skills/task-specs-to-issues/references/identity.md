# `.cvg/identity` — routing a spec to a tracker identity

A spec says *what kind of executor* it needs — `execution_backend: claude`,
`agent: python-developer` — never *which tracker identity*. The
**identity** is the local, opt-in lookup that turns those routing choices
into a person, service account, or future engine identity, so `register.sh` can
seed a Linear issue's `assigneeId`.

It is **optional**. With no identity, assignee resolution is a fail-soft
miss and the issue registers without it — the base projection is unchanged.
Nothing here ever gates a registration.

## Format

Plain `KEY=VALUE` lines, one per mapping — the same shape and guarantees as
`.cvg/config`: greppable, bash-3.2-safe, idempotent replace-or-append.

```
# .cvg/identity
agent:python-developer=ana@owshq.com
backend:claude=luan@owshq.com
backend:codex=luan@owshq.com
default=luan@owshq.com
```

Blank lines and whole-line `#` comments are allowed. Keys must be exactly
`default`, `backend:<safe-token>`, or `agent:<safe-token>`; values must be
non-empty and may not contain `=`. Duplicate keys, malformed lines, symlinks,
and files larger than 64 KiB are rejected. The CLI writes through a same-
directory atomic rename and sets mode `0600`.

**Keys** are routing choices, matched against a spec's frontmatter:

| key | matches | example |
|-----|---------|---------|
| `agent:<role>` | the spec's `agent:` (its needed role) | `agent:python-developer` |
| `backend:<engine>` | the spec's `execution_backend:` (which harness runs it) | `backend:claude` |
| `default` | the catch-all when nothing more specific maps | `default` |

**Values** are a Linear **email** or **user uuid**. A uuid passes straight
through; an email is resolved via `users(filter:{ email:{ eq } })` to a uuid at
register time (`_ln_resolve_user`). An email that matches no active user is a
fail-soft skip.

## Local choices, never credentials

An email or a user id is a **routing choice**, not a credential. The file
remains machine-local because it is organization-specific and may identify people.
This repository's `.gitignore` ignores `.cvg/*` except the tracked gate policy;
in a new consuming repository, the first setup write also adds the local
config/identity/cache paths to `.git/info/exclude`. `cvg` bridges only its path
(`TSI_IDENTITY`) into the adapter; it never stores or forwards a Linear API
key. See the SKILL.md trust model and
[adapter-contract.md](./adapter-contract.md).

## How register resolves an assignee

The driver picks the **most specific** key that carries signal, and the adapter
resolves it — falling back to `default` when the specific key is unmapped:

```
agent:<role>   (if agent is a real role, not "any"/none)
     ↓ else
backend:<engine>   (if execution_backend is set)
     ↓ else
default
```

So `agent: python-developer` wins over `execution_backend: claude`; a spec whose
`agent: any` falls back to its backend; a spec with neither still picks up the
`default` mapping if one exists. Resolution and the `default` fallback both live
in the adapter (`_ln_identity_lookup` → `_ln_resolve_user`), so the driver just
supplies one key and the projection stays portable — github/jira ignore it.

`assigneeId` is **seed-once** (applied on create only), so re-registering never
re-assigns an issue a human has since re-routed on the board.

## Subscribers

`subscriberIds` does **not** use `.cvg/identity`. It is derived directly from
the spec's `signed_off_by` (comma/space separated — each token resolved
independently, unresolvable ones skipped). Unlike the assignee, subscribers are
**union-merged**: the adapter reads the issue's current subscribers and adds to
them, so a human who subscribed on the board is never dropped by a re-register.

## Managing it

```
cvg setup identity                      # discover tracker identities
cvg setup identity --map backend:claude=you@org.com
cvg setup identity --map agent:coder=you@org.com --map default=you@org.com
```

`cvg setup identity` (no flags / `--list`) calls the adapter's `users` verb
to list the workspace's members as a ready-to-paste block; `--map KEY=VALUE`
writes atomically and idempotently. Coverage shows on `cvg setup` as an
informational row — it never blocks `READY`, because an unmapped assignee is
fail-soft by design.
