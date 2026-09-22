---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-JUIZO
name: Juízo lane
owner: juizo
seam_id: SEAM-JUIZO
source_seam_sha256: ece9904fa201a63366f43e9607dfdd0b8202b6d2389657c116ca6cb0067f9074
legs:
- LEG-JUIZO-ACUSA
---
# Juízo lane

This is the single owning swimlane for `SEAM-JUIZO`. Ownership is `juizo`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
