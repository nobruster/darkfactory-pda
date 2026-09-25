---
schema_version: 1
kind: delivery-intent
id: DI-PDA-PRATICAS-DELTA
title: Boas práticas Delta em todas as camadas
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- Suíte inteira verde.
- Toda tabela Delta do lago com retenção de 5 anos.
- OPTIMIZE com dado idêntico.
out_of_scope:
- VACUUM (só sob pedido do dono).
- Sessões do produtor (Parquet, não Delta).
---
# Boas práticas Delta em todas as camadas

## Delivery outcome

Evolução aditiva por padrão, sessão declarada, retenção de 5 anos, OPTIMIZE pós-carga.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
