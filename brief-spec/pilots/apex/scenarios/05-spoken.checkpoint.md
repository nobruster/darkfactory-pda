<!-- briefspec:checkpoint:v1 mode=spoken -->
## Session Checkpoint · Spoken

Headline: The shared contract is ready for installation testing.
Script: Here is the current picture. BriefSpec now translates lifecycle events from Codex, Claude,
and Copilot into one small internal model. It does not call another language model, and it does not
save raw prompts, tool results, or transcripts. Instead, the host agent writes the explanation,
while BriefSpec decides when a checkpoint is useful and checks that the final shape is complete.
Time and interaction volume can make a checkpoint eligible, but the checkpoint waits until a safe
boundary. If a required handoff is malformed, the hook can ask for one correction. The repair guard
then stops the loop. The next step is practical rather than theoretical: install the built package
inside an isolated home directory, send real fixture events through the installed command, and
confirm that uninstall preserves files it does not own.

Screen-only proof:
- [direct/info] `src/briefspec/state.py` — bounded private state implementation
- [direct/info] `src/briefspec/hooks.py` — one-repair guard

Next:
- Run the clean-room installation gate.
<!-- /briefspec -->
