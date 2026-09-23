FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-GOLD.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `9919257df3eed15126e2fb61de517a6fd64854500e75cfa06d6f2517720589c6`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-GOLD
name: Gold lane
owner: medalhao
seam_id: SEAM-GOLD
source_seam_sha256: bbe01e22d328e3359e7983c1457cb730d614b12301ab8bff2e7f0e607c03c679
legs:
- LEG-GOLD-RECONCILIA
---
# Gold lane

This is the single owning swimlane for `SEAM-GOLD`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
