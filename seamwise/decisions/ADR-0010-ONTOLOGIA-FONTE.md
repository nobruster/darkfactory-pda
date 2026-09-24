---
schema_version: 1
kind: decision
id: ADR-0010-ONTOLOGIA-FONTE
status: accepted
owner: Bruno Nunes
rationale: 'ADR 0010, decidido pelo dono em 2026-09-24: a ontologia versionada é a fonte da verdade; a
  Delta especie e o Postgres são projeções reconferidas, consultadas por agentes e BI fora do Spark. Postgres
  como fonte foi rejeitado: dado editado no banco escapa da cadeia.'
---
# ADR-0010-ONTOLOGIA-FONTE

Status: **accepted**

Owner: Bruno Nunes

## Rationale

ADR 0010, decidido pelo dono em 2026-09-24: a ontologia versionada é a fonte da verdade; a Delta especie e o Postgres são projeções reconferidas, consultadas por agentes e BI fora do Spark. Postgres como fonte foi rejeitado: dado editado no banco escapa da cadeia.
