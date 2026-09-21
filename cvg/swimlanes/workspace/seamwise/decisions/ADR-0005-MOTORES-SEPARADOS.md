---
schema_version: 1
kind: decision
id: ADR-0005-MOTORES-SEPARADOS
status: accepted
owner: Bruno Nunes
rationale: Spark grava no lago, Python puro confere. Um juiz que usa o motor que julga herda seus pontos
  cegos — se a leitura distribuída descartar uma das duas colunas Espécie, os dois lados concordariam
  e nada acusaria.
---
# ADR-0005-MOTORES-SEPARADOS

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Spark grava no lago, Python puro confere. Um juiz que usa o motor que julga herda seus pontos cegos — se a leitura distribuída descartar uma das duas colunas Espécie, os dois lados concordariam e nada acusaria.
