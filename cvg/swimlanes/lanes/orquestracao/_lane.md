FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-ORQUESTRACAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `ec0e2b0cf81142c4ea2a1c4497bd5a54c8ecb0212aeaa86961b1850819076356`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-ORQUESTRACAO
name: Orquestração lane
owner: orquestracao
seam_id: SEAM-ORQUESTRACAO
source_seam_sha256: 52da5c86fe059445eea2a21aad92340aa77f5ccc68d841d09e3070022c4e357b
legs:
- LEG-DESFECHO-COM-PACOTE
---
# Orquestração lane

This is the single owning swimlane for `SEAM-ORQUESTRACAO`. Ownership is `orquestracao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
