FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-AGREGACAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `965b45e676ec9081c117eb34a35b8bf9d3496c6060900dfbb12f72cc85e96bf4`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-AGREGACAO
name: Agregação lane
owner: agregacao
seam_id: SEAM-AGREGACAO
source_seam_sha256: 6f39e5cd7a0a601adc08eee8f2ab4d38058ea72bdb75d74be554d4d95c9bcd50
legs:
- LEG-AGREGADO-EXATO
---
# Agregação lane

This is the single owning swimlane for `SEAM-AGREGACAO`. Ownership is `agregacao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
