---
schema_version: 1
kind: decision
id: DEC-CAMADAS-GRAVAM-NO-MINIO
status: accepted
owner: Bruno Nunes
rationale: 'Decidido pelo dono em 2026-09-23: as camadas Bronze, Silver e Gold GRAVAM no MinIO — o medalhão
  existe para persistir as camadas, não para devolver objetos em memória. Destino: s3a://<camada>/pda/beneficios-emitidos/competencia=<c>/execucao=<id>/,
  em Parquet. Protocolo, igual nas três: grava os dados no prefixo da execução, RELÊ e reconfere o que
  gravou, grava o manifesto _ESTADO.json e por ÚLTIMO o ponteiro competencia=<c>/_ATUAL — um PUT único
  de objeto, que o S3 torna visível inteiro ou não torna. O consumidor lê pelo ponteiro, nunca por listagem.
  Isto define o destino e a atomicidade que o Pass 4 tinha adiado como storage.'
---
# DEC-CAMADAS-GRAVAM-NO-MINIO

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Decidido pelo dono em 2026-09-23: as camadas Bronze, Silver e Gold GRAVAM no MinIO — o medalhão existe para persistir as camadas, não para devolver objetos em memória. Destino: s3a://<camada>/pda/beneficios-emitidos/competencia=<c>/execucao=<id>/, em Parquet. Protocolo, igual nas três: grava os dados no prefixo da execução, RELÊ e reconfere o que gravou, grava o manifesto _ESTADO.json e por ÚLTIMO o ponteiro competencia=<c>/_ATUAL — um PUT único de objeto, que o S3 torna visível inteiro ou não torna. O consumidor lê pelo ponteiro, nunca por listagem. Isto define o destino e a atomicidade que o Pass 4 tinha adiado como storage.
