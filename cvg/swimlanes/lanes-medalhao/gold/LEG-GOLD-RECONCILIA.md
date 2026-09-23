> Projetado de `LEG-GOLD-RECONCILIA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `93f835d7ba6c82f4c231014e31f11543cd4d016370b376683903a24242d9005f`

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
    then: 'No caminho Spark, o Context do Python NÃO governa a aritmética — medido: com prec=3 e Emax=5
      no Python, o Spark somou exato, e sum() promove decimal(14,2) a decimal(24,2) por conta própria.
      O que governa é o DecimalType do acumulador, declarado a partir da politica_decimal do contrato,
      e a sessão roda com spark.sql.ansi.enabled=true DECLARADO: em modo não-ANSI, o estouro do acumulador
      devolve NULL sem erro, que é o Infinity da Regra 5 com outro nome. O Context(prec, rounding, traps=[],
      Emax, Emin) vale para o que roda em Python fora do motor. A agregação por código e a comparação
      do mapa rodam NO MOTOR, sem coletar as linhas de Silver — só as 65 linhas agregadas e os totais
      saem do motor. o arredondamento acontece UMA VEZ, sobre o total, como o ADR 0003 exige, na camada
      que o 0007 e o 0009 preservaram — arredondar cada código antes de somar dá resultado diferente,
      e a diferença é sistemática, não ruído — 2,345 + 2,345 dá 4,68 por campo e 4,69 no total, ambos
      meio-para-par. O modo é HALF_EVEN, decidido pelo ADR 0003 e preservado pelo 0009, lido do CONTRATO,
      nunca escolhido aqui, porque meio-para-cima empurra todo empate na mesma direção e vira tendência
      em volume. A precisão é a declarada e o contexto é CONSTRUÍDO DO ZERO — localcontext(Context(prec,
      rounding, traps=[], Emax, Emin)) — o contexto INTEIRO declarado, e os cinco valores vêm da politica_decimal
      do CONTRATO, que agora declara emax 999999 e emin -999999 com aprovador e data. Não são escolha
      de quem implementa: são o limite que NÃO INTERFERE, declarado para que nenhuma biblioteca o imponha
      — as TRAPS são declaradas, não deixadas por conta do construtor. localcontext() sozinho COPIA o
      contexto global e herda as traps junto; e Context(prec, rounding) sem declarar traps preenche o
      que foi omitido a partir de DefaultContext, que é IGUALMENTE mutável, então uma biblioteca que ligue
      DefaultContext.traps[Inexact] derruba também essa construção. O que não se declara, se herda: com
      traps[Inexact] ligada por qualquer biblioteca importada, Decimal(''2.345'').quantize(Decimal(''.01''))
      LEVANTA Inexact dentro de um localcontext que declarou prec e rounding, e o arredondamento que o
      contrato PERMITE encerra a operação. O ADR 0006 diz que a precisão é declarada e não herdada; as
      traps são herdadas do mesmo jeito, e declarar prec e rounding não basta. Gold só agrega sobre ''silver
      classificado'' com estado INTEGRO — BLOQUEADO, DIVERGE, NAO_MEDIDO e ERRO_LEITURA param a cadeia
      com o estado propagado sem tradução, pelo mesmo motivo que vale em Silver: estado negativo propagado
      para e cadeia para. Antes de reconciliar, a COMPETÊNCIA que Silver carrega é comparada com a do
      contrato, e divergir é DIVERGE — a R-1 exige que a âncora exista PARA AQUELA competência, não que
      contenha números iguais, e um Silver de outra competência com os mesmos valores por código satisfaria
      soma, mapa e cardinalidade contra o contrato errado. A competência atravessa Bronze e Silver sem
      ser descartada, como a marca de procedência. Depois de agregar, a soma das linhas de Gold é RECONCILIADA
      com a âncora do contrato e a igualdade é exata ao centavo. Soma e cardinalidade NÃO BASTAM: uma
      redistribuição compensada entre códigos preserva as duas e troca os valores de lugar — {''01'':
      10.00, ''03'': 20.00} e {''01'': 11.00, ''03'': 19.00} têm a mesma soma e as mesmas chaves, e acrescentar
      os outros 63 códigos idênticos aos dois mantém o contraexemplo com os 65. Por isso o MAPA total_por_codigo
      de Gold é comparado, código a código, contra o mapa que a camada anterior produziu, em soma EXATA
      não quantizada; com um mapa só, deslocar valor entre códigos seria aprovado por comparação consigo
      mesmo; Gold que não reconcilia devolve DIVERGE e NÃO publica, porque um agregado publicado sem reconciliar
      é exatamente o que a âncora existe para impedir. A reconciliação é recalculada a partir das linhas
      CANDIDATAS — materializadas em local privado, jamais no caminho que os consumidores leem — e não
      herdada de Bronze, senão Gold provaria a conta de outra camada. A capacidade ''gold reconciliado''
      tem FORMA declarada, como as de Bronze e Silver, e COLUNAS NOMEADAS — especie_codigo, especie_descricao,
      vl_liquido_total e competencia, uma linha por código. Gold consome ''silver classificado'' pelos
      nomes que Silver declara e prova que consome a saída REAL de Silver, produzida pelo módulo de Silver,
      não uma fixture. Conteúdo: o estado, as linhas agregadas — uma por código — o mapa total_por_codigo
      em Decimal exato, o veredito da reconciliação, a competência e as marcas de limitação. A reconciliação
      de Gold é a conferência DO PRODUTOR, e não basta para publicar: o ADR 0006 preserva a separação
      de motores — Spark grava, Python puro confere — e Gold reconciliando sobre o próprio Spark é o produtor
      conferindo a si mesmo. Por isso Gold EMITE O ENVELOPE da SEAM-FRONTEIRA, e o campo defeitos dele
      carrega SOMENTE defeitos de LINHA — que, no ÚNICO caminho que emite envelope, é VAZIO: linhas_invalidas
      é um dos cinco controles e está ancorado em zero, Bronze só fica INTEGRO com zero defeitos de domínio,
      e o envelope só é emitido com a cadeia inteira INTEGRO. Não é preciso, portanto, reconstruir a posição
      de linha do CSV, que o Parquet não carrega. Se uma competência futura ancorar linhas inválidas,
      o lago terá de carregar o número da linha do CSV, e isso é mudança no produtor, que está sem Task-Spec
      (Regra 11) — limitação declarada, não escondida. Cada defeito, quando houver, vai como — cada um
      como (tipo, valor_original, posicao), com posicao INTEIRA, o número da linha —, porque o validador
      os compara por multiconjunto exato contra os defeitos que a leitura observou, e colapso de identidade
      fica FORA dali: a leitura o guarda num campo separado, e o próprio validador registra que identidade
      colapsada não entra nessa conta (ADR 0008). O envelope sai com os controles de DETALHE e o sha256
      que recebeu de Bronze através de Silver — jamais recalculando count, min e max sobre as próprias
      65 linhas agregadas, que não são os controles da âncora, conforme o ENVELOPE_SCHEMA declarado em
      src/pda/envelope.py, e a publicação é decidida pelo ORQUESTRADOR já selado da primeira descida,
      nunca por uma reimplementação dele dentro de Gold: orquestracao.conduzir(diretorio_evidencia, competencia_solicitada,
      caminho_contrato, executar_leitura), em que executar_leitura é o ponto de injeção, e é DENTRO dele
      que roda a cadeia INTEIRA — Bronze, Silver e Gold — e que Gold chama envelope.validar_envelope(envelope,
      capacidade_leitura, contrato) ANTES de montar os insumos, porque, MEDIDO, conduzir() NÃO valida
      o envelope: ele só chama julgar() sobre insumos.agregado. Recusa do envelope, a marca PROCEDENCIA_NAO_VINCULADA
      — que não cabe no ENVELOPE_SCHEMA nem em InsumosExecucao, e por isso é decidida AQUI, antes dos
      insumos, mesmo com as camadas INTEGRO —, e qualquer camada que PARE a cadeia — Bronze ou Silver
      fora de INTEGRO, inclusive Silver sem o mapa aprovado —, sobe como exceção cuja MENSAGEM é o diagnóstico
      estruturado serializado em JSON — camada, estado, os controles que divergiram com o valor observado
      e o ancorado, e as classificações —, porque, MEDIDO, o pacote guarda de evento_falha apenas {tipo,
      mensagem}: uma mensagem ''Bronze DIVERGE'' descartaria tudo o que permite reconstruir a recusa.
      O veredito EXTERNO é o do orquestrador — ERRO, sem autorização de publicar —, e ''sem tradução''
      significa que o estado do medalhão é preservado VERBATIM dentro do pacote, não re-rotulado. conduzir
      a captura, grava o pacote com evento_falha e devolve um Desfecho sem autorização de publicar. Assim
      TODO caminho deixa evidência, e não só o que chega à agregação. Pelo ponto de injeção Gold entrega
      um InsumosExecucao que PAREIA a leitura PRÓPRIA do juiz sobre o CSV com o envelope de Gold — hash_ancorado,
      hash_observado pela leitura, hash_declarado no envelope, defeitos_leitura contra defeitos_envelope,
      totais_leitura contra totais_envelope. conduzir carrega o contrato, julga, grava o pacote de evidência
      em QUALQUER desfecho e devolve um Desfecho; Gold publica se e somente se Desfecho.autorizado_publicar
      for verdadeiro E Desfecho.caminho_pacote existir em disco. Não se compara string ''ACEITO'' contra
      o retorno de julgar(), que devolve Veredito(aceito, classificacoes), nem contra rederivar_veredito(),
      que devolve o par (veredito, causa) — descrever essas assinaturas em prosa errou um detalhe a cada
      rodada, e o orquestrador já as fala. Gold importa o orquestrador e o juiz, jamais os edita, e nenhum
      dos dois importa Gold. A publicação é um passo POSTERIOR e condicionado a autorizado_publicar, e
      o veredito CONSOME a marca PROCEDENCIA_NAO_VINCULADA que Bronze emite e Silver preserva — Gold recusa
      publicar sob ela, e a recusa tem eval próprio, senão cada camada cumpre o seu e a marca se perde
      na transformação: se as candidatas fossem escritas no destino para depois serem relidas, o dado
      divergente já teria ficado exposto antes de qualquer veredito, e remover depois não desfaz a exposição.
      Um teste que confira só o resultado final ou a ausência de arquivos ao término não vê isso — o eval
      observa que o caminho de destino permanece inalterado DURANTE a reconciliação. E a publicação em
      si é uma transição INDIVISÍVEL de visibilidade: o conjunto publicado é exatamente o conjunto reconciliado,
      tudo ou nada. Copiar vários arquivos expondo-os à medida que chegam deixaria um consumidor lendo
      parte das candidatas, ou misturadas com as da execução anterior, com a reconciliação correta e o
      total lido por ninguém aprovado — e uma interrupção no meio congela esse estado. Publicação interrompida
      deixa o destino como estava antes'
  - id: B-2
    given: um Silver cujo total não reproduz a âncora, ou uma competência sem âncora no contrato
    when: Gold agrega
    then: 'devolve DIVERGE quando o total não bate e NAO_MEDIDO quando não há âncora, dois estados distintos
      que nunca colapsam num só — sem âncora não é divergência, é ausência de referencial, e tratá-los
      igual faria a fábrica parecer que mediu quando não tinha contra o que medir. O orçamento da R-9
      é MEDIDO, não presumido: do início da leitura de Bronze ao VEREDITO da cadeia, sobre a partição
      real de 41.572.553 linhas, a cadeia termina em até 20 minutos — e o veredito é o primeiro estado
      que PARA a cadeia, qualquer que seja. Enquanto o mapa código→descrição não estiver aprovado no contrato,
      a cadeia real para em Silver com NAO_MEDIDO, e é até ESSE veredito que se mede: exigir que Gold
      agregasse a competência real antes da aprovação tornaria o eval impossível por construção, e a duração
      sai no veredito. A tech-spec registra esse número como ''não medido'' — meta declarada sem medição
      é a Regra 9, e executar no motor não garante o orçamento: uma execução distribuída pode preservar
      todas as propriedades funcionais e ainda estourá-lo. Nenhum dos dois publica, o motivo sai nomeado,
      e cada diferença recebe EXATAMENTE UMA das seis classificações da R-6 — inclusive a introduzida
      DEPOIS de Bronze, que é justamente a que nenhuma camada anterior viu. Devolver só estado e motivo
      cumpriria este plano e violaria a especificação; diferença que Gold não saiba classificar recebe
      UNRESOLVED, que bloqueia; a contagem de códigos de Gold é conferida contra os 65 do contrato, e
      a especie_descricao publicada de cada código é conferida contra a descrição ORIGINAL que Silver
      entregou para aquele código — trocar as descrições de dois códigos não colapsados mantém códigos,
      valores, soma, competência e cardinalidade, e passaria em todas as outras provas. O GRÃO das linhas
      publicadas é UMA por código — reagrupar candidatas para construir o mapa esconderia código duplicado
      no resultado materializado, já que (''01'', 30.00) e o par (''01'', 10.00) mais (''01'', 20.00)
      produzem o mesmo mapa e a mesma contagem de códigos distintos; a prova é sobre as linhas EFETIVAMENTE
      publicadas, não sobre o mapa derivado delas, porque um agregado com menos códigos que a fonte pode
      somar o mesmo total e ainda assim ter perdido uma categoria inteira'
  evals:
  - id: eval_1
    description: Arredondamento único, precisão declarada, e recusa sob procedência não vinculada
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in arredonda_uma_vez half_even_do_contrato
      nao_arredonda_por_campo traps_declaradas recusa_sob_procedencia_nao_vinculada ansi_declarado_estouro_nao_vira_nulo;
      do python3 -m pytest --collect-only -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" ||
      { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold.py -k "arredonda_uma_vez
      or half_even_do_contrato or nao_arredonda_por_campo or traps_declaradas or recusa_sob_procedencia_nao_vinculada
      or ansi_declarado_estouro_nao_vira_nulo"'
    verifies:
    - B-1
  - id: eval_2
    description: Reconcilia recalculando, compara o mapa por código e confere os 65
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reconcilia_recalculando
      mapa_por_codigo redistribuicao_compensada contagem_de_codigos competencia_bate_com_o_contrato uma_linha_por_codigo
      recusa_silver_nao_integro consome_saida_real_de_silver publica_so_com_autorizado_publicar descricao_publicada_bate_com_a_original
      publica_so_com_pacote_em_disco envelope_so_defeitos_de_linha envelope_validado_antes_dos_insumos
      envelope_positivo_sem_defeitos_de_linha; do python3 -m pytest --collect-only -q tests/test_gold.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_gold.py -k "reconcilia_recalculando or mapa_por_codigo or redistribuicao_compensada
      or contagem_de_codigos or competencia_bate_com_o_contrato or uma_linha_por_codigo or recusa_silver_nao_integro
      or consome_saida_real_de_silver or publica_so_com_autorizado_publicar or descricao_publicada_bate_com_a_original
      or publica_so_com_pacote_em_disco or envelope_so_defeitos_de_linha or envelope_validado_antes_dos_insumos
      or envelope_positivo_sem_defeitos_de_linha"'
    verifies:
    - B-1
    - B-2
  - id: eval_3
    description: DIVERGE e NAO_MEDIDO são estados distintos e nenhum publica
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in diverge_nao_publica
      sem_ancora_nao_medido destino_inalterado_durante classifica_diferenca_das_seis orcamento_leitura_ao_veredito_medido
      parada_antecipada_grava_evidencia diagnostico_estruturado_no_pacote marca_de_procedencia_vira_evidencia;
      do python3 -m pytest --collect-only -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" ||
      { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold.py -k "diverge_nao_publica
      or sem_ancora_nao_medido or destino_inalterado_durante or classifica_diferenca_das_seis or orcamento_leitura_ao_veredito_medido
      or parada_antecipada_grava_evidencia or diagnostico_estruturado_no_pacote or marca_de_procedencia_vira_evidencia"'
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
source_seam_sha256: 209793270e3e5fbe2440235b560a50ed9cc86c385460ccc9b575101b75a3e92a
---
# Gold só publica quando reconcilia com a âncora

## Observable proof

A soma das linhas agregadas reproduz a âncora ao centavo; um centavo de diferença devolve DIVERGE.

## Runnable leaves

- `T-20260922-gold-reconcilia-ancora` — Agregar por código e reconciliar com a âncora: A soma das linhas de Gold é igual à âncora ao centavo, com arredondamento único no total.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
