FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-ORQUESTRACAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `48d474a0436fe1cb51ca78d5f175c502a8eed9d126e10977e1722ec122c14022`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-ORQUESTRACAO
name: Orquestração lane
owner: orquestracao
seam_id: SEAM-ORQUESTRACAO
source_seam_sha256: 3db2401a2e978fb76869d56194a739b4201cd57707a9ece22b756a231f21d065
legs:
- LEG-DESFECHO-SEMPRE-COM-PACOTE
---
# Orquestração lane

This is the single owning swimlane for `SEAM-ORQUESTRACAO`. Ownership is `orquestracao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
