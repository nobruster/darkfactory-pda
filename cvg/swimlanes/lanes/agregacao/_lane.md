FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-AGREGACAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `22dd3349d37586b0dda78e9b6dd7cd856e31d14923a342c74812c5ff1ab84ee7`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-AGREGACAO
name: Agregação lane
owner: agregacao
seam_id: SEAM-AGREGACAO
source_seam_sha256: dfd5a4abbf50b33e7034e72de928ba28629e2871c75c3f77c65141ebf664214f
legs:
- LEG-AGREGADO-EXATO
---
# Agregação lane

This is the single owning swimlane for `SEAM-AGREGACAO`. Ownership is `agregacao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
