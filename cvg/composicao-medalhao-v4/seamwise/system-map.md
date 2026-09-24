---
schema_version: 1
kind: system-map
claim: proposed
components:
- Ingestão julgada
- Gold principal
- Contrato com grupos
- Gold por assuntos
- Limpeza do preparo
external_dependencies:
- Silver publicada em s3a://silver/pda/beneficios-emitidos
- Gold principal publicada em s3a://gold/pda/beneficios-emitidos
- grupos_especie aprovado no contrato
unknowns: []
proposed_steel_thread:
- LEG-JUIZO-NA-INGESTAO
- LEG-GOLD-LE-SILVER
- LEG-CONTRATO-EXPOE-GRUPOS
- LEG-GOLD-ASSUNTOS
- LEG-LIMPA-PREPARO
objections: []
contentions: []
---
# System Map

## Components

- Ingestão julgada
- Gold principal
- Contrato com grupos
- Gold por assuntos
- Limpeza do preparo

## External dependencies

- Silver publicada em s3a://silver/pda/beneficios-emitidos
- Gold principal publicada em s3a://gold/pda/beneficios-emitidos
- grupos_especie aprovado no contrato

## Unknowns

- (none)

This is a **proposed** map. The delivery-plan transformation must
close or gate every material unknown; it may not reinterpret this text as
runtime proof.
