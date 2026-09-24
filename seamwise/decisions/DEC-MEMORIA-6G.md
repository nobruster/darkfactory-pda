---
schema_version: 1
kind: decision
id: DEC-MEMORIA-6G
status: accepted
owner: Bruno Nunes
rationale: 'Correção de 2026-09-24: a costura de performance mandou declarar a memória sem dizer quanto,
  e a entrega declarou 1g. Medido: suíte numa JVM ainda estoura; gate NAO_MEDIDO por 6g->1g; o builder
  define o heap efetivo (6g -> 6,00 GiB). O valor é o das baselines.'
---
# DEC-MEMORIA-6G

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Correção de 2026-09-24: a costura de performance mandou declarar a memória sem dizer quanto, e a entrega declarou 1g. Medido: suíte numa JVM ainda estoura; gate NAO_MEDIDO por 6g->1g; o builder define o heap efetivo (6g -> 6,00 GiB). O valor é o das baselines.
