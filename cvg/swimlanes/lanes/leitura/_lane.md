FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-LEITURA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `8e05522479bab670104136da7b29e2c1c9295bf5280d5b87ccd841aff105c667`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-LEITURA
name: Leitura lane
owner: leitura
seam_id: SEAM-LEITURA
source_seam_sha256: 933575b842cf9a432c8b2264add7b98e465b423b498c02afc23bd24164ccff52
legs:
- LEG-LEITURA-POSICIONAL
---
# Leitura lane

This is the single owning swimlane for `SEAM-LEITURA`. Ownership is `leitura`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
