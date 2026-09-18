FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-AGREGACAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `aa4dcb7ea3628a06c7e91a4fc300f07fedbecf896b566a68c26a5a7284599282`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-AGREGACAO
name: Agregação lane
owner: agregacao
seam_id: SEAM-AGREGACAO
source_seam_sha256: c137eb3fadc449712d848a11e2d210c0e9d22db5bc9a6749629cf20ff725efda
legs:
- LEG-AGREGADO-EXATO
---
# Agregação lane

This is the single owning swimlane for `SEAM-AGREGACAO`. Ownership is `agregacao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
