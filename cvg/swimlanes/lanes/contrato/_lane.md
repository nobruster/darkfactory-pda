FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-CONTRATO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `df715158d8f9ccff762e0e5f92f3532cc1920314b54d8a9de3536fe875474753`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-CONTRATO
name: Contrato lane
owner: contrato
seam_id: SEAM-CONTRATO
source_seam_sha256: 86bf44fc7b7f3cfdc2acf9c127c66ee1befb3239b1f541694738b771e13d3ce2
legs:
- LEG-CONTRATO-RECUSA-SEM-ANCORA
---
# Contrato lane

This is the single owning swimlane for `SEAM-CONTRATO`. Ownership is `contrato`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
