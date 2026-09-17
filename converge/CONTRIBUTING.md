# Contributing

## Get to a green build

```bash
make bootstrap
make check
```

`bootstrap` assembles the pinned release pairing under `.engines/` and `.venv/`
— both gitignored — and the Makefile finds them automatically. Nothing else needs
exporting.

The pairing is not optional. Converge coordinates two independently released
engines and pins them to exact commits:

| Engine | Version | Commit |
|---|---|---|
| Task-Spec | 3.8.0 | `0e6180cfc3009bd4ef9cf7ab050b463e10d4af91` |
| Seamwise | 0.2.0 | `5a398169c3fefcb65eb1a47c0cb4f967dfdc0515` |

Task-Spec 3.9.x is **rejected on purpose**: its `rebuild-state` writes an
absolute `path:` into `cvg/tasks/_state.yaml`, which is committed and must stay
byte-reproducible across machines. `bin/cvg` fails closed rather than let a
developer's home directory leak into tracked state.

The engine repositories are private. Without access, `make bootstrap` cannot
fetch them and the suites that need a live engine will not run.

## The shape of the tree

| Home | Holds |
|---|---|
| `bin/` `contracts/` `skills/` `templates/` | what ships to npm, per the `files` allowlist in `package.json` |
| `apps/cockpit/` | the observer UI; deliberately not packaged |
| `tests/` `scripts/` `evidence/` | what proves the thing works |
| `docs/` | knowledge base; start at `docs/index.md` |
| `assets/` | the README banner |

Every directory above carries a `README.md` explaining its job. `make check-layout`
fails if a new top-level entry appears without being declared, if a home loses its
README, or if a retired path comes back.

## Before you open a pull request

```bash
make check
```

Five gates run: `check-core`, `check-json`, `check-docs`, `check-composed`,
`check-package`. Each suite ends in a machine-readable token — `LAYOUT=PASS`,
`CLEAN_ROOM_E2E=PASS`, `DOCS=READY` — so failures name themselves.

Two rules the automation enforces, worth knowing before they surprise you:

- **A suite that exists must run in CI.** `tests/test-ci-covers-every-suite.sh`
  fails if you add `tests/test-*.sh` without wiring it into
  `.github/workflows/ci.yml`. Coverage on the tin is not coverage in the pipeline.
- **The CLI surface is `contracts/cli-command-matrix.json`.** Edit that
  matrix and regenerate `docs/reference/cli.md` with
  `python3 scripts/render-cli-reference.py`. `make check-docs` fails on drift.

## Conventions

Commits follow [Conventional Commits](https://www.conventionalcommits.org):
`type(scope): summary`, where type is one of feat, fix, chore, docs, refactor,
test, perf, build, ci, style.

Shell targets bash 3.2 — stock macOS still ships it, and the portability floor is
asserted in CI. No `declare -A`, no `${var^^}`, no `mapfile`.

Large binaries do not belong in the tree. Historical artifacts live as assets on
the release that owns them. `make check-release-assets` resolves the archived
v0.1.0 names against the live release, so a deleted asset fails loudly instead
of rotting into a 404.
