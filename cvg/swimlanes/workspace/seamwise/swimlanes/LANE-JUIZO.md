---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-JUIZO
name: Juízo lane
owner: juizo
seam_id: SEAM-JUIZO
source_seam_sha256: c591e98509ba64835843b55ac4e8064bda64a9a3fd8fe5f1fbd0b5907ec5849a
legs:
- LEG-JUIZO-ACUSA-CENTAVO
---
# Juízo lane

This is the single owning swimlane for `SEAM-JUIZO`. Ownership is `juizo`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
