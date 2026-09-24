---
schema_version: 1
kind: decision
id: DEC-TESTES-LEVES-SEM-TOCAR-ASSERCAO
status: accepted
owner: Bruno Nunes
rationale: 'Exceção declarada à regra de não editar teste selado: só auxiliares e fixtures mudam; a prova
  é executável — mesmos ids coletados e corpo de cada test_* idêntico pela AST.'
---
# DEC-TESTES-LEVES-SEM-TOCAR-ASSERCAO

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Exceção declarada à regra de não editar teste selado: só auxiliares e fixtures mudam; a prova é executável — mesmos ids coletados e corpo de cada test_* idêntico pela AST.
