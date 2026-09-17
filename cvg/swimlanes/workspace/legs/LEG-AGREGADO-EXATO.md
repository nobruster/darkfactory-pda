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
    then: a entrada é recusada com erro explícito
  - id: B-2
    given: valores em empate exato de arredondamento
    when: o total é calculado com meio-para-par
    then: o resultado difere do calculado com meio-para-cima
  evals:
  - id: eval_1
    description: Float em campo monetário é recusado
    bash: pytest -q tests/test_agregacao.py -k recusa_float
    verifies:
    - B-1
  - id: eval_2
    description: Meio-para-par difere de meio-para-cima
    bash: pytest -q tests/test_agregacao.py -k half_even
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
source_seam_sha256: b48a8c1ccc439cb17c484183fcb1562f0043b0d2caad08d50c376da8b1d1f472
---
# O agregado é exato e recusa float

## Observable proof

Float em campo monetário é recusado; HALF_EVEN e HALF_UP produzem totais diferentes no mesmo dado.

## Runnable leaves

- `T-20260917-agregacao-exata` — Somar valores monetários com meio-para-par: Float é recusado na entrada e o total usa meio-para-par a duas casas.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
