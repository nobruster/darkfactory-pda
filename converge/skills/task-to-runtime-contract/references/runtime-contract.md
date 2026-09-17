# Runtime contract

## Canonical-source rule

The Task-Spec is the authorization contract. The execution profile must not
copy `touches_paths`, `creates_paths`, `Do-Not-Touch`, eval bodies, budgets, or
sign-off fields. It records the Task-Spec path and SHA-256 plus pointers to
those fields.

The only state that belongs directly in the profile is:

- the initial intra-task topology and its justification;
- explicit parallel ownership partitions;
- the evidence slice selected for this run;
- pinned external-document metadata;
- runtime escalation policy;
- references to concrete enforcement artifacts;
- knowledge-candidate and receipt output paths.

## Artifact path

```text
cvg/execution/<task-id>/execution-profile.yaml
```

The file is the JSON subset of YAML 1.2. This keeps the `.yaml` contract while
allowing portable, dependency-free parsing with the language standard library.

## Freshness

The profile records SHA-256 values for:

- the complete Task-Spec;
- every required ADR or context file;
- every approved knowledge input;
- every cached external-document copy.

Any mismatch fails readiness. Regenerate the profile after an authorized source
change; do not patch hashes by hand.

## Authorization

Tier 1 HMAC verification is required by default. `--supervised` permits a Tier
2 structural sign-off only when a human remains in the execution loop. Tier 3
or unsigned tasks always fail.

## External documentation

Every external document entry has:

- a source URL;
- a repository-relative cache path;
- a content SHA-256.

The cache is the execution input. The URL is provenance. This preserves offline
execution, version pinning, and reproducibility.

