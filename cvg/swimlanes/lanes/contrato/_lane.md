FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-CONTRATO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `7a22d9d2cebd594ec2dba1c6ef4db73394af7a4351429e22d9d9a9fb4a79ab91`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-CONTRATO
name: Contrato lane
owner: contrato
seam_id: SEAM-CONTRATO-ANCORA
source_seam_sha256: 1ff3fe3f337f93425b2d5d7433e5becc05292cf0ae36e582b70f6252285ddde7
legs:
- LEG-CONTRATO-RECUSA-SEM-ANCORA
---
# Contrato lane

This is the single owning swimlane for `SEAM-CONTRATO-ANCORA`. Ownership is `contrato`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
