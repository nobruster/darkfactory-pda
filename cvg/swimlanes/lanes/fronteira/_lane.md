FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-FRONTEIRA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `68baea2c57a9ed605d6e8a075e1c1d1c12029587aaba968163ffe8c5c5bb06fb`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-FRONTEIRA
name: Fronteira lane
owner: fronteira
seam_id: SEAM-FRONTEIRA
source_seam_sha256: 29b6d98644c70132abfc8175cca43b153e94f4371746ece97d77a3c6d4d1283a
legs:
- LEG-ENVELOPE-VINCULADO
---
# Fronteira lane

This is the single owning swimlane for `SEAM-FRONTEIRA`. Ownership is `fronteira`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
