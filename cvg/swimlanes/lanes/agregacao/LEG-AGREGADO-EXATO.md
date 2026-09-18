> Projetado de `LEG-AGREGADO-EXATO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `8c2a38f38b30e507816ba172a27d8f382ad099d9886e8a05d7aaace54d36fdc0`

---

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
    then: a entrada é recusada com erro explícito, e o agregado devolvido traz os CINCO controles nomeados
      que o juízo compara — count_linhas, sum_vl_liquido, min_vl_liquido, max_vl_liquido, linhas_invalidas
  - id: B-2
    given: valores em empate exato, um contexto decimal cujo default já é meio-para-par, e a alternativa
      de arredondar por campo
    when: o total é calculado
    then: o modo é passado EXPLICITAMENTE — um teste que troca o default do contexto para meio-para-cima
      falha se a implementação o herdar; e arredondar por campo produz total diferente (2,345+2,345 dá
      4,68 por campo e 4,69 só no total), provando a granularidade do ADR 0004
  evals:
  - id: eval_1
    description: Float recusado; o agregado traz os cinco controles nomeados
    bash: pytest -q tests/test_agregacao.py -k "recusa_float or cinco_controles"
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
source_seam_sha256: c137eb3fadc449712d848a11e2d210c0e9d22db5bc9a6749629cf20ff725efda
---
# O agregado é exato e recusa float

## Observable proof

Float em campo monetário é recusado; HALF_EVEN e HALF_UP produzem totais diferentes no mesmo dado.

## Runnable leaves

- `T-20260917-agregacao-exata` — Somar valores monetários com meio-para-par: Float é recusado na entrada e o total usa meio-para-par a duas casas.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
