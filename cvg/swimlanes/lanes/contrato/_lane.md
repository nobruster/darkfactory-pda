FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-CONTRATO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `c0e58f2dec22aa50f74fe3084c31728f869fae439a9944133dbef807d4b9dd5e`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-CONTRATO
name: Contrato lane
owner: contrato
seam_id: SEAM-CONTRATO-ANCORA
source_seam_sha256: 4daea285d89dc2539661e1279d747c216a34bdab45c61b75fa698179656c3b45
legs:
- LEG-CONTRATO-RECUSA-SEM-ANCORA
---
# Contrato lane

This is the single owning swimlane for `SEAM-CONTRATO-ANCORA`. Ownership is `contrato`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
