FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-BRONZE.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `6229a03ffcd49292e02a7c0e3b56617ccacf07e7b4b6f1ab521eda03f5da954d`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-BRONZE
name: Bronze lane
owner: medalhao
seam_id: SEAM-BRONZE
source_seam_sha256: 7c2690802325e1272bbe8fdf643d3f6ad9a7b273bf8727f00bcdcbc13d304d59
legs:
- LEG-BRONZE-REPRODUZ-ANCORA
---
# Bronze lane

This is the single owning swimlane for `SEAM-BRONZE`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
