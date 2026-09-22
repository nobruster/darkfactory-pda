---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-ORQUESTRACAO
name: Orquestração lane
owner: orquestracao
seam_id: SEAM-ORQUESTRACAO
source_seam_sha256: 00f982524034c26ed6c4481689e926a715a859b6734c83bb693ae7bdf390e6a1
legs:
- LEG-DESFECHO-COM-PACOTE
---
# Orquestração lane

This is the single owning swimlane for `SEAM-ORQUESTRACAO`. Ownership is `orquestracao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
