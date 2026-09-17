# Lesson — Pass 2 (Structure): CI pipeline grounding (BROKEN modes fixture)

> Negative fixture: base sections valid, all three emitter modes malformed.
> modes: adept, review, map

## TL;DR

Same content as the good fixture, but the mode sections are deliberately broken
so check-lesson.sh must FAIL for the mode reasons, not the base ones.

## Why this pass exists

Pass 2 lowers altitude from *what to ship* to *what is true about the pipeline*.
Its never-blur rule: record a fact, never a build instruction. Pass 3 consumes
these facts to plan the deploy lanes.

## The artifact, component by component

### 0001-runner-has-no-docker-socket

- **What it is:** the shared CI runner exposes no Docker socket.
- **Why it is shaped this way:** locked-down shared tenant.
- **The decision it encodes:** builds use a rootless builder.
- **What breaks downstream without it:** a `docker build` fails on the runner.

## Decisions and roads not taken

| Decision | Rejected alternative | Why it lost |
|----------|---------------------|-------------|
| Rootless image builds | Bind-mount the Docker socket | No socket on the shared runner |

## Vocabulary

- **runner:** the machine that executes CI jobs.

## What to watch

- The runner image is pinned; re-verify on provider bumps.

## Check yourself

1. Why can't a deploy job bind-mount the Docker socket? (→ see "0001-runner-has-no-docker-socket")
2. What builder must image jobs use? (→ see "0001-runner-has-no-docker-socket")
3. What breaks if a plan assumes a socket? (→ see "0001-runner-has-no-docker-socket")

---

## ADEPT explanations

### 0001-runner-has-no-docker-socket

- **Analogy:** like a kitchen with no gas line — you bring your own burner.
- **Diagram:** `job --> rootless-builder`
- **Example:** the build job runs buildah in rootless mode.
- **Plain-English:** no privileged socket, so builds run unprivileged.
  (this block deliberately omits the fifth label)

## Review schedule

Q: What builder must image jobs use on the shared runner?
A: A rootless builder — there is no Docker socket.
Q: What is the terrain fact here?
A: The shared runner exposes no Docker socket.
(deliberately only 2 cards and no dated schedule)

## Concept map

Nodes (shuffled): job · rootless-builder · image
Assemble the flow, then check:

<!-- answer -->
(deliberately no edge lines here; the arrows are omitted on purpose)
