---
schema_version: 1
kind: seam
claim: derived
id: SEAM-CONTRATO
name: Contrato e âncora
description: Separa a verdade declarada do código que a consome.
evidence:
- E-ANCORA-202601
responsibility: Guardar a âncora medida e o layout posicional, e recusar construir sem eles.
consumes:
- âncora medida na origem
produces:
- contrato validado
owner: contrato
independent_proof: Competência sem âncora devolve NAO_MEDIDO como valor, antes de abrir o arquivo.
decision_ids:
- ADR-0002-POSICIONAL
rejected_alternatives:
- alternative: Derivar a âncora do Parquet já publicado
  reason: Mede o que o pipeline produziu, não o que a fonte publicou; um defeito comum às duas execuções
    ficaria invisível.
swimlane:
  id: LANE-CONTRATO
  name: Contrato lane
  owner: contrato
  legs:
  - id: LEG-CONTRATO-RECUSA-SEM-ANCORA
    observable_state: A fábrica recusa construir sem âncora medida
    proof: Competência sem âncora devolve NAO_MEDIDO; com âncora incompleta (sem aprovador ou sem data)
      também.
    requires: []
    produces:
    - contrato validado
    tasks:
    - id: T-20260921-contrato-ancora
      title: Carregar contrato, âncora e layout posicional
      goal: Fazer a ausência de prova bloquear em vez de virar verde.
      done_condition: Os cinco controles e o layout saem com procedência; sem âncora, ou sem aprovador,
        retorna NAO_MEDIDO como valor.
      effort: M
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
      - src/pda/contrato.py
      - tests/test_contrato.py
      - contracts/competencia-202601.yaml
      behavior:
      - id: B-1
        given: um contrato com os cinco controles nomeados, a procedência e o layout posicional
        when: o contrato é carregado
        then: âncora, procedência e layout saem juntos; a mesma âncora sem aprovador ou sem data de medição
          resulta em NAO_MEDIDO
      - id: B-2
        given: uma competência sem âncora no contrato
        when: o contrato é carregado
        then: retorna NAO_MEDIDO como valor, sem gravar nem encerrar o processo
      evals:
      - id: eval_1
        description: Cinco controles com procedência; sem aprovador vira NAO_MEDIDO
        bash: pytest -q tests/test_contrato.py -k "ancorada or sem_procedencia"
        verifies:
        - B-1
      - id: eval_2
        description: Sem âncora retorna NAO_MEDIDO sem escrever em disco
        bash: pytest -q tests/test_contrato.py -k nao_medido
        verifies:
        - B-2
      - id: eval_3
        description: O layout declara as 14 posições, com Espécie em 12 e 13
        bash: pytest -q tests/test_contrato.py -k layout
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: gerar a âncora quando ela falta
        reason: um número que ninguém viu medir é um palpite
        instead: retornar NAO_MEDIDO
      - action: editar a âncora para um veredito passar
        reason: falsifica a verdade contra a qual tudo é medido
        instead: investigar; âncora revista exige nova aprovação
      - action: declarar colunas por nome no contrato
        reason: Espécie aparece duas vezes e o nome não decide qual
        instead: declarar o índice posicional
      do_not_touch:
      - _raw
      - cvg/docs/adrs
      rollback: Remover o carregador de contrato e seus testes.
      observability: competências ancoradas no contrato
---
# Contrato e âncora

Separa a verdade declarada do código que a consome.

## Responsibility

Guardar a âncora medida e o layout posicional, e recusar construir sem eles.

## Independent proof

Competência sem âncora devolve NAO_MEDIDO como valor, antes de abrir o arquivo.

## Rejected alternatives

- **Derivar a âncora do Parquet já publicado** — Mede o que o pipeline produziu, não o que a fonte publicou; um defeito comum às duas execuções ficaria invisível.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
