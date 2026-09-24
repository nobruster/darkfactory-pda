FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-TESTES-LEVES.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `a64470cbab94a5ea6b319ecae9bf63bd141aa5979dd33d34f8cfaed8ff17b5f8`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-TESTES-LEVES
name: Testes mais leves — o cenário montado uma vez lane
owner: medalhao
seam_id: SEAM-TESTES-LEVES
source_seam_sha256: fc066a6f247b110a4dbe01d7da2703c31510081255247b6f9aab1943e2f795e3
legs:
- LEG-TESTES-LEVES
---
# Testes mais leves — o cenário montado uma vez lane

This is the single owning swimlane for `SEAM-TESTES-LEVES`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
