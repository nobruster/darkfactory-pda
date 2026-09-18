---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-LEITURA
name: Leitura lane
owner: leitura
seam_id: SEAM-LEITURA
source_seam_sha256: f37398a6a04d1430da4f1c25115e09fc3924d4ea919b0f6fbe0bba63a9c81a2f
legs:
- LEG-LEITURA-NAO-ALTERA-FONTE
---
# Leitura lane

This is the single owning swimlane for `SEAM-LEITURA`. Ownership is `leitura`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
