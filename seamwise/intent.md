---
schema_version: 1
kind: delivery-intent
id: DI-PDA-PROCEDENCIA
title: Vincular a partição da landing ao CSV de origem
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- CSV com sha256 diferente do contrato não vincula nada.
- Partição cujo conteúdo não é a transformação do CSV não vincula.
- A Bronze só tira a marca quando hash, manifesto e controles conferem.
out_of_scope:
- 'Regravar a partição ou rodar o produtor de novo: ele grava com append (ADR 0011) e duplicaria 41,5
  M linhas.'
- Editar src/produtor/gravar_lago.py, que está sem Task-Spec (Regra 11).
- 'Alterar o contrato: o sha256 do CSV já está declarado e aprovado.'
---
# Vincular a partição da landing ao CSV de origem

## Delivery outcome

Provar que a partição competencia=2026-01 na landing é a transformação do CSV cujo sha256 o contrato declara, gravar essa prova ao lado da partição, e fazer a Bronze conferi-la — para a marca PROCEDENCIA_NAO_VINCULADA sair por prova, nunca por decreto.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
