FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-JUIZO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `5f13970df1d4ca956754d3a0b6fd214c2415ecff4fca2524b663bd2a134c097d`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-JUIZO
name: Juízo lane
owner: juizo
seam_id: SEAM-JUIZO
source_seam_sha256: 34b0096968f0bf7b9b48e9e9f90bb76ccf82f7bcf6cf9477c6999292558627dc
legs:
- LEG-JUIZO-ACUSA
---
# Juízo lane

This is the single owning swimlane for `SEAM-JUIZO`. Ownership is `juizo`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
