FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-TESTES-LEVES.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `9ebf70eca8d0b68b4bb6e4f24d099aee2a368c2406671a4c66cc9fa24382264a`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-TESTES-LEVES
name: Testes mais leves — o cenário montado uma vez lane
owner: medalhao
seam_id: SEAM-TESTES-LEVES
source_seam_sha256: 03433f7cba7711d00e96e0917140634d2b26c2bbcb8f6eca8cc715a5a8d34d54
legs:
- LEG-TESTES-LEVES
---
# Testes mais leves — o cenário montado uma vez lane

This is the single owning swimlane for `SEAM-TESTES-LEVES`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
