FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-AGREGACAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `718f1609c66fb8ed94aae7ba5fdadee9e4b5004d562a799a2f925f6a215c8308`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-AGREGACAO
name: Agregação lane
owner: agregacao
seam_id: SEAM-AGREGACAO
source_seam_sha256: 48bc5d548e4104c8c4eb395e93d8a683fb16b11f3de9f3388024836d09e6c05a
legs:
- LEG-AGREGADO-EXATO
---
# Agregação lane

This is the single owning swimlane for `SEAM-AGREGACAO`. Ownership is `agregacao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
