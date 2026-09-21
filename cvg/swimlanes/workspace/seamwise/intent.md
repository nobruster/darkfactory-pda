---
schema_version: 1
kind: delivery-intent
id: DI-PDA-BENEFICIOS
title: Conferir uma competência do PDA contra âncora medida antes de publicar
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: 94a7379f89cc795d8a355774626fc3984f116272b4184278ed9ab50750998573
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
- O carregamento ao lago em Spark e MinIO. Não é incógnita - o ADR 0005 decidiu que os motores são separados,
  e o juízo precisa existir antes de haver o que julgar. Entra como plano próprio depois deste.
---
# Conferir uma competência do PDA contra âncora medida antes de publicar

## Delivery outcome

Ler o CSV da competência por posição, agregar o valor líquido com aritmética exata, comparar contra os cinco controles da âncora medida na origem, classificar toda diferença e deixar um pacote de evidência — recusando publicar quando não houver prova.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
