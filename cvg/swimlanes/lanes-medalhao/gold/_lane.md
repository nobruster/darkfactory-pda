FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-GOLD.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `e955f17951508b2d7f6b8d1bc2fc77bd58cf19918436018237602023edf14332`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-GOLD
name: Gold lane
owner: medalhao
seam_id: SEAM-GOLD
source_seam_sha256: b0718bc47e124f9d28c55ad6adc87226acc7f069ea9f721dbf202e6f979debd8
legs:
- LEG-GOLD-RECONCILIA
---
# Gold lane

This is the single owning swimlane for `SEAM-GOLD`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
