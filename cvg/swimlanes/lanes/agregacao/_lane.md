FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-AGREGACAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `0aa0d00cde3a8c68629fb644817d984a7111897c461e8ef6eacf4adeb4007996`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-AGREGACAO
name: Agregação lane
owner: agregacao
seam_id: SEAM-AGREGACAO
source_seam_sha256: e1d2085c6a796c122dce56dcfc7500649e108918cbb871bf68ad8382978fe363
legs:
- LEG-AGREGADO-EXATO
---
# Agregação lane

This is the single owning swimlane for `SEAM-AGREGACAO`. Ownership is `agregacao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
