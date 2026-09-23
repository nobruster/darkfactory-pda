---
schema_version: 1
kind: delivery-intent
id: DI-PDA-BENEFICIOS
title: Conferir uma competência do PDA contra âncora medida antes de publicar
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- Sem âncora medida o veredito não autoriza publicar.
- Os cinco controles são comparados individualmente.
- Ponto flutuante em campo monetário é recusado na entrada.
- Uma linha removida ou um centavo alterado é recusado.
- Agrupar por descrição truncada é recusado.
out_of_scope:
- Corrigir defeitos da fonte — a fábrica classifica, nunca corrige.
- Substituir o carregamento atual, que segue rodando em paralelo.
- O ETL a jusante que consome o resultado.
- O carregamento ao lago em Spark e MinIO. Não é incógnita - o ADR 0006 decidiu que o juízo e o produtor
  são entregáveis separáveis, e que a infra ausente não impede construir nem provar o juízo. Entra como
  plano próprio, contra o envelope que a SEAM-FRONTEIRA já contrata. O ADR 0006 supersedes a linha de
  escopo do 0005, que prendia a infra a este mesmo plano.
- Comparar competências VIZINHAS. O ADR 0001 nomeia a lacuna — nenhum gate aqui vê um salto na média entre
  meses, e a fábrica acusa um centavo errado DENTRO de uma competência sem enxergar isso. O darkfactory-inss
  mediu seis competências e achou dois fenômenos reais na média, além de um máximo de 2026-01 três vezes
  maior que o de fevereiro e março. Fica declarado como limite conhecido, não resolvido em silêncio —
  e faixa medida numa competência não vira regra para outra.
---
# Conferir uma competência do PDA contra âncora medida antes de publicar

## Delivery outcome

Ler o CSV da competência por posição, agregar o valor líquido com aritmética exata, comparar contra os cinco controles da âncora medida na origem, classificar toda diferença e deixar um pacote de evidência — recusando publicar quando não houver prova.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
