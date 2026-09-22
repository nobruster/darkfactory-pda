---
schema_version: 1
kind: seam
claim: derived
id: SEAM-AGREGACAO
name: Agregação monetária
description: Separa a soma exata da comparação contra a âncora.
evidence:
- E-ANCORA-202601
responsibility: Somar o valor líquido com precisão declarada e agrupar pelo código.
consumes:
- registros lidos
produces:
- agregado da competência
owner: agregacao
independent_proof: Float é recusado na entrada; agrupar por descrição produz contagem diferente de agrupar
  por código.
decision_ids:
- ADR-0003-HALF-EVEN
- ADR-0004-CODIGO-E-CHAVE
rejected_alternatives:
- alternative: Usar float e arredondar no final
  reason: 0.1 + 0.2 != 0.3 em binário; o centavo some sem nada acusar.
- alternative: Agrupar por descricao_especie
  reason: 51 códigos colapsam em 40 descrições; quatro espécies virariam uma linha com o total continuando
    a bater.
swimlane:
  id: LANE-AGREGACAO
  name: Agregação lane
  owner: agregacao
  legs:
  - id: LEG-AGREGADO-EXATO
    observable_state: O agregado é exato e a chave é o código
    proof: Float recusado; precisão baixa acusa a perda; agrupar por descrição diverge de agrupar por
      código.
    requires:
    - registros lidos
    produces:
    - agregado da competência
    tasks:
    - id: T-20260921-agregacao-exata
      title: Somar com precisão declarada e agrupar pelo código
      goal: Tornar as três decisões de decimal explícitas e verificáveis.
      done_condition: Float recusado na entrada; os cinco controles saem nomeados; agrupar por descrição
        diverge de agrupar por código.
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
        given: um valor de ponto flutuante em campo monetário, e um lote com registros ilegíveis misturados
          aos válidos
        when: o agregado é calculado
        then: o float é recusado com erro explícito; os cinco controles são DOIS de contagem e TRÊS monetários,
          e só sum_vl_liquido é soma — count_linhas conta todo registro lido, linhas_invalidas conta só
          os ilegíveis, e sum, min e max ignoram o ilegível em vez de tratá-lo como 0.00; o teste prova
          que o ilegível foi EXCLUÍDO, nunca comparando totais, porque preencher com 0.00 não muda a soma,
          não muda max e não muda min — min já é 0.00 na fonte — e passaria despercebido pelos três
      - id: B-2
        given: um contexto decimal de precisão baixa, valores em empate exato, e a alternativa meio-para-cima
        when: o total é calculado
        then: o resultado é o de HALF_EVEN a duas casas — comparado contra o valor que HALF_UP produziria,
          e RECUSANDO-o; declarar um modo não basta, o teste falha se a implementação usar meio-para-cima.
          A perda por precisão baixa também é acusada, e arredondar por campo difere de arredondar no
          total
      evals:
      - id: eval_1
        description: Float recusado; dois de contagem e três monetários; ilegível excluído, não zerado
        bash: pytest -q tests/test_agregacao.py -k "recusa_float or cinco_controles or ilegivel_excluido_nao_zerado"
        verifies:
        - B-1
      - id: eval_2
        description: HALF_EVEN recusa o valor que HALF_UP daria; precisão e granularidade
        bash: pytest -q tests/test_agregacao.py -k "recusa_half_up or precisao_declarada or granularidade"
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
---
# Agregação monetária

Separa a soma exata da comparação contra a âncora.

## Responsibility

Somar o valor líquido com precisão declarada e agrupar pelo código.

## Independent proof

Float é recusado na entrada; agrupar por descrição produz contagem diferente de agrupar por código.

## Rejected alternatives

- **Usar float e arredondar no final** — 0.1 + 0.2 != 0.3 em binário; o centavo some sem nada acusar.
- **Agrupar por descricao_especie** — 51 códigos colapsam em 40 descrições; quatro espécies virariam uma linha com o total continuando a bater.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
