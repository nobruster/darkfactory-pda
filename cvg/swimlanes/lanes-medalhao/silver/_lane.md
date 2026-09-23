FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-SILVER.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `47d182a5dc25d55b964189b1ce2c11adac4ace03a0bb50057e2fd9b13d817516`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-SILVER
name: Silver lane
owner: medalhao
seam_id: SEAM-SILVER
source_seam_sha256: 93cdacc0d0a902626d00123991ba0a49c7829fc472013c6382a8e651aa2c1346
legs:
- LEG-SILVER-PRESERVA-DEFEITO
---
# Silver lane

This is the single owning swimlane for `SEAM-SILVER`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
