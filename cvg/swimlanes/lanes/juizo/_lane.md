FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-JUIZO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `863cda3a7ebc554fafa272676632b6998f5e42debfda6720507da7ff65652e2f`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-JUIZO
name: Juízo lane
owner: juizo
seam_id: SEAM-JUIZO
source_seam_sha256: d6e6643b53be6a4147efc3881981cee88eb78d723e62c65f4e7ca1f30ba77ef7
legs:
- LEG-JUIZO-ACUSA-CENTAVO
---
# Juízo lane

This is the single owning swimlane for `SEAM-JUIZO`. Ownership is `juizo`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
