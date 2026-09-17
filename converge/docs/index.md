# Converge documentation

The knowledge base for the coordinator — how Converge sequences two independent
engines without taking their authority. The machine contracts live in
[`../contracts/`](../contracts/). Everything here explains them.

Task-Spec and Seamwise are separate products. Their docs stay in those
repositories. This tree covers only what Converge owns.

## Start here

| File | Purpose |
|---|---|
| [getting-started/index.md](getting-started/index.md) | Orientation and the shortest path in |
| [getting-started/installation.md](getting-started/installation.md) | Install the coordinator and resolve the two engines |
| [getting-started/first-composed-task.md](getting-started/first-composed-task.md) | Prepare through settlement for one leaf |
| [getting-started/reviewer-route.md](getting-started/reviewer-route.md) | Falsify the release claims in five minutes |
| [quick-reference.md](quick-reference.md) | One-page commands and tokens |

## Concepts

| File | Purpose |
|---|---|
| [concepts/authority.md](concepts/authority.md) | Who may decide what — and who may not |
| [concepts/skills.md](concepts/skills.md) | Eleven Converge skills plus standalone Tasking — purpose, when, not, gate |
| [concepts/compose-and-settlement.md](concepts/compose-and-settlement.md) | `COMPOSE=*`, `TASK_LOOP=*`, and `ACCEPTED=1` |

## Guides

| File | Purpose |
|---|---|
| [guides/descent.md](guides/descent.md) | Two phases, one barrier, workspace discovery, lane, cvg next |
| [guides/chat.md](guides/chat.md) | Chat session path: cvg next, pass prompts, harness dests, `.claude-plugin/` |
| [guides/bind-and-loop.md](guides/bind-and-loop.md) | Bind one signed leaf and run the bounded loop |
| [guides/recovery.md](guides/recovery.md) | The one safe next action for each compose state |

## Trust and reference

| File | Purpose |
|---|---|
| [trust/index.md](trust/index.md) | What a receipt proves and what it does not |
| [reference/index.md](reference/index.md) | CLI, contracts, and schemas |
| [reference/cli.md](reference/cli.md) | Generated from `contracts/cli-command-matrix.json` |
| [reference/contracts.md](reference/contracts.md) | Versioned JSON contracts Converge emits |

## How to navigate

1. Start at [getting-started](getting-started/index.md) if you need a first
   success.
2. Read **concepts** for definitional questions ("who authorizes a task?").
3. Read **guides** for how-to questions ("the loop blocked — what now?").
4. Read **trust** before unattended settlement.
5. Read **reference** for exact forms, tokens, and schemas.

For Task-Spec format, evals, and signing, use the Task-Spec engine docs — not
this tree. For decomposition theory, use Seamwise.
