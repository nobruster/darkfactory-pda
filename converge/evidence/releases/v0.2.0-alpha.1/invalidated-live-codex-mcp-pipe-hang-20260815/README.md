# Invalidated live Codex run

This evidence set is retained for auditability but is **not release evidence**.

The exact Task-Spec and Seamwise candidate provenance was verified, and Codex
created the expected in-scope implementation. The run did not settle because
Codex-launched MCP child processes inherited the engine adapter's stdout pipe
and kept it open after `codex exec` exited. The loop therefore could not observe
EOF or evaluate the completed work.

The run was terminated, its ephemeral workspace was moved to the macOS Trash,
and the adapter was changed to capture Codex output through a regular file. A
fresh canonical `live-codex/` run is required after that regression is tested.
