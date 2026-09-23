FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-GOLD.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `728419b52950d0fd1f49d9e4169fabfd7c228c950feecdd455980fbe010b9007`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-GOLD
name: Gold lane
owner: medalhao
seam_id: SEAM-GOLD
source_seam_sha256: ae2a3b3b818e01d393c9dbd9b005bbdb93f766bfa31988609bddda7f7b6d6bdd
legs:
- LEG-GOLD-RECONCILIA
---
# Gold lane

This is the single owning swimlane for `SEAM-GOLD`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
