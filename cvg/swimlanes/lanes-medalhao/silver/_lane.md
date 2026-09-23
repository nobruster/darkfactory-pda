FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-SILVER.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `c088681d9ffcd6909a8770a66c6c637f1f439e40fb2d8a250fb77d7b16a476e9`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-SILVER
name: Silver lane
owner: medalhao
seam_id: SEAM-SILVER
source_seam_sha256: 4774f4aa3d1dbdfedcfc17fa65e0911bf8fe66532f82246b9d05779d6dd002e3
legs:
- LEG-SILVER-PRESERVA-DEFEITO
---
# Silver lane

This is the single owning swimlane for `SEAM-SILVER`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
