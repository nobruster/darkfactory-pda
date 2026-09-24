---
schema_version: 1
kind: decision
id: DEC-PERFORMANCE-MEDIDA
status: accepted
owner: Bruno Nunes
rationale: 'Decidido pelo dono em 2026-09-24: otimizar unpersist, memória declarada, reconferência numa
  passada e testes. Medido: suíte numa JVM estourou 1 GB herdado; com 6 GB declarados a Bronze caiu de
  506s para 374s de executor e o spill de 1307 para 196 MB. Todo ganho passa pelo gate spark-perf com
  saída idêntica.'
---
# DEC-PERFORMANCE-MEDIDA

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Decidido pelo dono em 2026-09-24: otimizar unpersist, memória declarada, reconferência numa passada e testes. Medido: suíte numa JVM estourou 1 GB herdado; com 6 GB declarados a Bronze caiu de 506s para 374s de executor e o spill de 1307 para 196 MB. Todo ganho passa pelo gate spark-perf com saída idêntica.
