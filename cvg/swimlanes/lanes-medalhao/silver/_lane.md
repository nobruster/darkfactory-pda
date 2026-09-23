FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-SILVER.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `09cf50662dda14db4659b451a057e801284583fb33af73485fa97c55f19a979b`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-SILVER
name: Silver lane
owner: medalhao
seam_id: SEAM-SILVER
source_seam_sha256: 7e96feaa4a71b3e2b4f7fd2c36346eda9df18f7d5fd4c9258acf883a421de386
legs:
- LEG-SILVER-PRESERVA-DEFEITO
---
# Silver lane

This is the single owning swimlane for `SEAM-SILVER`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
