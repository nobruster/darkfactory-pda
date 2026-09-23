FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-SILVER.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `8d12c5065861bebf33a2546f409722fe98fd56a4a20325f5457806e17b16f399`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-SILVER
name: Silver lane
owner: medalhao
seam_id: SEAM-SILVER
source_seam_sha256: 1610243402f966bfd17310d9a3032fc55279ecaa75cb5f10a599faecf631ec9d
legs:
- LEG-SILVER-PRESERVA-DEFEITO
---
# Silver lane

This is the single owning swimlane for `SEAM-SILVER`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
