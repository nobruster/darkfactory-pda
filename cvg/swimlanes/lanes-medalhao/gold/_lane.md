FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-GOLD.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `2abce1e497f13986ccdddb805d23b69e0fa82689a115bbd581e971717f18c2a6`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-GOLD
name: Gold lane
owner: medalhao
seam_id: SEAM-GOLD
source_seam_sha256: 5b4e015a3cb55e743f353467d460df2d9b70a3964def3af4a405313ebcf15410
legs:
- LEG-GOLD-RECONCILIA
---
# Gold lane

This is the single owning swimlane for `SEAM-GOLD`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
