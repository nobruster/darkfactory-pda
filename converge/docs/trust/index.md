# Trust and operational boundaries

Converge is a credential-free referee. It does not hold model API keys. It
sequences engines, binds a path fence, and records receipts. It assumes the
executor may be hostile inside the write scope it was given.

| Mechanism | Proves | Does not prove |
|---|---|---|
| External `taskspec` / `seamwise` binaries | Converge is not a second copy of those engines | That the binaries on `PATH` are the ones you meant — set `CVG_*_BIN` |
| Seamwise capabilities check | The decomposer claims no materialize or dispatch authority | That the human review was wise |
| `taskspec gate --stamp` | A repository-key holder sealed one Task-Spec revision | Human identity, key secrecy from the worker, or isolation |
| Composition receipt | Engine versions, source commit, digests; `dispatch_authorized: false` | That any leaf was authorized or accepted |
| Bind / path policy | Declared paths were checked at settlement | That every engine *prevented* an out-of-scope write (many adapters only detect) |
| Sealed evals (tier 1) | The Exit Check exited 0 on this host | That the eval was not gamed, or that holdouts stayed unseen |
| Tier-2 `--verify` | A different-family judge produced `UPHELD` or `REFUTED` | That the worker never read `## Holdout` — the brief still points at the spec |
| `ACCEPTED=1` | Task-Spec accepted the exact handoff and revision | Production health or semantic perfection |
| Cockpit snapshot | A read-only projection of workspace state | Authority to approve, stamp, or settle |

## Honest limits

- **Holdout.** Documentation and `verify-work.py` treat `## Holdout` as
  judge-only. The loop still tells the worker the Task-Spec is its instruction
  source. Treat hidden holdouts as a goal, not a shipped invariant.
- **Signing key.** The HMAC key lives in git-private
  `.git/info/taskspec-signing-key`. A worker with repository file access can
  read it unless the harness confinement actually prevents that.
- **Default settle.** NORMAL/FAST can land `TASK_LOOP=LOCAL_SETTLED` on sealed
  evals without `--verify`. The v0.2.0 live-Codex evidence did exactly that.
- **Path control.** Codex can prevent some writes at the OS layer. Claude and
  Kimi path control is often postflight detect. Bind records the class; it
  does not upgrade detect to prevent.
- **Cockpit.** Observation only. If it could stamp a task, it would be a
  second authority.

Accepting risk is allowed. Hiding it is not. Use `--accept-unverified` or an
audited `--no-verify` when you mean it.

Read [authority](../concepts/authority.md) before granting unattended loops.
For Task-Spec's own threat model, use the Task-Spec engine docs.
