FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-FRONTEIRA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `3673e105d0588a930d42c334470695a31cd637fb0feeea43edda9eccaf096330`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-FRONTEIRA
name: Fronteira lane
owner: fronteira
seam_id: SEAM-FRONTEIRA
source_seam_sha256: 4e607967cfb9de1b07664fcc77201e9db1025d11b5bd8027574322953ca355e5
legs:
- LEG-ENVELOPE-VINCULADO
---
# Fronteira lane

This is the single owning swimlane for `SEAM-FRONTEIRA`. Ownership is `fronteira`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
