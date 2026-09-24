---
schema_version: 1
kind: decision
id: DEC-CHECK-NO-CREATE
status: accepted
owner: Bruno Nunes
rationale: 'Correção do plano em 2026-09-24, depois do perf-gold esgotar as 5 tentativas: o plano pedia
  UM CHECK combinado e o teste selado exige um CHECK por coluna. Medido: o Delta 3.2.1 aceita os CHECK
  por coluna no próprio CREATE, num commit, e eles recusam o negativo. O ganho é um commit, não um CHECK
  — o teste selado continua valendo.'
---
# DEC-CHECK-NO-CREATE

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Correção do plano em 2026-09-24, depois do perf-gold esgotar as 5 tentativas: o plano pedia UM CHECK combinado e o teste selado exige um CHECK por coluna. Medido: o Delta 3.2.1 aceita os CHECK por coluna no próprio CREATE, num commit, e eles recusam o negativo. O ganho é um commit, não um CHECK — o teste selado continua valendo.
