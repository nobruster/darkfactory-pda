---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-JUIZO
name: Juízo lane
owner: juizo
seam_id: SEAM-JUIZO
source_seam_sha256: 0df54dbe8631c62e2807d8128ef4b3bbf847dacbb127a6a795f15f620aeaab9f
legs:
- LEG-JUIZO-ACUSA-CENTAVO
---
# Juízo lane

This is the single owning swimlane for `SEAM-JUIZO`. Ownership is `juizo`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
