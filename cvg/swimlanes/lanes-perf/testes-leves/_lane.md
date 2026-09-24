FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-TESTES-LEVES.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `3949c0e2d9a5c53f72db7cfab628033d006def120b17b4831b419621ec052108`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-TESTES-LEVES
name: Testes mais leves — o cenário montado uma vez lane
owner: medalhao
seam_id: SEAM-TESTES-LEVES
source_seam_sha256: cca54e9a3f80b29246f12fee1ab79882004445eb595a3c77ee008aa93db0f2e2
legs:
- LEG-TESTES-LEVES
---
# Testes mais leves — o cenário montado uma vez lane

This is the single owning swimlane for `SEAM-TESTES-LEVES`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
