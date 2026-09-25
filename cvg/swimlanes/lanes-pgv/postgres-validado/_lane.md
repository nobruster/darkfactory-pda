FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-POSTGRES-VALIDADO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `eb2afa9a78adee9910ed157577ddbe58b1b31eb614bb090dbf5068626ae140e0`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-POSTGRES-VALIDADO
name: Postgres validado lane
owner: medalhao
seam_id: SEAM-POSTGRES-VALIDADO
source_seam_sha256: 58c6feac378ee17f8686796803af8223d157599092f19c05c3f7b1e413bf9eef
legs:
- LEG-POSTGRES-VALIDADO
---
# Postgres validado lane

This is the single owning swimlane for `SEAM-POSTGRES-VALIDADO`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
