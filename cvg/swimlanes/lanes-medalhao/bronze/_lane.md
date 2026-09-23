FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-BRONZE.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `ab3ae2d482dd8b584005b26ed680c0a8c4f37d1e5828f00c1b69945359feb873`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-BRONZE
name: Bronze lane
owner: medalhao
seam_id: SEAM-BRONZE
source_seam_sha256: cafe7556ea32a1b7e59f01ac0b9e4f27ebad765b0a3e0bc8868e265a46885d85
legs:
- LEG-BRONZE-REPRODUZ-ANCORA
---
# Bronze lane

This is the single owning swimlane for `SEAM-BRONZE`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
