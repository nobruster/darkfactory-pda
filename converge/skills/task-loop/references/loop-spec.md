# The loop specification — what Pass 8 actually is

> Grounded in a July-2026 scan of the loop-engineering literature and of what
> shipped tooling actually does. Sources are cited inline so the claims can be
> argued with.

## The thing we got wrong first

Until now Converge's "loop" **was not a loop**. It ran the evals once, reported
RED or GREEN, and settled or refused. There was no iteration, no agent was ever
invoked, and every spec declared

```yaml
budget_iterations: 15
max_iterations: 15
circuit_breaker_no_progress: 3
on_terminal_failure: park_with_context
```

which **nothing enforced**. That is the same defect class as WP4's
`external_writes: deny` — a control that exists in the artifact and not in the
runtime. A gate is a fine thing to be; it is just not what the spec promised.

## What a loop is

A **loop specification** is an external, bounded, reusable artifact — *trigger,
goal, verification, stopping rule, memory* — that a human hands to a harness so
the agent pursues a goal on its own.¹ It is distinct from a `while` statement
and from the perceive-act-observe cycle the harness already runs internally.

Converge's version:

| element | Converge |
|---|---|
| **trigger** | `cvg loop --issue <id>` — never self-selected |
| **goal** | the signed Task-Spec's Exit Check |
| **verification** | the eval, then an independent judge |
| **stopping rule** | named terminal states + three budgets + stagnation |
| **memory** | the workspace on disk; receipts; the tracker |

## The verification ladder

The single most useful refinement of "verifiable vs judged" is a five-level
ladder of rigour¹:

| level | what it is | zone |
|---|---|---|
| **1** | deterministic — assertion, exit code, golden output | **autonomous** |
| **2** | rule/constraint over text — linter, schema, policy | **autonomous** |
| 3 | delayed field truth — tests, deploy, customer response | objective |
| 4 | model as judge, scoring by rubric | assisted |
| 5 | human checkpoint | assisted |

**The discipline is honesty: never report level 4 as level 1.** A loop is only
as autonomous as the level its verifier truly sits at.

Converge sits at **level 1–2 for the gate** (the Exit Check is an exit code; the
path guard is a policy over a diff) and uses **level 4 only as a hardened
secondary** — `cvg verify`, which requires a *different model family* and a
holdout the agent never saw. That combination is the recommended shape, and it
is why the eval-sharpening work mattered: an existence-only eval is a level-1
check in form and a level-0 check in substance.

## Named terminal states — error is never success

A well-formed loop names its terminal states, and **an error or an exhausted
budget never counts as success**.¹ Naming them is what stops a loop from calling
"I got tired of iterating" a win.

| state | token | meaning |
|---|---|---|
| settled | `TASK_LOOP=SETTLED` | green eval, external writes permitted, PR opened |
| local settled | `TASK_LOOP=LOCAL_SETTLED` | green eval, policy denies external writes |
| no-op | `TASK_LOOP=NO_OP` | already green on arrival; nothing to do |
| blocked | `TASK_LOOP=BLOCKED` | needs a human or missing upstream input |
| stalled | `TASK_LOOP=STALLED` | stagnation detector fired — no progress |
| exhausted | `TASK_LOOP=EXHAUSTED` | a budget ceiling was reached |
| cancelled | `TASK_LOOP=CANCELLED` | an external stop signal arrived |
| error | `TASK_LOOP=ERROR` | the loop itself could not continue safely |

Only `SETTLED`, `LOCAL_SETTLED` and `NO_OP` exit zero.

## Three budgets, because they fail differently

An agent can burn a dollar budget in four huge-context iterations, run 200 cheap
iterations over six hours, or hang on one tool call overnight. So the ceiling is
**three-axis**: iterations, tokens/cost, wall-clock.

**Check before the call, never after** — post-flight checking means the tokens
are already spent before the limit is known.

**Budget exhaustion is a planned landing, not a crash.** On exhaustion the loop
commits work-in-progress to its branch, writes a handoff note describing state
and next steps, and exits cleanly with `EXHAUSTED`. That is the same exit
machinery as convergence, with a different report.

## Stagnation beats a fixed count

Fixed iteration counts burn effort long after output stops improving; a semantic
stopping rule has been measured cutting tokens ~38% at comparable quality.² A
static analysis of 6,549 agent repositories confirmed 68 likely infinite-loop
defects across 47 projects — in every case the loop reached model calls, tools
or retries with no stopping condition covering the whole feedback path.³

Converge's no-progress rule fires when **the same eval fails the same way twice
in a row**, or the diff stops changing. That is `circuit_breaker_no_progress`,
finally enforced.

## Fresh context per attempt (the Ralph lesson)

Each retry re-reads the entire context window — every prior failed attempt.
Iteration one costs 100 tokens, iteration ten costs thousands. Worse, content
pushed deep into a long context is attended to least.

So **each attempt spawns a new agent process with a fresh context**, and all
state lives on disk — the spec, the diff, git history, the attempt log. Memory
is versioned artifacts, not conversation history.

This is deliberately the *bash-loop* form of Ralph rather than the in-session
plugin form: an in-session stop-hook loop accumulates context rot across
iterations, which is the problem the pattern exists to solve.

## Anti-patterns we are explicitly defending against

| anti-pattern¹ | Converge's structural defense |
|---|---|
| **while-true around a stranger** | every turn ends in a real level-1 check; the agent calls named skills |
| **the self-approving loop** | maker ≠ checker by construction; `cvg verify` demands a different model family |
| **specification gaming** | the eval is HMAC-sealed and outside the agent's write scope; holdout evals; the agent may never silence a failing check |
| **pretending level 4 is level 1** | the receipt records which ladder level actually ran |
| **the unattended runaway** | named terminal states + three budgets + stagnation detector + `external_writes: deny` by default |

The strongest of these is structural: **the agent cannot edit its own eval.**
The Exit Check lives in a signed spec, the signature covers the eval bodies, and
`fs.write` scope never includes the spec. A loop that can silence its own check
is not verified, however green it looks.

## The tracker is the state store, not a notification

When a tracker is configured, the loop is a **full circle**: the issue is where
work is claimed, progress is narrated, and outcomes land. Linear models this
natively⁴ — `AgentSession` tracks one agent run; `AgentActivity` carries
`thought` / `action` / `elicitation` / `response` / `error`; the `stop` signal is
an external kill switch the loop must honour immediately.

Converge's mapping:

| loop phase | tracker effect |
|---|---|
| claim | move the issue to the first `started` state; open an `AgentSession` |
| attempt N | `action` activity — engine, iteration, budget remaining |
| eval RED | `thought` activity — which check failed and why |
| blocked | `error` activity + a blocked-task report |
| green + settle | `response` activity; issue → completed |
| stop signal | halt now, emit `response`, exit `CANCELLED` |

**The tracker never instructs.** The signed spec is the only instruction source;
issue bodies are state. This is what keeps a compromised or merely careless
comment from steering an unattended agent.

Every tracker call is **fail-soft and idempotent** — keyed so a retry cannot
double-apply. No tracker configured means the loop still runs, locally, whole.

---

¹ Macedo, *Stop Hand-Holding Your Coding Agent: Engineering the Loops that
Replace Step-by-Step Prompting*, arXiv:2607.00038 — loop-spec anatomy, the
five-level ladder, named terminal states, and the anti-pattern catalogue.
² arXiv:2606.27009 — semantic stopping rule vs fixed iteration count.
³ arXiv:2607.01641 — 68 infinite-agent-loop defects across 47 of 6,549 repos.
⁴ Linear, *Developing the Agent Interaction* and *Agent Best Practices* —
`AgentSession`, `AgentActivity`, signals, delegate-vs-assignee.

---

## Two fences, not one (added after reviewing loop-engineering)

The capability envelope answers *"may this task write here?"*. That is per-task
and **authored** — so a spec declaring `touches_paths: [auth/]` is not a
violation, it is an instruction, and everything downstream works perfectly to
let an agent edit the auth code.

`.cvg/gate.yaml` answers a different question: *"may ANY task ever write here?"*
It is per-repo and **standing**, it is not part of the signed payload, and
**protected paths beat contract, always** — re-signing a spec cannot buy access
to anything they cover. `max_changed_files` adds a blast-radius cap that is
orthogonal to paths: twelve legal files changed unattended is a different event
from two.

An unparseable gate is a FAILURE, never a skipped control. A fence you can
disable with a typo is not a fence.

## Isolation

`--isolation worktree` gives the run its own checkout. Work is discarded
wholesale on a non-green landing, so a bad run costs exactly zero and nothing an
unattended agent does reaches the tree a human is reading. Landings that leave
something worth inspecting (`SETTLED`, `LOCAL_SETTLED`, `EXHAUSTED`, `STALLED`)
keep theirs, because a handoff note is useless without the work it describes.

**A worktree sees committed state only.** Uncommitted work in the main tree is
invisible to it — correct git semantics, and a sharp edge worth knowing before
you wonder why an isolated run started green.

## Cost: a ceiling, not a prediction

`--estimate` reports what a run *can* spend before its own brakes stop it. It
deliberately does not predict: engines frequently report no usage at all — the
first real codex run finished with `TOKENS_USED=0` — so any estimate would be a
number we invented. When no `budget_tokens` is declared the output says the
token axis is unenforceable on that run rather than implying a limit exists.

Credit: `gate.yaml`, the worktree convention and pre-run cost reporting are
adapted from the loop-engineering project (MIT). Its readiness *score* is
deliberately not adopted — it measures file presence, which is a setup-maturity
signal rather than a correctness one.
