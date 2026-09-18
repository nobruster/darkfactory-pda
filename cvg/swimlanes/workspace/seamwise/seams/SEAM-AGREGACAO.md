---
schema_version: 1
kind: seam
claim: derived
id: SEAM-AGREGACAO
name: Agregação monetária
description: Separa a soma exata da comparação contra a âncora.
evidence:
- E-ADR-ARREDONDAMENTO
responsibility: Somar valores monetários com aritmética exata declarada.
consumes:
- registros lidos
produces:
- agregado da competência
owner: agregacao
independent_proof: Ponto flutuante em campo monetário é recusado na entrada, e o mesmo dado arredondado
  meio-para-cima leva o juízo a um VEREDITO diferente — total diferente não basta, porque o juízo poderia
  re-arredondar e anular a diferença (objeção C5).
decision_ids:
- ADR-0001-HALF-EVEN
- ADR-0004-ARREDONDA-NO-TOTAL
rejected_alternatives:
- alternative: Usar ponto flutuante e arredondar no final
  reason: 0.1 + 0.2 != 0.3 em binário; o centavo some sem nada acusar.
- alternative: Arredondar cada campo na entrada
  reason: Cada arredondamento é uma perda e elas somam — 2,345 + 2,345 dá 4,68 por campo contra 4,69 só
    no total, ambos meio-para-par.
swimlane:
  id: LANE-AGREGACAO
  name: Agregação lane
  owner: agregacao
  legs:
  - id: LEG-AGREGADO-EXATO
    observable_state: O agregado é exato e recusa float
    proof: Float em campo monetário é recusado; HALF_EVEN e HALF_UP produzem totais diferentes no mesmo
      dado.
    requires:
    - registros lidos
    produces:
    - agregado da competência
    tasks:
    - id: T-20260917-agregacao-exata
      title: Somar valores monetários com meio-para-par
      goal: Tornar a regra de arredondamento explícita e verificável.
      done_condition: Float é recusado na entrada e o total usa meio-para-par a duas casas.
      effort: M
      profile: standard
      execution_backend: any
      required_tools:
      - git
      - bash
      - python3
      - pytest
      depends_on:
      - T-20260917-leitura-competencia
      touches_paths: []
      creates_paths:
      - src/fabrica/agregacao.py
      - tests/test_agregacao.py
      behavior:
      - id: B-1
        given: um valor de ponto flutuante em campo monetário
        when: o agregado é calculado
        then: a entrada é recusada com erro explícito
      - id: B-2
        given: valores em empate exato, um contexto decimal cujo default já é meio-para-par, e a alternativa
          de arredondar por campo
        when: o total é calculado
        then: o modo é passado EXPLICITAMENTE — um teste que troca o default do contexto para meio-para-cima
          falha se a implementação o herdar; e arredondar por campo produz total diferente (2,345+2,345
          dá 4,68 por campo e 4,69 só no total), provando a granularidade do ADR 0004
      evals:
      - id: eval_1
        description: Float em campo monetário é recusado
        bash: pytest -q tests/test_agregacao.py -k recusa_float
        verifies:
        - B-1
      - id: eval_2
        description: Modo explícito (falha se herdar o contexto) e granularidade do total
        bash: pytest -q tests/test_agregacao.py -k "modo_explicito or granularidade"
        verifies:
        - B-2
      - id: eval_3
        description: O total de 2026-03 reproduz a âncora medida
        bash: pytest -q tests/test_agregacao.py -k total_ancora
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: herdar o arredondamento padrão da linguagem
        reason: defaults divergem e o erro fica estruturalmente verde
        instead: declarar a regra no contrato e testá-la
      - action: converter float para decimal silenciosamente
        reason: o centavo já se perdeu antes da conversão
        instead: recusar float na entrada
      - action: arredondar a cada soma parcial
        reason: o erro de arredondamento acumula linha a linha
        instead: somar exato e arredondar uma vez no final
      do_not_touch:
      - cvg/docs/adrs
      rollback: Remover o agregador e seus testes.
      observability: total agregado por competência
---
# Agregação monetária

Separa a soma exata da comparação contra a âncora.

## Responsibility

Somar valores monetários com aritmética exata declarada.

## Independent proof

Ponto flutuante em campo monetário é recusado na entrada, e o mesmo dado arredondado meio-para-cima leva o juízo a um VEREDITO diferente — total diferente não basta, porque o juízo poderia re-arredondar e anular a diferença (objeção C5).

## Rejected alternatives

- **Usar ponto flutuante e arredondar no final** — 0.1 + 0.2 != 0.3 em binário; o centavo some sem nada acusar.
- **Arredondar cada campo na entrada** — Cada arredondamento é uma perda e elas somam — 2,345 + 2,345 dá 4,68 por campo contra 4,69 só no total, ambos meio-para-par.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
