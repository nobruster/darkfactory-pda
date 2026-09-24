FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-ONTOLOGIA-POSTGRES.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `175f367812c12e9ae84f82294607b67ddb4e7d12dc3006136a6a8e5716bd1a86`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-ONTOLOGIA-POSTGRES
name: Ontologia no Postgres lane
owner: medalhao
seam_id: SEAM-ONTOLOGIA-POSTGRES
source_seam_sha256: d6839f94a0081dc129a2ce9543bb8f9967029d0e1379570eb1b8843c1a03ca46
legs:
- LEG-ONTOLOGIA-POSTGRES
---
# Ontologia no Postgres lane

This is the single owning swimlane for `SEAM-ONTOLOGIA-POSTGRES`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
