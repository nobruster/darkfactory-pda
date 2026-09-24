FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-ONTOLOGIA-POSTGRES.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `b695bc34269f62d74f78480f8993382aa4424f1142342e9bdc6fd7cd8ccaca58`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-ONTOLOGIA-POSTGRES
name: Ontologia no Postgres lane
owner: medalhao
seam_id: SEAM-ONTOLOGIA-POSTGRES
source_seam_sha256: d000271ccc150ae31bdc39c4a8229467b6a8166342f533393847879c96fc2b8e
legs:
- LEG-ONTOLOGIA-POSTGRES
---
# Ontologia no Postgres lane

This is the single owning swimlane for `SEAM-ONTOLOGIA-POSTGRES`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
