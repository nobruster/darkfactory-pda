---
schema_version: 1
kind: delivery-intent
id: DI-PDA-ADOTA-PRODUTOR
title: Produtor e gravador do lago sob Task-Spec
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- verificar_procedencia.py devolve PROCEDENCIA=OK pela primeira vez.
- Suíte inteira numa JVM só, verde, sem skip.
- As funções dos dois módulos iguais às de antes, salvo o --destino.
out_of_scope:
- Mudar a gravação para Delta ou o destino do landing.
- Regravar o landing de 2026-01.
- Adotar vincular_procedencia.py (já tem Task-Spec).
---
# Produtor e gravador do lago sob Task-Spec

## Delivery outcome

Os dois únicos arquivos de src/ sem Task-Spec passam a ter uma, com testes do comportamento que já gravou o landing, sem mudá-lo.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
