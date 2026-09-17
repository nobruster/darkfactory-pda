# Tests

Hermetic suites. Every one is offline, creates its own workspace under a
temporary directory, and ends in a machine-readable token (`LAYOUT=PASS`,
`CLEAN_ROOM_E2E=PASS`, …) so a caller can branch on the result without parsing
prose.

Run them through the Makefile, not directly — `make check` resolves the pinned
engines these suites assume:

```bash
make check          # core + json + docs + composed + package
make check-core     # the gate, install, loop, and skill suites
```

A green run needs the release pairing documented in the root README: Task-Spec
3.8.0, Seamwise 0.2.0, and a Python with `jsonschema`.

Two suites police the others. `test-ci-covers-every-suite.sh` fails if a suite
exists but `.github/workflows/ci.yml` never invokes it — coverage on the tin is
not coverage in the pipeline. `test-repo-layout.sh` fails if the top-level tree
drifts from the contract the README documents.

`fixtures/` holds inputs shared across suites; it contains no suites itself.
