# Topology and permissions

## Static topology selection

| Mode | Use when | Capability shape |
|---|---|---|
| `single` | One context and write surface are coherent | one task-scoped writer |
| `single-explorer` | Broad read-only discovery would pollute implementation context | read-only explorer + task-scoped writer |
| `implementer-verifier` | Risk or policy requires independent verification | task-scoped writer + read-only verifier |
| `parallel` | Two or more write partitions are provably disjoint | multiple scoped writers + read-only verifier |

Runtime evidence such as repeated eval failures, unexpected dependencies, or
context pressure cannot justify the initial Pass 7 decision because it has not
happened yet. The profile records those as permitted Pass 8 escalation signals.

## Capability classes

Capabilities are assembled per task, not installed as permanent personas:

- `discover` — read-only repository and documentation exploration.
- `diagnose` — read-only inspection with command execution.
- `implement` — writes constrained by the Task-Spec.
- `verify` — independent read-only evaluation.
- `integrate` — merge or reconcile already authorized task-local outputs.
- `document` — scoped documentation writes.

## Parallel ownership

Use repeated worker declarations:

```bash
--worker api:scoped-write:src/api/** \
--worker tests:scoped-write:tests/api/**
```

The gate rejects:

- fewer than two scoped writers in `parallel` mode;
- overlapping ownership;
- ownership outside `touches_paths` and `creates_paths`;
- any writable ownership for a `read-only` worker.

## Enforcement

The Task-Spec remains the source for allowed and forbidden paths.

1. Vendor-native hooks or sandboxes should call the candidate-path guard before
   a write.
2. The portable diff guard must run before settlement.
3. A green eval never overrides an out-of-scope diff.

