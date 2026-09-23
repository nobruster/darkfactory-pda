---
schema_version: 1
kind: decision
id: DEC-CAMADAS-EM-DELTA
status: accepted
owner: Bruno Nunes
rationale: 'Decidido pelo dono em 2026-09-23: Bronze, Silver e Gold gravam em DELTA LAKE no MinIO, para
  ter imposição e evolução de schema, commit atômico e histórico. REVISA o protocolo de DEC-CAMADAS-GRAVAM-NO-MINIO
  (manifesto _ESTADO.json + ponteiro _ATUAL), que continua valendo quanto ao destino: o commit no _delta_log
  faz o papel do ponteiro, o userMetadata do commit o do manifesto, e versionAsOf o de resolver uma vez.
  Medido: Delta 3.2.1 sobre Spark 3.5.9 grava e lê em s3a://bronze com decimal(14,2) preservado — DELTA_FUMACA=OK.
  Um único escritor: o LogStore padrão do S3 basta; escritores concorrentes exigiriam o do DynamoDB.'
---
# DEC-CAMADAS-EM-DELTA

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Decidido pelo dono em 2026-09-23: Bronze, Silver e Gold gravam em DELTA LAKE no MinIO, para ter imposição e evolução de schema, commit atômico e histórico. REVISA o protocolo de DEC-CAMADAS-GRAVAM-NO-MINIO (manifesto _ESTADO.json + ponteiro _ATUAL), que continua valendo quanto ao destino: o commit no _delta_log faz o papel do ponteiro, o userMetadata do commit o do manifesto, e versionAsOf o de resolver uma vez. Medido: Delta 3.2.1 sobre Spark 3.5.9 grava e lê em s3a://bronze com decimal(14,2) preservado — DELTA_FUMACA=OK. Um único escritor: o LogStore padrão do S3 basta; escritores concorrentes exigiriam o do DynamoDB.
