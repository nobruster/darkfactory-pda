---
schema_version: 1
kind: system-map
claim: proposed
components:
- Contrato e âncora
- Leitura posicional
- Agregação monetária
- Juízo do agregado
- Pacote de evidência
- Orquestração da execução
external_dependencies:
- Arquivo CSV da competência, imutável em _raw/
- Âncora medida na origem por fora do pipeline
- Spark e MinIO, a montar — o carregamento ao lago é escopo próprio
unknowns: []
proposed_steel_thread:
- LEG-CONTRATO-RECUSA-SEM-ANCORA
- LEG-LEITURA-POSICIONAL
- LEG-AGREGADO-EXATO
- LEG-JUIZO-ACUSA
- LEG-EVIDENCIA-RECONSTROI
- LEG-DESFECHO-COM-PACOTE
objections: []
contentions: []
---
# System Map

## Components

- Contrato e âncora
- Leitura posicional
- Agregação monetária
- Juízo do agregado
- Pacote de evidência
- Orquestração da execução

## External dependencies

- Arquivo CSV da competência, imutável em _raw/
- Âncora medida na origem por fora do pipeline
- Spark e MinIO, a montar — o carregamento ao lago é escopo próprio

## Unknowns

- (none)

This is a **proposed** map. The delivery-plan transformation must
close or gate every material unknown; it may not reinterpret this text as
runtime proof.
