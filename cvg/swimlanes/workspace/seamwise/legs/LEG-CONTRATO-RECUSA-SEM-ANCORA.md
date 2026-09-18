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
    given: um contrato com os cinco números nomeados (count_linhas, sum_vl_liquido, min, max, linhas_invalidas),
      a procedência (aprovador, data, comando que mediu) E o layout de leitura (posições, formato monetário,
      chave do registro)
    when: o contrato é carregado
    then: âncora, procedência e layout saem juntos, com os cinco controles sob os MESMOS nomes que o agregado
      usa — count_linhas, sum_vl_liquido, min_vl_liquido, max_vl_liquido, linhas_invalidas; a MESMA âncora
      sem aprovador, sem data ou sem layout resulta em NAO_MEDIDO
  - id: B-2
    given: uma competência sem âncora no contrato
    when: o contrato é carregado
    then: RETORNA o veredito NAO_MEDIDO como valor — não grava nem encerra o processo; quem persiste é
      a evidência, e quem encerra é o orquestrador
  evals:
  - id: eval_1
    description: Cinco valores nomeados com procedência; sem aprovador ou data vira NAO_MEDIDO
    bash: pytest -q tests/test_contrato.py -k "ancorada or sem_procedencia"
    verifies:
    - B-1
  - id: eval_2
    description: Sem âncora retorna NAO_MEDIDO como valor, sem escrever em disco
    bash: pytest -q tests/test_contrato.py -k "nao_medido and not evidencia"
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
source_seam_sha256: 94901d8029fd3cc2133f3866658109bd10c1a80c6d9d3681320f45353f83199a
---
# A fábrica recusa construir sem âncora medida

## Observable proof

Competência sem âncora no contrato produz NAO_MEDIDO e exit diferente de zero, antes de qualquer leitura de dado.

## Runnable leaves

- `T-20260917-contrato-ancora` — Carregar o contrato e recusar competência sem âncora: Competência com âncora carrega os cinco valores; sem âncora retorna NAO_MEDIDO e exit 1.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
