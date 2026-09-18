---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-LEITURA
name: Leitura lane
owner: leitura
seam_id: SEAM-LEITURA
source_seam_sha256: 35fc90700abd4f23b193f6c146579dc7d35c0a503edc77e5d7eac87040add772
legs:
- LEG-LEITURA-NAO-ALTERA-FONTE
---
# Leitura lane

This is the single owning swimlane for `SEAM-LEITURA`. Ownership is `leitura`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
