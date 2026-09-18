---
schema_version: 1
kind: decision
id: ADR-0004-ARREDONDA-NO-TOTAL
status: accepted
owner: Bruno Nunes
rationale: Arredonda uma vez, sobre o total final. Por campo, 2,345 + 2,345 dá 4,68 contra 4,69 — ambos
  meio-para-par. A mesma granularidade vale para a medição da âncora, senão a comparação mede a granularidade.
---
# ADR-0004-ARREDONDA-NO-TOTAL

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Arredonda uma vez, sobre o total final. Por campo, 2,345 + 2,345 dá 4,68 contra 4,69 — ambos meio-para-par. A mesma granularidade vale para a medição da âncora, senão a comparação mede a granularidade.
