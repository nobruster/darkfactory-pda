FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-SILVER.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `1386ed28f54b70d5e939244c6fbb0846337c02c0c7560c6560d84ee1d1f3b74c`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-SILVER
name: Silver lane
owner: medalhao
seam_id: SEAM-SILVER
source_seam_sha256: a5636ca91354e032c70b8af37b8fb11d40420b1989006b5ec8ae2b0ee1a6e9b4
legs:
- LEG-SILVER-PRESERVA-DEFEITO
---
# Silver lane

This is the single owning swimlane for `SEAM-SILVER`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
