FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-GOLD.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `a77f2d52d54b85c8baf379e12a1c3588b219d631c7afa4befb6885caab3a3d07`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-GOLD
name: Gold lane
owner: medalhao
seam_id: SEAM-GOLD
source_seam_sha256: a13745618e85463a44b7b99635d4b4c3be45f67651bdfc2a329a1507a97b2998
legs:
- LEG-GOLD-RECONCILIA
---
# Gold lane

This is the single owning swimlane for `SEAM-GOLD`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
