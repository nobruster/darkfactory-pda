#!/usr/bin/env bash
# Fake `claude -p` that answers WITHOUT <new_description> tags: the improver
# must fail closed instead of adopting this raw stdout as the new description.
cat > /dev/null
echo 'Here is my improved description, delivered without any tags whatsoever.'
