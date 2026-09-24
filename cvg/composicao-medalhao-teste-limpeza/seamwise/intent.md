---
schema_version: 1
kind: delivery-intent
id: DI-PDA-TESTE-LIMPEZA
title: Suíte coerente com a regra aprovada da limpeza
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- Suíte inteira numa JVM só, verde.
- Só um teste sai; a lista do módulo é conferida.
out_of_scope:
- Mudar o comportamento da limpeza.
---
# Suíte coerente com a regra aprovada da limpeza

## Delivery outcome

Retirar test_commit_seguido_de_outro_preserva, que contradiz a regra aprovada e duplica o cenário de um teste novo.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
