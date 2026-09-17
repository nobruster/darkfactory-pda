# Vendor adapters

The profile and portable guards are the contract. Vendor adapters translate
that contract into runtime-specific controls; they never redefine it.

| Runtime | Native control | Portable fallback |
|---|---|---|
| Claude Code | emitted `PreToolUse` settings fragment can call `guard-tool-input.py` for Edit/Write/NotebookEdit; dispatcher installation required | whole-repo diff guard before settlement |
| Codex | workspace sandbox bounds writable roots, but not Task-Spec subpaths | whole-repo diff guard before settlement |
| Kimi | permission mode or hook when available | diff guard before settlement |
| Any/simpler agent | surrounding runner passes candidate paths when possible | diff guard before settlement |

Each generated adapter manifest records:

- the execution-profile path;
- candidate-path and postflight commands;
- whether pre-tool prevention is already wired (capability alone is not evidence);
- the native mechanism expected from the runtime;
- the portable fail-closed fallback.

Adapter manifests are evidence and integration inputs. They do not claim a
vendor configuration was installed. The Claude manifest includes the exact
settings fragment, but records prevention as `integration-required`; its hook
emits Claude Code's structured `hookSpecificOutput.permissionDecision=deny`
response when invoked. A dispatcher owns installation and must not upgrade the
profile from `detect` to `prevent` without runtime evidence. The mandatory
postflight remains the cross-runtime settlement boundary.
