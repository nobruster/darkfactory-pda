---
schema_version: 1
kind: decision
id: DEC-JUIZO-NA-INGESTAO
status: accepted
owner: Bruno Nunes
rationale: 'Decidido pelo dono em 2026-09-23: a Gold não recebe o arquivo inteiro. Medido: a Gold principal
  recalculava Bronze e Silver da landing e o juiz lia as 41,5 M linhas do CSV — cerca de 20 dos 22 minutos
  — sem ler a Silver publicada. O ADR 0006 (Spark grava, Python confere) continua valendo; o que muda
  é ONDE o juízo acontece: na ingestão, uma vez, onde o bruto é legitimamente lido. As camadas seguintes
  reconciliam exato contra a anterior e seguem a linhagem até o pacote ACEITO da ingestão.'
---
# DEC-JUIZO-NA-INGESTAO

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Decidido pelo dono em 2026-09-23: a Gold não recebe o arquivo inteiro. Medido: a Gold principal recalculava Bronze e Silver da landing e o juiz lia as 41,5 M linhas do CSV — cerca de 20 dos 22 minutos — sem ler a Silver publicada. O ADR 0006 (Spark grava, Python confere) continua valendo; o que muda é ONDE o juízo acontece: na ingestão, uma vez, onde o bruto é legitimamente lido. As camadas seguintes reconciliam exato contra a anterior e seguem a linhagem até o pacote ACEITO da ingestão.
