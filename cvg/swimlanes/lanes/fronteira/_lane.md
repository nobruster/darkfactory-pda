FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-FRONTEIRA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `a0448b270ca03ebf1b21fc5c87ed11fa892223cde0753fcf73fea1afc11c0365`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-FRONTEIRA
name: Fronteira lane
owner: fronteira
seam_id: SEAM-FRONTEIRA
source_seam_sha256: 38892c04dd2c02af31e68cd3c517aba746423e051bbfabe55402fb2f0788693a
legs:
- LEG-ENVELOPE-VINCULADO
---
# Fronteira lane

This is the single owning swimlane for `SEAM-FRONTEIRA`. Ownership is `fronteira`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
