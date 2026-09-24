---
schema_version: 1
kind: delivery-intent
id: DI-PDA-PERFORMANCE
title: Performance e memória do medalhão, medidas
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- Bronze e Silver com PERF=MELHOR e saída idêntica.
- Assuntos com PERF=MELHOR e saída idêntica.
- test_gold_assuntos em menos da metade dos 551s, com os mesmos testes.
- Nenhum preparo de execução conferida sobra.
out_of_scope:
- Fase 2 da Gold (landing com 14 colunas).
- Alterar o juiz ou o orquestrador selados.
---
# Performance e memória do medalhão, medidas

## Delivery outcome

Declarar a memória, liberar o cache, reconferir numa passada, reduzir commits de constraint e aliviar os testes — cada ganho provado pelo gate spark-perf com a saída idêntica.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
