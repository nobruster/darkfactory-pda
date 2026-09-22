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
- contrato validado
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
    given: um valor de ponto flutuante em campo monetário, e um lote com registros ilegíveis misturados
      aos válidos
    when: o agregado é calculado
    then: o float é recusado com erro explícito; os cinco controles são DOIS de contagem e TRÊS monetários,
      e só sum_vl_liquido é soma — count_linhas conta todo registro lido, linhas_invalidas conta só os
      ilegíveis, e sum, min e max ignoram o ilegível em vez de tratá-lo como 0.00; o teste prova que o
      ilegível foi EXCLUÍDO, nunca comparando totais, porque preencher com 0.00 não muda a soma, não muda
      max e não muda min — min já é 0.00 na fonte — e passaria despercebido pelos três. No limite em que
      NENHUM registro é legível, min e max não têm valor e o agregado os marca AUSENTES, com sum=0.00
      e a contagem de inválidos igual à de lidos — zero inventaria extremos que não existem, e levantar
      exceção decidiria por conta própria que defeito de fonte interrompe o processamento, coisa que nem
      a tech-spec nem o juízo pediram; a ausência é representada e atravessa a fronteira e a evidência,
      que já marcam campo não percorrido como ausente
  - id: B-2
    given: um contexto decimal de precisão baixa, valores em empate exato, e a alternativa meio-para-cima
    when: o total é calculado
    then: o resultado é o de HALF_EVEN a duas casas — comparado contra o valor que HALF_UP produziria,
      e RECUSANDO-o; declarar um modo não basta, o teste falha se a implementação usar meio-para-cima.
      O contexto do agregador é PRÓPRIO e COMPLETO como o da leitura — precisão, arredondamento, Emax,
      Emin e traps declarados, com teste sob global adverso nos três eixos; declarar só precisão e modo
      deixaria uma biblioteca externa transformar execução válida em ERRO, e a exigência de contexto completo
      escrita só na leitura protege o mapa de referência, não quem soma. A perda por precisão baixa também
      é acusada, e arredondar por campo difere de arredondar no total. E a SAÍDA do agregador preserva
      os códigos distintos — tantos quantos a competência tiver, conferidos contra a cardinalidade ancorada
      no contrato e NÃO contra os 51 do ADR 0004, que foram medidos em ~3 milhões de linhas; na competência
      inteira são 65, e fixar 51 recusaria o arquivo correto. Cada VALOR por código é conferido contra
      os totais por código da leitura, não só a chave presente — um agregador que somasse por descrição,
      atribuísse o total ao primeiro código e emitisse zero nos demais conservaria todas as chaves e todos
      os controles globais, e a demonstração de que descrição e código têm cardinalidades diferentes continuaria
      verdadeira; se esse agregador fornecesse a referência da fronteira, o defeito contaminaria a conferência
      também
  evals:
  - id: eval_1
    description: Float recusado; ilegível excluído e não zerado; nenhum legível marca extremos ausentes
    bash: pytest -q tests/test_agregacao.py -k "recusa_float or ilegivel_excluido_nao_zerado or nenhum_legivel_extremos_ausentes"
    verifies:
    - B-1
  - id: eval_2
    description: HALF_EVEN recusa o valor que HALF_UP daria; precisão e granularidade
    bash: pytest -q tests/test_agregacao.py -k "recusa_half_up or precisao_declarada or granularidade"
    verifies:
    - B-2
  - id: eval_3
    description: A saída preserva a cardinalidade ancorada; chave por descrição faz falhar
    bash: pytest -q tests/test_agregacao.py -k "chave_e_codigo or cardinalidade_ancorada"
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
source_seam_sha256: 48bc5d548e4104c8c4eb395e93d8a683fb16b11f3de9f3388024836d09e6c05a
---
# O agregado é exato e a chave é o código

## Observable proof

Float recusado; precisão baixa acusa a perda; agrupar por descrição diverge de agrupar por código.

## Runnable leaves

- `T-20260921-agregacao-exata` — Somar com precisão declarada e agrupar pelo código: Float recusado na entrada; os cinco controles saem nomeados; agrupar por descrição diverge de agrupar por código.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
