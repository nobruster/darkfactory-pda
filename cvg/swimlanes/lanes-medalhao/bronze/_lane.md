FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-BRONZE.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `b1e4d68d362e1e8b1fc758b5d76bfb0f4579aa14e1387dca913cbf2542b03842`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-BRONZE
name: Bronze lane
owner: medalhao
seam_id: SEAM-BRONZE
source_seam_sha256: cafd6348439d37f0447861eca772149f4221dcc179c84df891706266a7eb0cec
legs:
- LEG-BRONZE-REPRODUZ-ANCORA
---
# Bronze lane

This is the single owning swimlane for `SEAM-BRONZE`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
