> Projetado de `LEG-GOLD-RECONCILIA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `2aab0eb4d7462ed9fd047b626c4bd23d41960285c70e7c9668ae9f28094c6e29`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-GOLD-RECONCILIA
seam_id: SEAM-GOLD
swimlane_id: LANE-GOLD
observable_state: Gold só publica quando reconcilia com a âncora
proof: A soma das linhas agregadas reproduz a âncora ao centavo; um centavo de diferença devolve DIVERGE.
requires:
- silver classificado
- totais por código de Silver
produces:
- gold reconciliado
tasks:
- id: T-20260922-gold-reconcilia-ancora
  title: Agregar por código e reconciliar com a âncora
  goal: Fazer o agregado provar que fecha, em vez de afirmar.
  done_condition: A soma das linhas de Gold é igual à âncora ao centavo, com arredondamento único no total.
  effort: S
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  depends_on:
  - T-20260922-silver-classifica-colapso
  touches_paths: []
  creates_paths:
  - src/medalhao/gold.py
  - tests/test_gold.py
  behavior:
  - id: B-1
    given: o Silver classificado e o contrato, com a política decimal declarada — HALF_EVEN, escala 2,
      e a precisão DERIVADA conforme o ADR 0009, que nesta competência dá 14
    when: Gold agrega por código
    then: 'o arredondamento acontece UMA VEZ, sobre o total, como o ADR 0003 exige, na camada que o 0007
      e o 0009 preservaram — arredondar cada código antes de somar dá resultado diferente, e a diferença
      é sistemática, não ruído — 2,345 + 2,345 dá 4,68 por campo e 4,69 no total, ambos meio-para-par.
      O modo é HALF_EVEN, decidido pelo ADR 0003 e preservado pelo 0009, lido do CONTRATO, nunca escolhido
      aqui, porque meio-para-cima empurra todo empate na mesma direção e vira tendência em volume. A precisão
      é a declarada e o contexto é CONSTRUÍDO DO ZERO — localcontext(Context(prec, rounding, traps=[],
      Emax, Emin)) — o contexto INTEIRO declarado — as TRAPS são declaradas, não deixadas por conta do
      construtor. localcontext() sozinho COPIA o contexto global e herda as traps junto; e Context(prec,
      rounding) sem declarar traps preenche o que foi omitido a partir de DefaultContext, que é IGUALMENTE
      mutável, então uma biblioteca que ligue DefaultContext.traps[Inexact] derruba também essa construção.
      O que não se declara, se herda: com traps[Inexact] ligada por qualquer biblioteca importada, Decimal(''2.345'').quantize(Decimal(''.01''))
      LEVANTA Inexact dentro de um localcontext que declarou prec e rounding, e o arredondamento que o
      contrato PERMITE encerra a operação. O ADR 0006 diz que a precisão é declarada e não herdada; as
      traps são herdadas do mesmo jeito, e declarar prec e rounding não basta. Depois de agregar, a soma
      das linhas de Gold é RECONCILIADA com a âncora do contrato e a igualdade é exata ao centavo. Soma
      e cardinalidade NÃO BASTAM: uma redistribuição compensada entre códigos preserva as duas e troca
      os valores de lugar — {''01'': 10.00, ''03'': 20.00} e {''01'': 11.00, ''03'': 19.00} têm a mesma
      soma e as mesmas chaves, e acrescentar os outros 63 códigos idênticos aos dois mantém o contraexemplo
      com os 65. Por isso o MAPA total_por_codigo de Gold é comparado, código a código, contra o mapa
      que a camada anterior produziu, em soma EXATA não quantizada; com um mapa só, deslocar valor entre
      códigos seria aprovado por comparação consigo mesmo; Gold que não reconcilia devolve DIVERGE e NÃO
      publica, porque um agregado publicado sem reconciliar é exatamente o que a âncora existe para impedir.
      A reconciliação é recalculada a partir das linhas CANDIDATAS — materializadas em local privado,
      jamais no caminho que os consumidores leem — e não herdada de Bronze, senão Gold provaria a conta
      de outra camada. A publicação é um passo POSTERIOR e condicionado ao veredito, e o veredito CONSOME
      a marca PROCEDENCIA_NAO_VINCULADA que Bronze emite e Silver preserva — Gold recusa publicar sob
      ela, e a recusa tem eval próprio, senão cada camada cumpre o seu e a marca se perde na transformação:
      se as candidatas fossem escritas no destino para depois serem relidas, o dado divergente já teria
      ficado exposto antes de qualquer veredito, e remover depois não desfaz a exposição. Um teste que
      confira só o resultado final ou a ausência de arquivos ao término não vê isso — o eval observa que
      o caminho de destino permanece inalterado DURANTE a reconciliação. E a publicação em si é uma transição
      INDIVISÍVEL de visibilidade: o conjunto publicado é exatamente o conjunto reconciliado, tudo ou
      nada. Copiar vários arquivos expondo-os à medida que chegam deixaria um consumidor lendo parte das
      candidatas, ou misturadas com as da execução anterior, com a reconciliação correta e o total lido
      por ninguém aprovado — e uma interrupção no meio congela esse estado. Publicação interrompida deixa
      o destino como estava antes'
  - id: B-2
    given: um Silver cujo total não reproduz a âncora, ou uma competência sem âncora no contrato
    when: Gold agrega
    then: devolve DIVERGE quando o total não bate e NAO_MEDIDO quando não há âncora, dois estados distintos
      que nunca colapsam num só — sem âncora não é divergência, é ausência de referencial, e tratá-los
      igual faria a fábrica parecer que mediu quando não tinha contra o que medir. Nenhum dos dois publica,
      o motivo sai nomeado, e cada diferença recebe EXATAMENTE UMA das seis classificações da R-6 — inclusive
      a introduzida DEPOIS de Bronze, que é justamente a que nenhuma camada anterior viu. Devolver só
      estado e motivo cumpriria este plano e violaria a especificação; diferença que Gold não saiba classificar
      recebe UNRESOLVED, que bloqueia; a contagem de códigos de Gold é conferida contra os 65 do contrato,
      e o GRÃO das linhas publicadas é UMA por código — reagrupar candidatas para construir o mapa esconderia
      código duplicado no resultado materializado, já que ('01', 30.00) e o par ('01', 10.00) mais ('01',
      20.00) produzem o mesmo mapa e a mesma contagem de códigos distintos; a prova é sobre as linhas
      EFETIVAMENTE publicadas, não sobre o mapa derivado delas, porque um agregado com menos códigos que
      a fonte pode somar o mesmo total e ainda assim ter perdido uma categoria inteira
  evals:
  - id: eval_1
    description: Arredondamento único, precisão declarada, e recusa sob procedência não vinculada
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'n=$(python3 -m pytest --collect-only
      -q tests/test_gold.py -k "arredonda_uma_vez or half_even_do_contrato or nao_arredonda_por_campo
      or traps_declaradas or recusa_sob_procedencia_nao_vinculada" 2>/dev/null | grep -c "::"); [ "$n"
      -lt 5 ] && { echo "EVAL=COLETOU_${n}_DE_5"; exit 1; }; python3 -m pytest -q tests/test_gold.py -k
      "arredonda_uma_vez or half_even_do_contrato or nao_arredonda_por_campo or traps_declaradas or recusa_sob_procedencia_nao_vinculada"'
    verifies:
    - B-1
  - id: eval_2
    description: Reconcilia recalculando, compara o mapa por código e confere os 65
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'n=$(python3 -m pytest --collect-only
      -q tests/test_gold.py -k "reconcilia_recalculando or mapa_por_codigo or redistribuicao_compensada
      or contagem_de_codigos or uma_linha_por_codigo" 2>/dev/null | grep -c "::"); [ "$n" -lt 5 ] && {
      echo "EVAL=COLETOU_${n}_DE_5"; exit 1; }; python3 -m pytest -q tests/test_gold.py -k "reconcilia_recalculando
      or mapa_por_codigo or redistribuicao_compensada or contagem_de_codigos or uma_linha_por_codigo"'
    verifies:
    - B-1
    - B-2
  - id: eval_3
    description: DIVERGE e NAO_MEDIDO são estados distintos e nenhum publica
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'n=$(python3 -m pytest --collect-only
      -q tests/test_gold.py -k "diverge_nao_publica or sem_ancora_nao_medido or destino_inalterado_durante
      or classifica_diferenca_das_seis" 2>/dev/null | grep -c "::"); [ "$n" -lt 4 ] && { echo "EVAL=COLETOU_${n}_DE_4";
      exit 1; }; python3 -m pytest -q tests/test_gold.py -k "diverge_nao_publica or sem_ancora_nao_medido
      or destino_inalterado_durante or classifica_diferenca_das_seis"'
    verifies:
    - B-2
  anti_patterns:
  - action: construir o contexto decimal sem declarar traps, Emax e Emin
    reason: localcontext() copia o global e Context() preenche o omitido do DefaultContext, os dois mutáveis;
      com Emax baixo a âncora vira Infinity e traps=[] silencia o Overflow que denunciaria
    instead: Context(prec=..., rounding=..., traps=[], Emax=..., Emin=...) — o contexto inteiro
  - action: provar a agregação só com a soma total e a contagem de códigos
    reason: 'uma redistribuição compensada entre códigos preserva as duas e troca os valores de lugar
      — contraexemplo executado com {''01'': 10.00, ''03'': 20.00} contra {''01'': 11.00, ''03'': 19.00}'
    instead: comparar o mapa total_por_codigo código a código contra o da camada anterior, em soma exata
      não quantizada
  - action: tratar falta de âncora como divergência
    reason: ausência de referencial vira medição com resultado ruim, e a fábrica parece ter medido
    instead: devolver NAO_MEDIDO, distinto de DIVERGE
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  rollback: Remover a camada Gold e seus testes.
  observability: agregados recusados por não reconciliar
source_seam_sha256: 639d23d78838a8e8e129e6653407b0a84abed92954ed6b87208c64673effb0b7
---
# Gold só publica quando reconcilia com a âncora

## Observable proof

A soma das linhas agregadas reproduz a âncora ao centavo; um centavo de diferença devolve DIVERGE.

## Runnable leaves

- `T-20260922-gold-reconcilia-ancora` — Agregar por código e reconciliar com a âncora: A soma das linhas de Gold é igual à âncora ao centavo, com arredondamento único no total.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
