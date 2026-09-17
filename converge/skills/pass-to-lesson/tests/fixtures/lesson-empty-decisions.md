# Lesson — Pass 2 (Structure): CI pipeline grounding (empty-decisions fixture)

> Negative fixture: the Decisions table carries only its header and separator —
> zero decision rows. Everything else is valid, so the gate must FAIL there.

## TL;DR

The release pipeline's assumptions now meet the real CI config: three immutable
terrain facts a later pass must build on.

## Why this pass exists

Pass 2 lowers altitude from *what to ship* to *what is true about the pipeline
we ship through*. Its never-blur rule: record a fact about the terrain, never a
build instruction. Pass 3 consumes these facts to plan the deploy lanes.

## The artifact, component by component

### 0001-runner-has-no-docker-socket

- **What it is:** the fact that the shared CI runner exposes no Docker socket.
- **Why it is shaped this way:** the runner is a locked-down shared tenant.
- **The decision it encodes:** image builds must use a rootless builder, not
  a bind-mounted socket.
- **What breaks downstream without it:** Pass 3 plans a `docker build` that
  fails on the runner at deploy time.

### 0002-secrets-are-oidc-only

- **What it is:** the CI has no static cloud keys; auth is OIDC federation.
- **Why it is shaped this way:** the org revoked long-lived keys.
- **The decision it encodes:** every deploy job assumes a short-lived OIDC token.
- **What breaks downstream without it:** a plan that reads a static secret finds
  none and the deploy silently no-ops.

## Decisions and roads not taken

| Decision | Rejected alternative | Why it lost |
|----------|---------------------|-------------|

## Vocabulary

- **OIDC:** short-lived federated identity tokens minted per job.
- **runner:** the machine that executes CI jobs.

## What to watch

- The runner image is pinned; re-verify if the CI provider bumps it.

## Check yourself

1. Why can't a deploy job bind-mount the Docker socket? (→ see "0001-runner-has-no-docker-socket")
2. What does every deploy job assume about credentials? (→ see "0002-secrets-are-oidc-only")
3. What breaks if Pass 3 plans a static-key deploy? (→ see "0002-secrets-are-oidc-only")
