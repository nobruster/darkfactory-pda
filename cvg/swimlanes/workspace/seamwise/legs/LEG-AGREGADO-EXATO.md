---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-AGREGADO-EXATO
seam_id: SEAM-AGREGACAO
swimlane_id: LANE-AGREGACAO
observable_state: O agregado é exato e recusa float
proof: Float em campo monetário é recusado; HALF_EVEN e HALF_UP produzem totais diferentes no mesmo dado.
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
    then: a entrada é recusada com erro explícito E o agregado é devolvido mesmo assim, com os CINCO controles
      nomeados (count_linhas, sum_vl_liquido, min_vl_liquido, max_vl_liquido, linhas_invalidas) e o campo
      monetário recusado contado em linhas_invalidas — recusar não é devolver nada
  - id: B-2
    given: valores em empate exato, um contexto cujo default já é meio-para-par, um contexto com prec=6,
      e a alternativa de arredondar por campo
    when: o total é calculado
    then: precisão E modo são DECLARADOS, não herdados — com prec=6 a soma acusa a perda (10000.00 + 0.01
      vira 10000.0, e quantizar depois não recupera, ADR 0006); trocar o default do contexto para meio-para-cima
      faz o teste falhar se a implementação o herdar; e arredondar por campo dá 4,68 contra 4,69 no total
      (ADR 0004)
  evals:
  - id: eval_1
    description: Float recusado; o agregado traz os cinco controles nomeados
    bash: pytest -q tests/test_agregacao.py -k "recusa_float or cinco_controles"
    verifies:
    - B-1
  - id: eval_2
    description: Precisão e modo declarados; prec=6 acusa; granularidade do total
    bash: pytest -q tests/test_agregacao.py -k "precisao_declarada or modo_explicito or granularidade"
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
source_seam_sha256: 6f39e5cd7a0a601adc08eee8f2ab4d38058ea72bdb75d74be554d4d95c9bcd50
---
# O agregado é exato e recusa float

## Observable proof

Float em campo monetário é recusado; HALF_EVEN e HALF_UP produzem totais diferentes no mesmo dado.

## Runnable leaves

- `T-20260917-agregacao-exata` — Somar valores monetários com meio-para-par: Float é recusado na entrada e o total usa meio-para-par a duas casas.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
