---
schema_version: 1
kind: system-map
claim: proposed
components:
- Bronze — leitura conferida
- Silver — defeito classificado
- Gold — agregado reconciliado
external_dependencies:
- Contrato validado, já selado em Tier 1 nesta fábrica
- Partição competencia=2026-01 no MinIO, escrita pelo produtor
- Spark 3.5.9 e os jars S3A, no contêiner pda-spark
- 'pytest num ambiente que também leia Parquet — medido: hoje nenhum dos dois tem os dois'
unknowns: []
proposed_steel_thread:
- LEG-BRONZE-REPRODUZ-ANCORA
- LEG-SILVER-PRESERVA-DEFEITO
- LEG-GOLD-RECONCILIA
objections: []
contentions: []
---
# System Map

## Components

- Bronze — leitura conferida
- Silver — defeito classificado
- Gold — agregado reconciliado

## External dependencies

- Contrato validado, já selado em Tier 1 nesta fábrica
- Partição competencia=2026-01 no MinIO, escrita pelo produtor
- Spark 3.5.9 e os jars S3A, no contêiner pda-spark
- pytest num ambiente que também leia Parquet — medido: hoje nenhum dos dois tem os dois

## Unknowns

- (none)

This is a **proposed** map. The delivery-plan transformation must
close or gate every material unknown; it may not reinterpret this text as
runtime proof.
