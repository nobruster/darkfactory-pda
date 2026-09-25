---
schema_version: 1
kind: delivery-intent
id: DI-PDA-POSTGRES-VALIDADO
title: Postgres pelos próprios arquivos, validado contra a Gold
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- Carga real com 2/13/14/5/65 validada contra a Gold de produção.
- Divergência não publica; carga anterior segue visível.
out_of_scope:
- Retirar projetar_ontologia e deixar o YAML só com conceitos (receita C, limpeza).
---
# Postgres pelos próprios arquivos, validado contra a Gold

## Delivery outcome

A projeção do Postgres vira um caminho independente que só publica o que concorda com a Gold.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
