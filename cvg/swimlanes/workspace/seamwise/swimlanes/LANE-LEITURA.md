---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-LEITURA
name: Leitura lane
owner: leitura
seam_id: SEAM-LEITURA
source_seam_sha256: 592bb673ef0c6ea002ce83ba66405e9fbacb5bda3e8f28c626a1deb70fd1481a
legs:
- LEG-LEITURA-POSICIONAL
---
# Leitura lane

This is the single owning swimlane for `SEAM-LEITURA`. Ownership is `leitura`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
