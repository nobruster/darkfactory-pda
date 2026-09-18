---
schema_version: 1
kind: decision
id: ADR-0006-PRECISAO-DECLARADA
status: accepted
owner: Bruno Nunes
rationale: A precisão do contexto decimal é declarada, não herdada. Em prec=6, 10000.00 + 0.01 vira 10000.0
  e quantizar depois não recupera — a perda é anterior ao arredondamento.
---
# ADR-0006-PRECISAO-DECLARADA

Status: **accepted**

Owner: Bruno Nunes

## Rationale

A precisão do contexto decimal é declarada, não herdada. Em prec=6, 10000.00 + 0.01 vira 10000.0 e quantizar depois não recupera — a perda é anterior ao arredondamento.
