# Getting started

Converge coordinates two independently versioned engines. It does not implement
decomposition or Task-Spec. It calls `seamwise` and `taskspec` as public
binaries, then binds, loops, and settles.

1. [Install the coordinator and resolve the engines](installation.md).
2. [Run one composed leaf through settlement](first-composed-task.md).
3. [Falsify the claims in five minutes](reviewer-route.md).
4. Keep the [quick reference](../quick-reference.md) nearby.

The shortest safe setup, once both engines and `cvg` are on `PATH`:

```bash
export CVG_TASKSPEC_BIN="$(command -v taskspec)"
export CVG_SEAMWISE_BIN="$(command -v seamwise)"
cvg doctor host
cvg compose status
```

`cvg compose status` is always read-only. A missing Seamwise binary is
`COMPOSE=ENGINE_UNAVAILABLE`, not a prompt to invent a plan locally.

There is no `cvg demo` yet. The first success is the composed journey in
[first-composed-task.md](first-composed-task.md), or the hermetic
`tests/test-clean-room-install-e2e.sh` suite if you are developing Converge
itself.
