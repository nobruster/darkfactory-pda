---
schema_version: 1
kind: delivery-intent
id: DI-PDA-REFERENCIA-MEDALHAO
title: Dicionário e glossário do INSS pelo medalhão
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- Landing com os bytes dos dois .xlsx e prova.
- Bronze com as linhas como vieram.
- Silver glossário e especie lidos da Bronze, com a linhagem das camadas.
- A especie da Bronze igual à v1 em produção, linha a linha.
- Gold com dim_especie e dim_termo lidas da Silver.
out_of_scope:
- Postgres lido da Gold e YAML só com conceitos (receita B).
- Retirar publicar_especie antiga (tarefa de limpeza).
---
# Dicionário e glossário do INSS pelo medalhão

## Delivery outcome

Os arquivos de referência do INSS passam por landing, Bronze e Silver como toda fonte, e a Bronze dos benefícios registra qual partição do landing leu.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
