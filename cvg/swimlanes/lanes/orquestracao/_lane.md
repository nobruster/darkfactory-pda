FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-ORQUESTRACAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `d5f1400eddaf93413f46e09ad519fdee5fbcdf25b579a962bb4f7cf112650d0f`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-ORQUESTRACAO
name: Orquestração lane
owner: orquestracao
seam_id: SEAM-ORQUESTRACAO
source_seam_sha256: b1699aa7ad1f194e713579286571e755ee53180c44e0409b9c5c124d449f41d7
legs:
- LEG-DESFECHO-COM-PACOTE
---
# Orquestração lane

This is the single owning swimlane for `SEAM-ORQUESTRACAO`. Ownership is `orquestracao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
