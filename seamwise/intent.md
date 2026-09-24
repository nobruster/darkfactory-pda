---
schema_version: 1
kind: delivery-intent
id: DI-PDA-MEMORIA-6G
title: Memória declarada com o valor medido
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- Sessão padrão com heap efetivo de 6 GB.
- Suíte inteira numa JVM só, verde.
- Gate spark-perf compara contra perf/ sem NAO_MEDIDO por memória.
out_of_scope:
- Alterar as baselines de perf/ — foram medidas com 6g e continuam valendo.
---
# Memória declarada com o valor medido

## Delivery outcome

A sessão declara 6g — o valor das baselines — em vez do 1g que antes era herdado e que a performance entregue apenas tornou explícito.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
