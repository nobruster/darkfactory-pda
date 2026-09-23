FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-BRONZE.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `fd63264f2c8eef2255ae40a117dd8a3b8a2af25f518c1849b6146a7dae8597d8`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-BRONZE
name: Bronze lane
owner: medalhao
seam_id: SEAM-BRONZE
source_seam_sha256: eb4170d5d366072c7592b93eacec62a43ff1103264fdc6b4b87ab04ac6935d46
legs:
- LEG-BRONZE-REPRODUZ-ANCORA
---
# Bronze lane

This is the single owning swimlane for `SEAM-BRONZE`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
