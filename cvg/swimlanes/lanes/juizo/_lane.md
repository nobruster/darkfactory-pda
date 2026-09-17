FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-JUIZO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `e30dc1f24c3e458bccde2e4143bc97422f2375f8606f89d8896a91b45dec8d73`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-JUIZO
name: Juízo lane
owner: juizo
seam_id: SEAM-JUIZO
source_seam_sha256: 8eb328041f2e216e1e2a8ccfcfb6deea2cdb8604c867993c314d8d3abf522cb7
legs:
- LEG-JUIZO-ACUSA-CENTAVO
---
# Juízo lane

This is the single owning swimlane for `SEAM-JUIZO`. Ownership is `juizo`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
