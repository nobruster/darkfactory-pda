---
schema_version: 1
kind: delivery-intent
id: DI-PDA-MEDALHAO-V4
title: Medalhão v4 — juízo na ingestão, Gold lê a Silver, Gold por assuntos
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- A Gold principal publica sem ler a landing nem o CSV.
- A Bronze só publica com o pacote ACEITO do juízo da ingestão.
- fat_especie e kpis_nacionais fecham exato com a âncora.
- Nenhum _preparo sobrevive a uma publicação conferida, e nada fora dele é apagado.
out_of_scope:
- 'fat_uf, fat_banco e perfil demográfico: exigem a landing v2 com as 14 colunas (Fase 2).'
- 'Alterar o orquestrador ou o juiz selados: eles são REUSADOS na ingestão, não modificados.'
---
# Medalhão v4 — juízo na ingestão, Gold lê a Silver, Gold por assuntos

## Delivery outcome

O arquivo bruto é lido UMA vez, na ingestão, onde o juízo com o segundo motor aceita a Bronze; Silver e Gold consomem só a camada anterior persistida; a Gold entrega tabelas por assunto; e o preparo é apagado depois da publicação conferida.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
