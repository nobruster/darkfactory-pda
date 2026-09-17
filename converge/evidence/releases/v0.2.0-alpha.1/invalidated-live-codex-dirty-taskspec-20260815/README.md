# Invalidated live Codex run

This evidence set is retained for auditability but is **not release evidence**.

The run reached local settlement and independent acceptance, but the Task-Spec
executable resolved to a concurrent dirty checkout. Its `environment.json`
recorded the intended release candidate rather than proving the executable's
actual source commit. That provenance mismatch invalidates the run for the
v0.2.0-alpha.1 sign-off.

The canonical `live-codex/` evidence directory must be regenerated using the
exact immutable Task-Spec and Seamwise candidates documented in the release
readiness ledger.
