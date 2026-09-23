---
schema_version: 1
kind: decision
id: DEC-PROCEDENCIA-POR-VINCULADOR
status: accepted
owner: Bruno Nunes
rationale: 'Decidido pelo dono em 2026-09-23: o vínculo de procedência entra por tarefa da cadeia. Como
  o produtor grava com append e está sem Task-Spec, um vinculador NOVO prova a procedência sem regravar
  dado: compara o conteúdo da partição com a transformação do CSV e grava _PROCEDENCIA.json ao lado da
  partição.'
---
# DEC-PROCEDENCIA-POR-VINCULADOR

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Decidido pelo dono em 2026-09-23: o vínculo de procedência entra por tarefa da cadeia. Como o produtor grava com append e está sem Task-Spec, um vinculador NOVO prova a procedência sem regravar dado: compara o conteúdo da partição com a transformação do CSV e grava _PROCEDENCIA.json ao lado da partição.
