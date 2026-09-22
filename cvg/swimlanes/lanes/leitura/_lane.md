FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-LEITURA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `23bdf85ce2d78cd8a90466df5f055ff515f04654fd730b3621aef45b609bfac5`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-LEITURA
name: Leitura lane
owner: leitura
seam_id: SEAM-LEITURA
source_seam_sha256: 567a04e3b5791d31fc62f1e369f489ed31a4537dd54a3e18cc5f4e35f2f2fcb9
legs:
- LEG-LEITURA-POSICIONAL
---
# Leitura lane

This is the single owning swimlane for `SEAM-LEITURA`. Ownership is `leitura`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
