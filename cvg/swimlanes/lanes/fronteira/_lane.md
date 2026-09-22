FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-FRONTEIRA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `9bef716992672e8f54dceea77b98cf9ff3c3f9cc3136a6d80f0f369a3b8abdf2`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-FRONTEIRA
name: Fronteira lane
owner: fronteira
seam_id: SEAM-FRONTEIRA
source_seam_sha256: 895f2994f6f10b3578de160f08b43bfbbb8cb0523c95ced8c7ef6e4dc5c1b5ce
legs:
- LEG-ENVELOPE-VINCULADO
---
# Fronteira lane

This is the single owning swimlane for `SEAM-FRONTEIRA`. Ownership is `fronteira`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
