# Lesson — Pass 2 (Structure): CI pipeline grounding (adept-unbalanced fixture)

> Negative fixture: two ADEPT blocks; the first carries all five labels, the
> second drops Technical. The union across the section still shows all five
> labels, so a section-wide count would PASS — the per-block rule must FAIL.
> modes: adept

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

### 0001-runner-has-no-docker-socket

- **Analogy:** like a kitchen with no gas line — you bring your own burner.
- **Diagram:** `job --> rootless-builder --> image`
- **Example:** the build job runs buildah in rootless mode on the shared runner.
- **Plain-English:** no privileged socket, so builds run unprivileged.
- **Technical:** the runner exposes no /var/run/docker.sock; builds use a rootless OCI builder inside the job sandbox.

### 0002-secrets-are-oidc-only

- **Analogy:** like a day-pass badge minted at the door instead of a permanent key that could be copied.
- **Diagram:** `job --request--> id-provider --short-token--> cloud`
- **Example:** the deploy job exchanges its CI identity for a 15-minute token, then calls the cloud API.
- **Plain-English:** the pipeline proves who it is per run instead of holding a stored password.
  (this block deliberately omits the fifth label; the first block still has it)
