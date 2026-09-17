#!/usr/bin/env bash
# Fake `claude -p` that answers with a properly tagged description: proves the
# happy path still works after the fail-closed change.
cat > /dev/null
echo '<new_description>Use this fixture skill to prove the tag path stays green.</new_description>'
