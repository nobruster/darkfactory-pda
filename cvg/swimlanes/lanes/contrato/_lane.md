FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-CONTRATO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `79e7e5710186c2b5737879a2c92dfa067435402b728851a5680f75e12b00dca8`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-CONTRATO
name: Contrato lane
owner: contrato
seam_id: SEAM-CONTRATO
source_seam_sha256: 5e888b5f89b816aa6207bcec5a9d1fbea79457e2ebc7ac58373f31a0689b7185
legs:
- LEG-CONTRATO-RECUSA-SEM-ANCORA
---
# Contrato lane

This is the single owning swimlane for `SEAM-CONTRATO`. Ownership is `contrato`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
