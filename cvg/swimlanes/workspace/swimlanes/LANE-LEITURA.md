---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-LEITURA
name: Leitura lane
owner: leitura
seam_id: SEAM-LEITURA
source_seam_sha256: fe4a3d93819553fd0686d836105214b801b26832ce44a7edf188b17bed90128e
legs:
- LEG-LEITURA-NAO-ALTERA-FONTE
---
# Leitura lane

This is the single owning swimlane for `SEAM-LEITURA`. Ownership is `leitura`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
