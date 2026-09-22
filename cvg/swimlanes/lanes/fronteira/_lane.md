FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-FRONTEIRA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `fa27d9b93f319d90b41a47904b4d10443df5faa9ea95ec452ef1c48657bc492f`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-FRONTEIRA
name: Fronteira lane
owner: fronteira
seam_id: SEAM-FRONTEIRA
source_seam_sha256: f1af5c2b485f8224a71049db3bb3fdc99b4e255ab59ab855c116aa8977a2d3e1
legs:
- LEG-ENVELOPE-VINCULADO
---
# Fronteira lane

This is the single owning swimlane for `SEAM-FRONTEIRA`. Ownership is `fronteira`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
