---
schema_version: 1
kind: decision
id: ADR-0005-MOTORES-SEPARADOS
status: accepted
owner: Bruno Nunes
rationale: 'Spark grava no lago, Python puro confere. Um juiz que usa o motor que julga herda seus pontos
  cegos — se a leitura distribuída descartar uma das duas colunas Espécie, os dois lados concordariam
  e nada acusaria. O ADR 0006 supersedeu a parte de ESCOPO do 0005, não esta: a separação de motores continua
  valendo, e é justamente ela que torna o juízo e o produtor entregáveis separáveis.'
---
# ADR-0005-MOTORES-SEPARADOS

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Spark grava no lago, Python puro confere. Um juiz que usa o motor que julga herda seus pontos cegos — se a leitura distribuída descartar uma das duas colunas Espécie, os dois lados concordariam e nada acusaria. O ADR 0006 supersedeu a parte de ESCOPO do 0005, não esta: a separação de motores continua valendo, e é justamente ela que torna o juízo e o produtor entregáveis separáveis.
