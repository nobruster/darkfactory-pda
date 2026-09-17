---
schema_version: 1
kind: seam
claim: derived
id: SEAM-CONTRATO-ANCORA
name: Contrato e âncora
description: Separa a verdade declarada do código que a consome.
evidence:
- E-ANCORA-202603
responsibility: Guardar a âncora medida e recusar construir sem ela.
consumes:
- âncora medida na origem
produces:
- contrato validado
owner: contrato
independent_proof: Um contrato sem âncora para a competência pedida retorna NAO_MEDIDO e o processo termina
  em código diferente de zero.
decision_ids:
- ADR-0002-ANCORA-2026-03
rejected_alternatives:
- alternative: Gerar a âncora rodando o pipeline na competência
  reason: Seria o pipeline conferindo a si mesmo; defeito comum às duas execuções ficaria invisível.
swimlane:
  id: LANE-CONTRATO
  name: Contrato lane
  owner: contrato
  legs:
  - id: LEG-CONTRATO-RECUSA-SEM-ANCORA
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
      done_condition: Competência com âncora carrega os cinco valores; sem âncora retorna NAO_MEDIDO e
        exit 1.
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
---
# Contrato e âncora

Separa a verdade declarada do código que a consome.

## Responsibility

Guardar a âncora medida e recusar construir sem ela.

## Independent proof

Um contrato sem âncora para a competência pedida retorna NAO_MEDIDO e o processo termina em código diferente de zero.

## Rejected alternatives

- **Gerar a âncora rodando o pipeline na competência** — Seria o pipeline conferindo a si mesmo; defeito comum às duas execuções ficaria invisível.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
