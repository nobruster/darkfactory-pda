<!-- briefspec:checkpoint:v1 mode=orient -->
## Session Checkpoint · Orient

Headline: The contract is implemented; installation verification is next.
Current state: The shared model and three runtime adapters are available.

Completed:
- Added outcome and checkpoint validators.
- Added bounded session state.

Decisions:
- Timers create eligibility; checkpoints appear only at safe boundaries.

Proof:
- [direct/info] `src/briefspec/hooks.py` — safe-boundary processing

Next:
- Run a clean-room user installation.

Open:
- Live Copilot CLI validation requires its executable.
<!-- /briefspec -->
