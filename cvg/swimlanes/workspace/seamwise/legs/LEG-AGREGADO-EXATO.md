---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-AGREGADO-EXATO
seam_id: SEAM-AGREGACAO
swimlane_id: LANE-AGREGACAO
observable_state: O agregado é exato e a chave é o código
proof: Float recusado; precisão baixa acusa a perda; agrupar por descrição diverge de agrupar por código.
requires:
- registros lidos
produces:
- agregado da competência
tasks:
- id: T-20260921-agregacao-exata
  title: Somar com precisão declarada e agrupar pelo código
  goal: Tornar as três decisões de decimal explícitas e verificáveis.
  done_condition: Float recusado na entrada; os cinco controles saem nomeados; agrupar por descrição diverge
    de agrupar por código.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on:
  - T-20260921-leitura-posicional
  touches_paths: []
  creates_paths:
  - src/pda/agregacao.py
  - tests/test_agregacao.py
  behavior:
  - id: B-1
    given: um valor de ponto flutuante em campo monetário
    when: o agregado é calculado
    then: a entrada é recusada com erro explícito, e o agregado devolvido traz os cinco controles nomeados
  - id: B-2
    given: um contexto decimal de precisão baixa e valores em empate exato
    when: o total é calculado
    then: precisão e modo são declarados, não herdados — a perda por precisão é acusada, e arredondar
      por campo produz total diferente de arredondar no total
  evals:
  - id: eval_1
    description: Float recusado; cinco controles nomeados no agregado
    bash: pytest -q tests/test_agregacao.py -k "recusa_float or cinco_controles"
    verifies:
    - B-1
  - id: eval_2
    description: Precisão e modo declarados; granularidade no total
    bash: pytest -q tests/test_agregacao.py -k "precisao_declarada or granularidade"
    verifies:
    - B-2
  - id: eval_3
    description: Agrupar por descrição diverge de agrupar por código
    bash: pytest -q tests/test_agregacao.py -k chave_e_codigo
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: herdar o arredondamento padrão da linguagem
    reason: defaults divergem e o erro fica estruturalmente verde
    instead: declarar precisão, granularidade e regra
  - action: agrupar por descricao_especie
    reason: quatro espécies virariam uma linha e o total bateria
    instead: agrupar pelo código da posição 12
  - action: arredondar a cada soma parcial
    reason: o erro de arredondamento acumula linha a linha
    instead: somar exato e arredondar uma vez no final
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  rollback: Remover o agregador e seus testes.
  observability: total agregado e espécies distintas
source_seam_sha256: d41f37234f2d7dcaf6109914d7bf9cb28f882060fe10be0a5868bec97b96b597
---
# O agregado é exato e a chave é o código

## Observable proof

Float recusado; precisão baixa acusa a perda; agrupar por descrição diverge de agrupar por código.

## Runnable leaves

- `T-20260921-agregacao-exata` — Somar com precisão declarada e agrupar pelo código: Float recusado na entrada; os cinco controles saem nomeados; agrupar por descrição diverge de agrupar por código.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
