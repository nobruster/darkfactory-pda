# Lesson — Pass 2 (Structure): CI pipeline grounding (DevOps fixture)

> Non-data-domain fixture for check-lesson.sh (rule 9 universality).
> modes: adept, review, map, teachback

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
| Rootless image builds | Bind-mount the Docker socket | No socket exists on the shared runner |
| OIDC-only auth | Static cloud access keys | The org revoked all long-lived keys |

## Vocabulary

- **OIDC:** short-lived federated identity tokens minted per job.
- **runner:** the machine that executes CI jobs.

## What to watch

- The runner image is pinned; re-verify if the CI provider bumps it.

## Check yourself

1. Why can't a deploy job bind-mount the Docker socket? (→ see "0001-runner-has-no-docker-socket")
2. What does every deploy job assume about credentials? (→ see "0002-secrets-are-oidc-only")
3. What breaks if Pass 3 plans a static-key deploy? (→ see "0002-secrets-are-oidc-only")

---

## ADEPT explanations

### 0002-secrets-are-oidc-only

- **Analogy:** like a day-pass badge minted at the door instead of a permanent key that could be copied.
- **Diagram:** `job --request--> id-provider --short-token--> cloud`
- **Example:** the deploy job exchanges its CI identity for a 15-minute token, then calls the cloud API.
- **Plain-English:** the pipeline proves who it is per run instead of holding a stored password.
- **Technical:** OIDC federation issues a per-job JWT the cloud trusts via a configured identity pool; no static credential exists.

## Review schedule

Q: What builder must image jobs use on the shared runner?
A: A rootless builder — there is no Docker socket.
Q: How does a deploy job authenticate to the cloud?
A: An OIDC-minted short-lived token, not a static key.
Q: What is the terrain fact behind the deploy auth model?
A: The org revoked all long-lived keys; auth is OIDC-only.

Schedule:
- day 1 — re-test cards 1–3
- day 3 — re-test any missed on day 1
- day 7 — full deck
- day 21 — full deck

## Concept map

Nodes (shuffled): cloud-api · ci-job · id-provider · short-token
Assemble the flow, then check:

<!-- answer -->
- ci-job --> id-provider
- id-provider --> short-token
- short-token --> cloud-api
