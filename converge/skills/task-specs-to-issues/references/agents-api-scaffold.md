# Linear Agents API — the scaffold, the prerequisite, and the seam

converge's Linear projection stops at the boundary of what a **personal API key**
can do. Everything in `adapters/linear.sh` — issues, relations, attachments,
labels, comments, state moves — is reachable with `LINEAR_API_KEY` acting as a
human. The **Agents API** is not: it needs the tracker to treat converge as a
first-class *agent* (an app user that can be assigned work, be @mentioned, and
narrate a live **AgentSession**), and that requires a credential and a runtime a
stateless referee CLI does not have.

Rather than half-ship it, T4 lands as a **scaffold** —
[`scripts/adapters/linear-agents.sh.scaffold`](../scripts/adapters/linear-agents.sh.scaffold)
— that is deliberately **never sourced, never dispatched, never advertised**.
This doc is the promotion runbook: the prerequisite that blocks it, and the
exact seams where it plugs into the code that already exists.

> Verify the API specifics (scope names, webhook `resourceTypes`, session/status
> enums, activity content shape) against Linear's current developer docs at
> wire-time — [linear.app/developers](https://linear.app/developers). The Agents
> surface is newer than the core GraphQL and still moving; the scaffold flags
> each spot with a `VERIFY` comment.

---

## 1. The prerequisite: a personal key can never be an agent

The live adapter sends the personal key as the **raw** `Authorization` header
(`_linear_gql`: `Authorization: ${LINEAR_API_KEY}`, no `Bearer`). A personal key
*is a human user*. It cannot be the actor behind an AgentSession, cannot be
@mentioned, and cannot post agent activities — those actions must be attributed
to an **app user**.

Becoming an app user is an OAuth flow, not a key you paste:

1. **Create an OAuth application** in Linear (workspace settings → API →
   OAuth applications). You get a `client_id` + `client_secret` and set a
   redirect URI.
2. **Authorize with `actor=app`** — the switch that attributes actions to the
   *app itself* (the agent) instead of the human who consents:

   ```
   GET https://linear.app/oauth/authorize
        ?response_type=code
        &client_id=<client_id>
        &redirect_uri=<redirect_uri>
        &scope=read,write,app:assignable,app:mentionable
        &actor=app
   ```

   `app:assignable` lets issues be assigned to the agent; `app:mentionable`
   lets it be @mentioned. Both are what make the agent show up as an assignable
   user on the board.
3. **Exchange the code for a token:**

   ```
   POST https://api.linear.app/oauth/token
        client_id=…  client_secret=…  redirect_uri=…
        code=<code>  grant_type=authorization_code
   ```

   The `access_token` that comes back is sent as **`Authorization: Bearer
   <token>`** — the single line that differs from the personal-key transport,
   which is why the scaffold ships its own `_lna_gql` instead of reusing
   `_linear_gql` (see **Seam 1**).

### Why this stays a scaffold in converge's trust model

- **The referee holds no creds.** `LINEAR_API_KEY` lives in the loop's env and
  is never written to `.cvg/` or bridged by `bin/cvg`. An agent needs *more*
  secrets — the OAuth `access_token`, the `client_secret` (for refresh), and the
  **webhook signing secret** — none of which fit that rule. They belong to a
  long-running receiver, not the referee.
- **An agent needs an inbound endpoint.** register/loop are one-shot commands.
  The Agents API is a two-way conversation: Linear POSTs an AgentSessionEvent to
  *you*, and you answer with activities. That needs a signed, always-on HTTP
  receiver — the "Manager" service sketched in
  [`adapter-contract.md`](./adapter-contract.md), or a serverless function — not
  a CLI. **This is the real missing runtime.**

So the emitters (activities, webhook-ensure, HMAC verify) are written as
real, credential-gated bash you can lift as-is; the **receiver** is documented
only. Until both exist, the four locks in the scaffold header keep it dark:
`.scaffold` extension · not in the source-guard · not in `_ln_main` · mode 644.

---

## 2. The seam: where it plugs into code that already exists

The projection was built so the agent path is *mostly already there*. Four
seams; three are one-liners against existing functions, one is the new service.

### Seam 1 — Transport (`_lna_gql`, in the scaffold)

A separate GraphQL transport that sends `Authorization: Bearer
${LINEAR_AGENT_TOKEN}`. Byte-for-byte identical to `_linear_gql` otherwise
(same `${2:-}`/`{}` quoting trap, same `errors[]` check). New secret env, all
receiver-runtime only, **never** `.cvg/` or `bin/cvg`:

| env | purpose |
|-----|---------|
| `LINEAR_AGENT_TOKEN` | OAuth `actor=app` access token (Bearer) |
| `LINEAR_AGENT_CLIENT_ID` | OAuth client id (token refresh only) |
| `LINEAR_WEBHOOK_SECRET` | webhook signing secret (inbound HMAC verify) |
| `LINEAR_AGENT_API_URL` | optional override of the GraphQL endpoint |

### Seam 2 — Source-guard (`adapters/linear.sh`)

linear.sh sources its companions behind an existence guard, after the core
helpers and before `_ln_main`. Promotion = drop the `.scaffold` extension and
add one guarded line to that block (and nowhere else), reusing the **same dir
variable that block already uses** for `linear-native`/`-projection`/`-structure`
(`$_ln_dir` here is illustrative — match linear.sh's actual name; the variable is
not part of the frozen function-name contract):

```sh
[ -f "$_ln_dir/linear-agents.sh" ] && . "$_ln_dir/linear-agents.sh"
```

Until the file is renamed, that guard never matches — the scaffold is inert.

### Seam 3 — Assignment is *already* the trigger (no code change)

This is the payoff. `register.sh` already emits `--assignee agent:<role>`;
`linear.sh` resolves it through `_ln_identity_lookup` → `_ln_resolve_user`
(which passes a UUID straight through). So a single `.cvg/identity` line —

```
agent:claude=<app-user-uuid>        # from the `agent-whoami` verb / _lna_app_user_id
```

— makes `cvg register` assign the issue to the **agent app user** with **zero
new code**, and Linear opens an AgentSession on that assignment. The assignment
*is* the "go run the loop" signal. The only things still missing are the app
user existing (Seam 0, the OAuth app) and something receiving the session
(Seam 4). The T1 assignee path was designed to be agent-ready on purpose.

### Seam 4 — Loop write path (`ln_write_result`, Pass 8)

Today `ln_write_result` posts a pass/fail `commentCreate` (plus the fail-soft PR
attachment + `:tada:` reaction). When the loop runs *inside* a session, the
receiver hands it `LINEAR_AGENT_SESSION_ID`, and the write path narrates the run
as agent activities instead of (or alongside) the comment:

```sh
# inside ln_write_result, when LINEAR_AGENT_SESSION_ID is set:
_lna_thought  "$sid" "running eval for $issue…"      # progress, non-terminal
_lna_action   "$sid" "eval" "$spec" "$result"        # a discrete step
if [ "$status" = pass ]; then
  _lna_response "$sid" "eval GREEN — done.${pr:+ PR: $pr}"   # TERMINAL
else
  _lna_error    "$sid" "eval RED — parked.${reason:+ $reason}"  # TERMINAL
fi
```

`response` completes the session; `error` fails it. Exactly one terminal
activity per run. Activities are cosmetic-fail-soft (`|| true`) — narration must
never change the pass/fail outcome, same rule as the reaction/attachment.

### Seam 0/5 — The receiver (the genuinely new runtime)

The piece a CLI cannot be. A long-running, signed HTTP endpoint that:

1. **Verifies the HMAC.** Linear signs the raw body with HMAC-SHA256 keyed on
   the webhook secret, in the `Linear-Signature` header (hex);
   `_lna_verify_signature` implements this. Reject deliveries whose
   `webhookTimestamp` is older than ~60s (replay protection). *This inbound seal
   is unrelated to the task-spec sign-off HMAC — different key, different bytes.*
2. **Parses the AgentSessionEvent** (`action: created` / `prompted`), reads the
   session via `_lna_session_get`, and finds the issue it is about.
3. **Maps issue → spec** by reading the issue's marker attachment — reuse
   `_ln_marker_url` / `_ln_find_by_external_id` in reverse: the marker URL
   `https://cvg.local/task-spec/<id>` *is* the bridge from a Linear issue back to
   a spec id. No new mapping table needed.
4. **Spawns the loop** for that spec with `LINEAR_AGENT_SESSION_ID` set, so
   Seam 4 lights up.

Register the receiver's URL once with `_lna_webhook_ensure <url>` (idempotent —
it reuses a webhook already pointing at that URL).

---

## 3. Activity vocabulary (the agent's narration)

`agentActivityCreate` takes a one-of `content` keyed on `type`. The scaffold
wraps each in a helper:

| helper | `type` | terminal? | maps a loop moment to… |
|--------|--------|-----------|------------------------|
| `_lna_thought`  | `thought`  | no  | internal reasoning shown to the user |
| `_lna_action`   | `action`   | no  | a discrete step (`{action, parameter, result}`) |
| `_lna_response` | `response` | **yes → complete** | eval GREEN — the final answer |
| `_lna_error`    | `error`    | **yes → error** | eval RED — the run failed |

(`elicitation`, "ask the user and wait", exists but converge's loop is
non-interactive, so it is omitted.) Linear expects a **first activity fast**
(≈10s) after a session opens or the agent reads as unresponsive — so the
receiver should emit a `thought` acknowledgement before it does anything slow.

---

## 4. Promotion checklist

1. Stand up the receiver service (Seam 0/5) with the four secrets in *its* env.
2. Create the OAuth app, walk the `actor=app` consent, capture the token.
3. `_lna_app_user_id` → put `agent:<role>=<uuid>` in `.cvg/identity` (Seam 3).
4. `_lna_webhook_ensure <receiver-url>` once; stash the returned secret.
5. `git mv linear-agents.sh.scaffold linear-agents.sh`, `chmod` to match the
   other companions, and delete each stub's `_lna_unwired … || return $?` guard.
6. Add the source line (Seam 2) and the six `agent-*` verbs to `_ln_main`.
7. Wire the Seam-4 branch into `ln_write_result`.
8. Only now: advertise the agent verbs in `bin/cvg` agent-context and bump the
   version. Until step 8, T4 stays invisible — exactly as it ships today.
