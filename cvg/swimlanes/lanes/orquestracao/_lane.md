FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-ORQUESTRACAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `46125fc69cb057df25cb23e28a032749b2653a3fae19ab1d9fefb3141cd0b96c`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-ORQUESTRACAO
name: Orquestração lane
owner: orquestracao
seam_id: SEAM-ORQUESTRACAO
source_seam_sha256: 00f982524034c26ed6c4481689e926a715a859b6734c83bb693ae7bdf390e6a1
legs:
- LEG-DESFECHO-COM-PACOTE
---
# Orquestração lane

This is the single owning swimlane for `SEAM-ORQUESTRACAO`. Ownership is `orquestracao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
