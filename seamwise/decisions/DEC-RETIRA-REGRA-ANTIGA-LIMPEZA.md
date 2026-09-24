---
schema_version: 1
kind: decision
id: DEC-RETIRA-REGRA-ANTIGA-LIMPEZA
status: accepted
owner: Bruno Nunes
rationale: 'Decidido pelo dono em 2026-09-24: atualizar o teste pela cadeia. test_commit_seguido_de_outro_preserva
  (v4) espera PRESERVADO num cenário idêntico ao de test_substituida_conferida_apaga, que espera APAGADO
  pela regra nova que o dono pediu. Exceção declarada à regra de não editar teste selado: sai exatamente
  um teste; a guarda confere a lista.'
---
# DEC-RETIRA-REGRA-ANTIGA-LIMPEZA

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Decidido pelo dono em 2026-09-24: atualizar o teste pela cadeia. test_commit_seguido_de_outro_preserva (v4) espera PRESERVADO num cenário idêntico ao de test_substituida_conferida_apaga, que espera APAGADO pela regra nova que o dono pediu. Exceção declarada à regra de não editar teste selado: sai exatamente um teste; a guarda confere a lista.
