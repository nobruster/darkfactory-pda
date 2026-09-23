FORK: B (task-driven) — rota única desde a v3.4 — o consenso sempre entrega à decomposição por tarefas; não é uma escolha desta fábrica.

> Projetado de `LANE-LIMPA-PREPARO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `f34548869c832ff01da10e008b700f9fcaad14e5c35f03a54c70b55944efe3ec`

---

---
schema_version: 1
kind: swimlane
claim: derived
id: LANE-LIMPA-PREPARO
name: Limpeza do preparo lane
owner: medalhao
seam_id: SEAM-LIMPA-PREPARO
source_seam_sha256: 0b08c68625b689d0142e01042001eeeef4f9a5f72e41dc47dba57473b39c632b
legs:
- LEG-LIMPA-PREPARO
---
# Limpeza do preparo lane

This is the single owning swimlane for `SEAM-LIMPA-PREPARO`. Ownership is `medalhao`.
Sibling capability legs are ordered only by explicit dependencies or recorded
contention—not by their position in this file.
