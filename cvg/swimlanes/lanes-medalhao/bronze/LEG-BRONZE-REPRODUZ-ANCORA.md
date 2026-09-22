> Projetado de `LEG-BRONZE-REPRODUZ-ANCORA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `42a6d5a0cb7f7fa5ca2273a7dbc7554f542547d634bb79ef13bdd498b4ed479b`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-BRONZE-REPRODUZ-ANCORA
seam_id: SEAM-BRONZE
swimlane_id: LANE-BRONZE
observable_state: Bronze só existe quando reproduz a âncora do contrato
proof: A partição lida devolve as linhas e a soma ancoradas; partição ausente, vazia ou divergente devolve
  NAO_MEDIDO.
requires: []
produces:
- bronze conferido
tasks:
- id: T-20260922-bronze-confere-ancora
  title: Ler a partição do lago e conferi-la contra a âncora
  goal: Fazer a camada recusar nascer sobre dado que não bate.
  done_condition: 'Os dois controles da partição real batem com o contrato; qualquer outro caso devolve
    NAO_MEDIDO como valor. Os evals rodam num ambiente que tem AO MESMO TEMPO pytest e um leitor de Parquet
    — medido, hoje nenhum tem: o host não tem pyspark, pyarrow, pandas, duckdb nem java, e o contêiner
    pda-spark não tem pytest. Montar esse ambiente é parte desta tarefa, não pressuposto dela.'
  effort: S
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  - pyspark
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
    then: a contagem e a soma são recalculadas SOBRE A PARTIÇÃO, nunca sobre a união das partições — um
      agregado sem GROUP BY na coluna de partição não mede partição nenhuma, e foi assim que a leitura
      da união deu 41.622.553 contra a âncora de 41.572.553 e uma contaminação inexistente foi reportada,
      quando a partição real batia exato e as 50.000 linhas estavam em competencia=fatia-teste, isolada.
      A soma é feita com a precisão DECLARADA no contrato, jamais herdada do contexto global, como o ADR
      0009 exige, porque qualquer biblioteca importada pode alterar o contexto e o acumulador passaria
      a perder centavos sem que uma linha deste código mude. Os DOIS controles precisam bater — contagem
      sozinha aprovaria uma partição com o mesmo número de linhas e valores trocados, e soma sozinha aprovaria
      uma partição com linhas a mais que se cancelam. A comparação monetária é entre Decimal e Decimal,
      nunca float, e a igualdade é exata — tolerância aqui seria a Regra 3 pelo avesso, afrouxar o oráculo
      para a camada passar. Todo valor lido é conferido contra o domínio monetário do contrato antes de
      entrar no acumulador — finito, NÃO NEGATIVO e dentro da escala declarada. A não-negatividade não
      é preferência, e sim a premissa de soma MONOTÔNICA sob a qual o ADR 0009 deriva a precisão 14 —
      um valor negativo quebra a premissa e a perda de centavo passa a acontecer DURANTE a soma, onde
      a comparação final não a enxerga. Bronze lê Parquet, que não passa nem pela gramática do CSV nem
      pela fronteira do envelope, e por isso é uma TERCEIRA porta de entrada para valores; fechá-la é
      obrigação desta camada. Valor fora do domínio é defeito classificado com identidade, valor original
      e posição, nunca somado em silêncio. A procedência do arquivo que originou a partição é APRESENTADA
      a Bronze junto da leitura — hoje pelo pacote que a gravação emite, não por coluna do Parquet, porque
      MEDIDO em gravar_lago.py a partição tem três colunas mais a de partição e nenhuma é procedência;
      exigir que ela viesse do Parquet faria Bronze devolver NAO_MEDIDO na partição CORRETA, que é o defeito
      da Regra 9 pelo avesso. Quando apresentada, o hash_csv_sha256 é comparado com o ancorado e divergência
      é DIVERGE, porque reproduzir os dois controles não distingue o arquivo ancorado de outro com os
      mesmos totais, e a âncora vale para UM arquivo. Fazer a partição carregar a procedência é melhoria
      desejável e exige tarefa própria, por tocar em gravar_lago.py, que está sem Task-Spec (Regra 11)
      — enquanto não existir, Bronze registra a ausência do vínculo como limitação declarada da camada,
      nunca como aprovação silenciosa. Partição que diverge é DIVERGE, e Bronze não escreve nada
  - id: B-2
    given: uma competência cuja partição não existe no lago, ou existe com zero linhas
    when: Bronze lê a partição
    then: retorna NAO_MEDIDO como valor, sem escrever camada nenhuma e sem encerrar o processo; partição
      ausente e partição vazia são casos distintos e ambos NAO_MEDIDO, porque ler o lago e não encontrar
      nada não é o mesmo que medir e encontrar zero — a Regra 9 existe porque o segundo caminho é o que
      veste NAO_MEDIDO de MEDIDO. As outras partições do lago são nomeadas E CONTADAS na saída, e a soma
      das contagens por partição é conferida contra o total lido — nomear sem contar afirma isolação sem
      medi-la, e a lista de nomes continuaria idêntica se as linhas de uma partição tivessem migrado para
      outra. Se a soma das partições não fecha com o total, é DIVERGE, porque linha que não pertence a
      partição nenhuma é contaminação, e foi para vê-la que este controle existe
  evals:
  - id: eval_1
    description: Os dois controles batem e a partição é medida isoladamente
    bash: pytest -q tests/test_bronze.py -k "dois_controles or isola_particao or nao_soma_uniao or precisao_declarada"
    verifies:
    - B-1
  - id: eval_2
    description: Partição ausente e partição vazia devolvem NAO_MEDIDO
    bash: pytest -q tests/test_bronze.py -k "particao_ausente or particao_vazia"
    verifies:
    - B-2
  - id: eval_3
    description: Um centavo a mais reprova, e os dois controles juntos são necessários
    bash: pytest -q tests/test_bronze.py -k "centavo_a_mais or dois_controles or diverge_nao_escreve"
    verifies:
    - B-1
  anti_patterns:
  - action: somar todas as partições e comparar o total com a âncora
    reason: mede a união e culpa a parte; foi o erro que reportou contaminação onde a partição real batia
      exato
    instead: agrupar pela coluna de partição e conferir só a partição da competência
  - action: aceitar diferença de centavos como arredondamento
    reason: afrouxar a tolerância é editar o oráculo pelo avesso
    instead: exigir igualdade exata entre Decimal e Decimal
  - action: reimplementar do zero o que scripts/medir_lago.py já faz, sem citá-lo
    reason: os dois passariam a medir a mesma partição com pisos possivelmente diferentes, e medir_lago.py
      traz a âncora como default de linha de comando em vez de lê-la do contrato
    instead: partir de medir_lago.py, lendo a âncora do CONTRATO, e declarar no código qual dos dois é
      o de produção
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  rollback: Remover o leitor Bronze e seus testes.
  observability: partições recusadas por controle divergente
source_seam_sha256: 71120a0fe6435c93122bbadd509f883a70f8056657c586befd03faaf3310a408
---
# Bronze só existe quando reproduz a âncora do contrato

## Observable proof

A partição lida devolve as linhas e a soma ancoradas; partição ausente, vazia ou divergente devolve NAO_MEDIDO.

## Runnable leaves

- `T-20260922-bronze-confere-ancora` — Ler a partição do lago e conferi-la contra a âncora: Os dois controles da partição real batem com o contrato; qualquer outro caso devolve NAO_MEDIDO como valor. Os evals rodam num ambiente que tem AO MESMO TEMPO pytest e um leitor de Parquet — medido, hoje nenhum tem: o host não tem pyspark, pyarrow, pandas, duckdb nem java, e o contêiner pda-spark não tem pytest. Montar esse ambiente é parte desta tarefa, não pressuposto dela.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
