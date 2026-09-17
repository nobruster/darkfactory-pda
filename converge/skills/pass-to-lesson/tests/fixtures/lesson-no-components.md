# Lesson — Pass 2 (Structure): CI pipeline grounding (no-components fixture)

> Negative fixture: the walkthrough is prose only — zero '### <component>'
> blocks. Everything else is valid, so the gate must FAIL on the walkthrough.

## TL;DR

The release pipeline's assumptions now meet the real CI config: three immutable
terrain facts a later pass must build on.

## Why this pass exists

Pass 2 lowers altitude from *what to ship* to *what is true about the pipeline
we ship through*. Its never-blur rule: record a fact about the terrain, never a
build instruction. Pass 3 consumes these facts to plan the deploy lanes.

## The artifact, component by component

Both ADRs were walked through in the session: the runner exposes no Docker
socket, so builds run rootless — without that fact, Pass 3 plans a
`docker build` that breaks downstream at deploy time; and auth is OIDC-only,
so a plan that reads a static secret breaks downstream silently.

## Decisions and roads not taken

| Decision | Rejected alternative | Why it lost |
|----------|---------------------|-------------|
| Rootless image builds | Bind-mount the Docker socket | No socket exists on the shared runner |
| OIDC-only auth | Static cloud access keys | The org revoked all long-lived keys |

## Vocabulary

- **OIDC:** short-lived federated identity tokens minted per job.
- **runner:** the machine that executes CI jobs.

## What to watch

- The runner image is pinned; re-verify if the CI provider bumps it.

## Check yourself

1. Why can't a deploy job bind-mount the Docker socket? (→ see the walkthrough)
2. What does every deploy job assume about credentials? (→ see the walkthrough)
3. What breaks if Pass 3 plans a static-key deploy? (→ see the walkthrough)
