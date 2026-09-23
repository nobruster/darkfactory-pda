> Projetado de `LEG-BRONZE-REPRODUZ-ANCORA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `385521028703a598cca9f778a591c08f2d944ca0baa9ed4f95857d5ae1ac0c83`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-BRONZE-REPRODUZ-ANCORA
seam_id: SEAM-BRONZE
swimlane_id: LANE-BRONZE
observable_state: Bronze só existe quando reproduz a âncora do contrato
proof: A partição lida reproduz os cinco controles ancorados; ausente ou vazia devolve NAO_MEDIDO, e medida-e-divergente
  devolve DIVERGE — estados distintos, nunca colapsados.
requires: []
produces:
- bronze conferido
- totais por código de Bronze
tasks:
- id: T-20260922-bronze-confere-ancora
  title: Ler a partição do lago e conferi-la contra a âncora
  goal: Fazer a camada recusar nascer sobre dado que não bate.
  done_condition: Os cinco controles da partição real batem com o contrato. Partição AUSENTE ou VAZIA
    devolve NAO_MEDIDO; partição MEDIDA que diverge em qualquer controle devolve DIVERGE — os dois são
    estados distintos e nenhum escreve camada, porque confundir ausência de medição com reprovação torna
    instável a interface que Silver consome. Os evals rodam DENTRO do contêiner pda-spark, que tem pytest
    e pyspark; montar esse ambiente é pré-requisito do HOST — infra/preparar-spark.sh — e NÃO é trabalho
    desta tarefa, porque o contrato de runtime nega rede ao agente e instalar qualquer coisa seria impossível
    por construção.
  effort: S
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  depends_on: []
  touches_paths: []
  creates_paths:
  - src/medalhao/bronze.py
  - tests/test_bronze.py
  behavior:
  - id: B-1
    given: uma partição do lago e o contrato da competência, com a âncora de linhas e de soma medidas
      na fonte
    when: Bronze lê a partição
    then: 'No caminho Spark, o Context do Python NÃO governa a aritmética — medido: com prec=3 e Emax=5
      no Python, o Spark somou exato, e sum() promove decimal(14,2) a decimal(24,2) por conta própria.
      O que governa é o DecimalType do acumulador, declarado a partir da politica_decimal do contrato,
      e a sessão roda com spark.sql.ansi.enabled=true DECLARADO: em modo não-ANSI, o estouro do acumulador
      devolve NULL sem erro, que é o Infinity da Regra 5 com outro nome. O Context(prec, rounding, traps=[],
      Emax, Emin) vale para o que roda em Python fora do motor. Os cinco controles, o mapa por código
      e o fechamento rodam NO MOTOR, sobre as 41.572.553 linhas, sem coletar — só os agregados saem do
      motor, e as linhas entregues a Silver são uma relação materializada, não uma coleção em memória.
      a contagem e a soma são recalculadas SOBRE A PARTIÇÃO, nunca sobre a união das partições — um agregado
      sem GROUP BY na coluna de partição não mede partição nenhuma, e foi assim que a leitura da união
      deu 41.622.553 contra a âncora de 41.572.553 e uma contaminação inexistente foi reportada, quando
      a partição real batia exato e as 50.000 linhas estavam em competencia=fatia-teste, isolada. A soma
      é feita com a precisão DECLARADA no contrato, jamais herdada do contexto global, como o ADR 0009
      exige — e o contexto é construído INTEIRO a partir da politica_decimal do contrato, Context(prec,
      rounding, traps=[], Emax, Emin), porque declarar só a precisão deixa traps e limites de expoente
      virem do DefaultContext, que é mutável: com Emax baixo a soma vira Infinity e traps=[] silencia
      o Overflow que denunciaria, porque qualquer biblioteca importada pode alterar o contexto e o acumulador
      passaria a perder centavos sem que uma linha deste código mude. Os CINCO controles da âncora são
      comparados INDIVIDUALMENTE, como a R-5 da tech-spec exige — count_linhas, sum_vl_liquido, min_vl_liquido,
      max_vl_liquido e linhas_invalidas. Contagem e soma sozinhas não bastam, e não bastam nem juntas:
      uma alteração COMPENSADA entre duas linhas preserva as duas e ainda assim empurra o máximo acima
      dos 183.725,76 ancorados, com todos os valores finitos, não negativos e na escala permitida. Silver
      preservaria a soma e Gold compararia soma e cardinalidade; nenhuma das três veria. Bronze PRODUZ
      o mapa total_por_codigo — soma exata não quantizada, por código — e ele é parte declarada de ''bronze
      conferido''. É a ORIGEM do mapa: quem lê o Parquet é quem sabe qual valor pertence a qual código,
      e uma camada posterior que o recalcule a partir dos mesmos bytes repetiria um erro de atribuição
      nos dois lados da comparação, aprovando-o. Cada controle que diverge é nomeado na saída, porque
      saber QUAL falhou é o que separa investigar de adivinhar — e cada diferença recebe EXATAMENTE UMA
      das seis classificações da R-6 (CONFIRMED_SOURCE_DEFECT, CONFIRMED_LEGACY_DEFECT, APPROVED_BEHAVIOR_CHANGE,
      MODERN_DEFECT, CONTRACT_AMBIGUITY, UNRESOLVED). DIVERGE é estado de MEDIÇÃO, não classificação:
      recusar a partição corretamente e entregar diagnóstico sem classificação deixaria a diferença sem
      dono. Diferença que a camada não saiba classificar recebe UNRESOLVED, que é uma das seis e BLOQUEIA
      — nunca fica em branco. O tipo monetário da ENTRADA é recusado se não for decimal — a R-4 manda
      recusar float, nunca convertê-lo, e converter apaga a evidência da entrada proibida: Decimal(str(1.25))
      devolve 1.25, finito, não negativo e na escala 2, satisfazendo todas as verificações de domínio
      enquanto a origem era um DOUBLE. A recusa é do TIPO declarado no esquema do Parquet, antes de ler
      valor algum. Só então a comparação monetária é entre Decimal e Decimal, e a igualdade é exata —
      tolerância aqui seria a Regra 3 pelo avesso, afrouxar o oráculo para a camada passar. Todo valor
      lido é conferido contra o domínio monetário do contrato antes de entrar no acumulador — finito,
      NÃO NEGATIVO e dentro da escala declarada. A não-negatividade não é preferência, e sim a premissa
      de soma MONOTÔNICA sob a qual o ADR 0009 deriva a precisão 14 — um valor negativo quebra a premissa
      e a perda de centavo passa a acontecer DURANTE a soma, onde a comparação final não a enxerga. Bronze
      lê Parquet, que não passa nem pela gramática do CSV nem pela fronteira do envelope, e por isso é
      uma TERCEIRA porta de entrada para valores; fechá-la é obrigação desta camada. Valor fora do domínio
      é defeito classificado com identidade, valor original e posição, nunca somado em silêncio. A procedência
      do arquivo que originou a partição é APRESENTADA a Bronze junto da leitura — hoje pelo pacote que
      a gravação emite, não por coluna do Parquet, porque MEDIDO em gravar_lago.py a partição tem três
      colunas mais a de partição e nenhuma é procedência; exigir que ela viesse do Parquet faria Bronze
      devolver NAO_MEDIDO na partição CORRETA, que é o defeito da Regra 9 pelo avesso. Quando apresentada,
      o hash_csv_sha256 é comparado com o ancorado e divergência é DIVERGE, porque reproduzir os dois
      controles não distingue o arquivo ancorado de outro com os mesmos totais, e a âncora vale para UM
      arquivo. Fazer a partição carregar a procedência é melhoria desejável e exige tarefa própria, por
      tocar em gravar_lago.py, que está sem Task-Spec (Regra 11) — enquanto não existir, a ausência do
      vínculo tem CONSEQUÊNCIA definida e propagada — ''bronze conferido'' sai marcado PROCEDENCIA_NAO_VINCULADA,
      Silver e Gold propagam a marca sem removê-la, e Gold NÃO PUBLICA sob ela. Registrar só uma ressalva
      deixaria a cadeia publicar partição diferente da ancorada, porque o hash correto num pacote sem
      vínculo verificável com a partição lida satisfaz a comparação textual e não prova nada. A capacidade
      ''bronze conferido'' tem FORMA declarada, não apenas nome: um objeto com estado (INTEGRO, DIVERGE,
      NAO_MEDIDO, ERRO_LEITURA), os cinco controles medidos, o mapa total_por_codigo em Decimal exato,
      as marcas de limitação como PROCEDENCIA_NAO_VINCULADA, a competência lida, e AS LINHAS CONFERIDAS,
      com os nomes de coluna MEDIDOS no lago — especie_codigo, especie_descricao, vl_liquido e competencia
      — que Silver consome pelos mesmos nomes, porque conteúdo sem nome deixa Bronze entregar codigo/descricao/valor
      e Silver esperar outra coisa, com as duas satisfazendo a descrição. Sem elas a capacidade é insuficiente:
      o multiconjunto de (código, valor) e a normalização de descrição não saem de agregado, e mandar
      Silver reler do lago introduziria uma SEGUNDA leitura cuja identidade com a conferida não está contratada
      — o mesmo motivo pelo qual Bronze recusa confiar no Parquet por tê-lo escrito — porque ''produces''
      com nome e sem forma deixa Silver e Bronze passarem nos próprios testes com fixtures locais e não
      encaixarem um no outro. Partição que diverge é DIVERGE, e Bronze não escreve nada'
  - id: B-2
    given: uma competência cuja partição não existe no lago, existe com zero linhas, ou existe e não está
      vazia mas NÃO tem âncora declarada no contrato
    when: Bronze lê a partição
    then: 'retorna NAO_MEDIDO como valor nos três casos — partição presente e não vazia SEM âncora é NAO_MEDIDO,
      não DIVERGE, porque sem referencial não há contra o que divergir, e tentar comparar contra controles
      ausentes falharia no acesso em vez de devolver veredito, sem escrever camada nenhuma e sem encerrar
      o processo; partição ausente e partição vazia são casos distintos e ambos NAO_MEDIDO, porque ler
      o lago e não encontrar nada não é o mesmo que medir e encontrar zero — a Regra 9 existe porque o
      segundo caminho é o que veste NAO_MEDIDO de MEDIDO. As outras partições do lago são nomeadas E CONTADAS
      na saída, e a soma das contagens por partição é conferida contra o total lido — nomear sem contar
      afirma isolação sem medi-la, e a lista de nomes continuaria idêntica se as linhas de uma partição
      tivessem migrado para outra. ERRO_LEITURA é o estado de quem NÃO CONSEGUIU medir — objeto ilegível,
      esquema inesperado, credencial ausente, listagem que falhou — e é distinto de NAO_MEDIDO, que é
      ter medido e não achar dado: não conseguir listar uma partição não prova que ela está ausente, e
      não conseguir ler um objeto não prova que ele tem zero linhas. Colapsar os dois faria a fábrica
      registrar ''não medido'' para um lago que nunca abriu. A PRECEDÊNCIA é declarada e não negociável:
      o estado da competência SOLICITADA decide primeiro. Ausente ou vazia devolve NAO_MEDIDO mesmo que
      o lago tenha outros problemas, porque não se reprova o que não se mediu. Partição presente SEM âncora
      é NAO_MEDIDO mesmo que o fechamento do lago diverja: sem referencial não há contra o que divergir,
      e o objeto órfão sai NOMEADO no diagnóstico sem mudar o estado. Só quando a competência existe,
      foi medida e TEM âncora é que o fechamento do lago entra no estado — e aí, se a soma das partições
      não fecha com o total, é DIVERGE, porque linha que não pertence a partição nenhuma é contaminação
      — e o total vem de um UNIVERSO INDEPENDENTE, a listagem dos objetos do lago, nunca da mesma leitura
      agrupada: somar contagens agrupadas pela própria relação lida é identidade, fecha sempre, inclusive
      somando o grupo nulo, e não veria arquivo que as DUAS leituras ignoraram. A CHAVE de partição é
      a declarada no contrato — ''competencia'' — e os objetos auxiliares que ele lista, como _SUCCESS,
      são ignorados no fechamento. A competência CONTRATADA não é a lista exaustiva de partições válidas:
      tratá-la assim reprovaria competencia=fatia-teste, que existe no lago e é legítima, e seria mais
      um gate recusando o correto; objeto fora delas, ou linha cuja chave de partição é nula, conta como
      não pertencente e faz o controle reprovar, e foi para vê-la que este controle existe'
  evals:
  - id: eval_1
    description: Os cinco controles comparados individualmente, e a partição medida isoladamente
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in cinco_controles alteracao_compensada
      isola_particao nao_soma_uniao precisao_declarada entrega_as_linhas_conferidas ansi_declarado_estouro_nao_vira_nulo;
      do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" ||
      { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k
      "cinco_controles or alteracao_compensada or isola_particao or nao_soma_uniao or precisao_declarada
      or entrega_as_linhas_conferidas or ansi_declarado_estouro_nao_vira_nulo"'
    verifies:
    - B-1
  - id: eval_2
    description: Ausente e vazia devolvem NAO_MEDIDO; medida e divergente devolve DIVERGE
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in particao_ausente particao_vazia
      presente_sem_ancora diverge_nao_e_nao_medido objeto_orfao_na_listagem erro_leitura_nao_e_nao_medido
      sem_ancora_vence_o_fechamento; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c"
      2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest
      -q tests/test_bronze.py -k "particao_ausente or particao_vazia or presente_sem_ancora or diverge_nao_e_nao_medido
      or objeto_orfao_na_listagem or erro_leitura_nao_e_nao_medido or sem_ancora_vence_o_fechamento"'
    verifies:
    - B-2
  - id: eval_3
    description: Float recusado na entrada, e toda diferença com uma das seis classificações
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in centavo_a_mais maximo_acima_do_ancorado
      recusa_float_na_entrada classificacao_das_seis recusa_valor_negativo recusa_valor_fora_da_escala
      recusa_hash_divergente emite_marca_sem_vinculo; do python3 -m pytest --collect-only -q tests/test_bronze.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_bronze.py -k "centavo_a_mais or maximo_acima_do_ancorado or recusa_float_na_entrada
      or classificacao_das_seis or recusa_valor_negativo or recusa_valor_fora_da_escala or recusa_hash_divergente
      or emite_marca_sem_vinculo"'
    verifies:
    - B-1
  anti_patterns:
  - action: conferir só contagem e soma, deixando min, max e linhas_invalidas de fora
    reason: a R-5 exige os cinco individualmente, e uma alteração compensada entre duas linhas preserva
      contagem e soma enquanto empurra o máximo acima do ancorado
    instead: comparar os cinco, nomeando na saída qual deles divergiu
  - action: aceitar diferença de centavos como arredondamento
    reason: afrouxar a tolerância é editar o oráculo pelo avesso
    instead: exigir igualdade exata entre Decimal e Decimal
  - action: pedir ao agente do loop que instale ou baixe qualquer coisa para montar o ambiente de eval
    reason: o contrato de runtime nega rede — net.egress False e policy.network deny — então a tarefa
      seria impossível por construção e queimaria o orçamento inteiro sem escrever um arquivo
    instead: preparar o ambiente fora do loop, em infra/preparar-spark.sh, e o eval apenas usá-lo
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  rollback: Remover o leitor Bronze e seus testes.
  observability: partições recusadas por controle divergente
source_seam_sha256: fe970e339a5576cbf4091a5d0c5925eec7b60563fcb94c6c39b1c1f55abb7df5
---
# Bronze só existe quando reproduz a âncora do contrato

## Observable proof

A partição lida reproduz os cinco controles ancorados; ausente ou vazia devolve NAO_MEDIDO, e medida-e-divergente devolve DIVERGE — estados distintos, nunca colapsados.

## Runnable leaves

- `T-20260922-bronze-confere-ancora` — Ler a partição do lago e conferi-la contra a âncora: Os cinco controles da partição real batem com o contrato. Partição AUSENTE ou VAZIA devolve NAO_MEDIDO; partição MEDIDA que diverge em qualquer controle devolve DIVERGE — os dois são estados distintos e nenhum escreve camada, porque confundir ausência de medição com reprovação torna instável a interface que Silver consome. Os evals rodam DENTRO do contêiner pda-spark, que tem pytest e pyspark; montar esse ambiente é pré-requisito do HOST — infra/preparar-spark.sh — e NÃO é trabalho desta tarefa, porque o contrato de runtime nega rede ao agente e instalar qualquer coisa seria impossível por construção.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
