FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-JUIZO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `636bc9ec518a4288e5df60983cce7b66f95317f6c0bd4b2128ade693ba5060f7`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-JUIZO
name: Juízo lane
owner: juizo
seam_id: SEAM-JUIZO
source_seam_sha256: e0624b2781e42364994756c81c3dbab8c8e071cb9f06779a94c911fbe98da102
legs:
- LEG-JUIZO-ACUSA
---
# Juízo lane

This is the single owning swimlane for `SEAM-JUIZO`. Ownership is `juizo`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
