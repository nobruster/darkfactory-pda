---
schema_version: 1
kind: delivery-intent
id: DI-FABRICA-COMPETENCIA
title: Conferir uma competência contra âncora medida antes de publicar
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-exemplo-fabrica.md
  captured_at: '2026-09-17T00:00:00Z'
  sha256: c820a57d632bf5b05dac362f1df7c4a251d27e215aab4b85d1a55ab95cf207c1
success:
- Sem âncora medida o veredito é ACEITO_SEM_ANCORA e não autoriza publicar.
- Toda diferença recebe exatamente uma de seis classificações.
- Um valor de ponto flutuante em campo monetário é recusado na entrada.
- Uma divergência de um centavo é recusada antes da publicação.
- Cada execução deixa evidência que reconstrói o veredito sem reexecutar.
out_of_scope:
- Corrigir defeitos da origem — a fábrica classifica, nunca corrige.
- Substituir o sistema atual, que segue rodando em paralelo.
- Interface visual ou painel.
---
# Conferir uma competência contra âncora medida antes de publicar

## Delivery outcome

Ler o arquivo de uma competência, produzir o agregado, compará-lo contra a âncora medida na origem, classificar toda diferença encontrada e deixar um pacote de evidência — recusando publicar quando não houver prova.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
