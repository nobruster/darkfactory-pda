FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-CONTRATO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `834179824670b793d1b94abd8d741dff7acedd7a7c6b69ee25047389d0eabafa`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-CONTRATO
name: Contrato lane
owner: contrato
seam_id: SEAM-CONTRATO
source_seam_sha256: 172592dfebd03e99a3520522778d804e90e578d09e7f2d9c7299a016421273bd
legs:
- LEG-CONTRATO-RECUSA-SEM-ANCORA
---
# Contrato lane

This is the single owning swimlane for `SEAM-CONTRATO`. Ownership is `contrato`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
