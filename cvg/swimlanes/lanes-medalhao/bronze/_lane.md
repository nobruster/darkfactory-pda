FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-BRONZE.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `6293010618737745a3f4cc2e031404ed8fa0a1a3d39f68975f5df3bb74a9afb1`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-BRONZE
name: Bronze lane
owner: medalhao
seam_id: SEAM-BRONZE
source_seam_sha256: 62b14968efdd71ae68d8e112eb043dbcc9fb242cd041b18366377f3c4aeb5dfc
legs:
- LEG-BRONZE-REPRODUZ-ANCORA
---
# Bronze lane

This is the single owning swimlane for `SEAM-BRONZE`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
