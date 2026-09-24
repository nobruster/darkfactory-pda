---
schema_version: 1
kind: delivery-intent
id: DI-PDA-ONTOLOGIA
title: Ontologia dos benefícios emitidos, com projeções reconferidas
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- Ontologia confere com os bytes do INSS e com o contrato.
- Tabela especie com 65 linhas e os dois textos, na Silver real 2026-01.
- Postgres com a ontologia inteira, reconferida, com o sha256 da versão.
out_of_scope:
- Mudar grupos_especie (o RMV entre os Amparos é decisão separada).
- Classificar as 22 divergências de texto como abreviação ou renomeação.
- Alterar a Silver ou a Gold publicadas.
---
# Ontologia dos benefícios emitidos, com projeções reconferidas

## Delivery outcome

A ontologia versionada liga colunas a termos e espécies a nomes oficiais e grupos; a Delta especie e o Postgres são projeções dela, carregadas e reconferidas pela cadeia.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
