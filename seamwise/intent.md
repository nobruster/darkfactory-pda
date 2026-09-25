---
schema_version: 1
kind: delivery-intent
id: DI-PDA-CORRIGE-PRODUTOR
title: Os defeitos latentes do produtor, corrigidos
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- O produtor corrigido sobre o CSV real de 2026-01 dá os controles da âncora.
- Landing no MinIO intocado pelos testes.
- PROCEDENCIA=OK e suíte inteira verde.
out_of_scope:
- 'Regravar o landing de 2026-01 (ele não muda: 0 inválidas, 2 casas, nenhum negativo).'
- Alterar o juiz Python selado.
- Trava de exclusão entre escritores concorrentes.
---
# Os defeitos latentes do produtor, corrigidos

## Delivery outcome

A gramática do juiz nos três módulos Spark, ANSI declarado, partição carregada recusada, rejeitos com o texto bruto, espécie fora do padrão e valor fora da precisão recusados.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
