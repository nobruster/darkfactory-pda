---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-CONTRATO-RECUSA-SEM-ANCORA
seam_id: SEAM-CONTRATO-ANCORA
swimlane_id: LANE-CONTRATO
observable_state: A fábrica recusa construir sem âncora medida
proof: Competência sem âncora no contrato produz NAO_MEDIDO e exit diferente de zero, antes de qualquer
  leitura de dado.
requires: []
produces:
- contrato validado
tasks:
- id: T-20260917-contrato-ancora
  title: Carregar o contrato e recusar competência sem âncora
  goal: Fazer a ausência de prova bloquear, em vez de virar verde.
  done_condition: Competência com âncora carrega os cinco valores; sem âncora retorna NAO_MEDIDO e exit
    1.
  effort: S
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on: []
  touches_paths: []
  creates_paths:
  - src/fabrica/contrato.py
  - tests/test_contrato.py
  behavior:
  - id: B-1
    given: uma competência com âncora medida no contrato
    when: o contrato é carregado
    then: os cinco valores da âncora são devolvidos
  - id: B-2
    given: uma competência sem âncora no contrato
    when: o contrato é carregado
    then: o resultado é NAO_MEDIDO e o processo sai com código 1
  evals:
  - id: eval_1
    description: Competência ancorada carrega os cinco valores
    bash: pytest -q tests/test_contrato.py -k ancorada
    verifies:
    - B-1
  - id: eval_2
    description: Competência sem âncora recusa construir
    bash: pytest -q tests/test_contrato.py -k nao_medido
    verifies:
    - B-2
  - id: eval_3
    description: A âncora carregada bate com o contrato em disco
    bash: pytest -q tests/test_contrato.py -k integridade
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: gerar a âncora automaticamente quando ela falta
    reason: um número que ninguém viu medir é um palpite
    instead: retornar NAO_MEDIDO e parar
  - action: tratar âncora ausente como zero
    reason: o gate compararia contra nada e publicaria ACEITO
    instead: distinguir ausência de valor
  - action: editar a âncora para um veredito passar
    reason: falsifica a verdade contra a qual tudo é medido
    instead: investigar; âncora revista exige nova aprovação
  do_not_touch:
  - cvg/docs/adrs
  rollback: Remover o carregador de contrato e seus testes.
  observability: contagem de competências ancoradas no contrato
source_seam_sha256: 4daea285d89dc2539661e1279d747c216a34bdab45c61b75fa698179656c3b45
---
# A fábrica recusa construir sem âncora medida

## Observable proof

Competência sem âncora no contrato produz NAO_MEDIDO e exit diferente de zero, antes de qualquer leitura de dado.

## Runnable leaves

- `T-20260917-contrato-ancora` — Carregar o contrato e recusar competência sem âncora: Competência com âncora carrega os cinco valores; sem âncora retorna NAO_MEDIDO e exit 1.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
