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
  done_condition: 'Os cinco controles da partição real batem com o contrato. Partição AUSENTE ou VAZIA
    devolve NAO_MEDIDO; partição MEDIDA que diverge em qualquer controle devolve DIVERGE — os dois são
    estados distintos e nenhum escreve camada, porque confundir ausência de medição com reprovação torna
    instável a interface que Silver consome. Os evals rodam num ambiente que tem AO MESMO TEMPO pytest
    e um leitor de Parquet — medido, hoje nenhum tem: o host não tem pyspark, pyarrow, pandas, duckdb
    nem java, e o contêiner pda-spark não tem pytest. As ferramentas do HOST são git, bash, python3, pytest
    e docker: pyspark NÃO entra em required_tools, porque o pré-voo confere o PATH do host com shutil.which
    e a tarefa que existe PARA montar o ambiente seria impedida de começar por exigir o que ela mesma
    vai prover — pyspark vive dentro do contêiner, que o docker levanta. Montar esse ambiente é parte
    desta tarefa e tem caminho declarado — infra/medalhao-evals.sh, que roda os evals num checkout limpo
    sem instalação manual — e os nove evals das três camadas o INVOCAM, em vez de chamar pytest direto,
    porque criar o script não muda o ambiente de quem executa e o eval falharia antes de testar Bronze.
    Sem ele a obrigação existiria sem forma reproduzível de cumpri-la, e um agente que criasse o arquivo
    mesmo assim receberia path_policy: fail.'
  effort: M
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
  - infra/medalhao-evals.sh
  behavior:
  - id: B-1
    given: uma partição do lago e o contrato da competência, com a âncora de linhas e de soma medidas
      na fonte
    when: Bronze lê a partição
    then: 'a contagem e a soma são recalculadas SOBRE A PARTIÇÃO, nunca sobre a união das partições —
      um agregado sem GROUP BY na coluna de partição não mede partição nenhuma, e foi assim que a leitura
      da união deu 41.622.553 contra a âncora de 41.572.553 e uma contaminação inexistente foi reportada,
      quando a partição real batia exato e as 50.000 linhas estavam em competencia=fatia-teste, isolada.
      A soma é feita com a precisão DECLARADA no contrato, jamais herdada do contexto global, como o ADR
      0009 exige, porque qualquer biblioteca importada pode alterar o contexto e o acumulador passaria
      a perder centavos sem que uma linha deste código mude. Os CINCO controles da âncora são comparados
      INDIVIDUALMENTE, como a R-5 da tech-spec exige — count_linhas, sum_vl_liquido, min_vl_liquido, max_vl_liquido
      e linhas_invalidas. Contagem e soma sozinhas não bastam, e não bastam nem juntas: uma alteração
      COMPENSADA entre duas linhas preserva as duas e ainda assim empurra o máximo acima dos 183.725,76
      ancorados, com todos os valores finitos, não negativos e na escala permitida. Silver preservaria
      a soma e Gold compararia soma e cardinalidade; nenhuma das três veria. Bronze PRODUZ o mapa total_por_codigo
      — soma exata não quantizada, por código — e ele é parte declarada de ''bronze conferido''. É a ORIGEM
      do mapa: quem lê o Parquet é quem sabe qual valor pertence a qual código, e uma camada posterior
      que o recalcule a partir dos mesmos bytes repetiria um erro de atribuição nos dois lados da comparação,
      aprovando-o. Cada controle que diverge é nomeado na saída, porque saber QUAL falhou é o que separa
      investigar de adivinhar — e cada diferença recebe EXATAMENTE UMA das seis classificações da R-6
      (CONFIRMED_SOURCE_DEFECT, CONFIRMED_LEGACY_DEFECT, APPROVED_BEHAVIOR_CHANGE, MODERN_DEFECT, CONTRACT_AMBIGUITY,
      UNRESOLVED). DIVERGE é estado de MEDIÇÃO, não classificação: recusar a partição corretamente e entregar
      diagnóstico sem classificação deixaria a diferença sem dono. Diferença que a camada não saiba classificar
      recebe UNRESOLVED, que é uma das seis e BLOQUEIA — nunca fica em branco. O tipo monetário da ENTRADA
      é recusado se não for decimal — a R-4 manda recusar float, nunca convertê-lo, e converter apaga
      a evidência da entrada proibida: Decimal(str(1.25)) devolve 1.25, finito, não negativo e na escala
      2, satisfazendo todas as verificações de domínio enquanto a origem era um DOUBLE. A recusa é do
      TIPO declarado no esquema do Parquet, antes de ler valor algum. Só então a comparação monetária
      é entre Decimal e Decimal, e a igualdade é exata — tolerância aqui seria a Regra 3 pelo avesso,
      afrouxar o oráculo para a camada passar. Todo valor lido é conferido contra o domínio monetário
      do contrato antes de entrar no acumulador — finito, NÃO NEGATIVO e dentro da escala declarada. A
      não-negatividade não é preferência, e sim a premissa de soma MONOTÔNICA sob a qual o ADR 0009 deriva
      a precisão 14 — um valor negativo quebra a premissa e a perda de centavo passa a acontecer DURANTE
      a soma, onde a comparação final não a enxerga. Bronze lê Parquet, que não passa nem pela gramática
      do CSV nem pela fronteira do envelope, e por isso é uma TERCEIRA porta de entrada para valores;
      fechá-la é obrigação desta camada. Valor fora do domínio é defeito classificado com identidade,
      valor original e posição, nunca somado em silêncio. A procedência do arquivo que originou a partição
      é APRESENTADA a Bronze junto da leitura — hoje pelo pacote que a gravação emite, não por coluna
      do Parquet, porque MEDIDO em gravar_lago.py a partição tem três colunas mais a de partição e nenhuma
      é procedência; exigir que ela viesse do Parquet faria Bronze devolver NAO_MEDIDO na partição CORRETA,
      que é o defeito da Regra 9 pelo avesso. Quando apresentada, o hash_csv_sha256 é comparado com o
      ancorado e divergência é DIVERGE, porque reproduzir os dois controles não distingue o arquivo ancorado
      de outro com os mesmos totais, e a âncora vale para UM arquivo. Fazer a partição carregar a procedência
      é melhoria desejável e exige tarefa própria, por tocar em gravar_lago.py, que está sem Task-Spec
      (Regra 11) — enquanto não existir, a ausência do vínculo tem CONSEQUÊNCIA definida e propagada —
      ''bronze conferido'' sai marcado PROCEDENCIA_NAO_VINCULADA, Silver e Gold propagam a marca sem removê-la,
      e Gold NÃO PUBLICA sob ela. Registrar só uma ressalva deixaria a cadeia publicar partição diferente
      da ancorada, porque o hash correto num pacote sem vínculo verificável com a partição lida satisfaz
      a comparação textual e não prova nada. Partição que diverge é DIVERGE, e Bronze não escreve nada'
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
      tivessem migrado para outra. A PRECEDÊNCIA é declarada e não negociável: o estado da competência
      SOLICITADA decide primeiro. Ausente ou vazia devolve NAO_MEDIDO mesmo que o lago tenha outros problemas,
      porque não se reprova o que não se mediu. Só quando a competência existe e foi medida é que o fechamento
      do lago entra — e aí, se a soma das partições não fecha com o total, é DIVERGE, porque linha que
      não pertence a partição nenhuma é contaminação — e o total vem de um UNIVERSO INDEPENDENTE, a listagem
      dos objetos do lago, nunca da mesma leitura agrupada: somar contagens agrupadas pela própria relação
      lida é identidade, fecha sempre, inclusive somando o grupo nulo, e não veria arquivo que as DUAS
      leituras ignoraram. As chaves que constituem partição válida são as declaradas no contrato; objeto
      fora delas, ou linha cuja chave de partição é nula, conta como não pertencente e faz o controle
      reprovar, e foi para vê-la que este controle existe'
  evals:
  - id: eval_1
    description: Os cinco controles comparados individualmente, e a partição medida isoladamente
    bash: bash infra/medalhao-evals.sh tests/test_bronze.py -k "cinco_controles or alteracao_compensada
      or isola_particao or nao_soma_uniao or precisao_declarada"
    verifies:
    - B-1
  - id: eval_2
    description: Ausente e vazia devolvem NAO_MEDIDO; medida e divergente devolve DIVERGE
    bash: bash infra/medalhao-evals.sh tests/test_bronze.py -k "particao_ausente or particao_vazia or
      presente_sem_ancora or diverge_nao_e_nao_medido"
    verifies:
    - B-2
  - id: eval_3
    description: Float recusado na entrada, e toda diferença com uma das seis classificações
    bash: bash infra/medalhao-evals.sh tests/test_bronze.py -k "centavo_a_mais or maximo_acima_do_ancorado
      or recusa_float_na_entrada or classificacao_das_seis"
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
source_seam_sha256: cafd6348439d37f0447861eca772149f4221dcc179c84df891706266a7eb0cec
---
# Bronze só existe quando reproduz a âncora do contrato

## Observable proof

A partição lida reproduz os cinco controles ancorados; ausente ou vazia devolve NAO_MEDIDO, e medida-e-divergente devolve DIVERGE — estados distintos, nunca colapsados.

## Runnable leaves

- `T-20260922-bronze-confere-ancora` — Ler a partição do lago e conferi-la contra a âncora: Os cinco controles da partição real batem com o contrato. Partição AUSENTE ou VAZIA devolve NAO_MEDIDO; partição MEDIDA que diverge em qualquer controle devolve DIVERGE — os dois são estados distintos e nenhum escreve camada, porque confundir ausência de medição com reprovação torna instável a interface que Silver consome. Os evals rodam num ambiente que tem AO MESMO TEMPO pytest e um leitor de Parquet — medido, hoje nenhum tem: o host não tem pyspark, pyarrow, pandas, duckdb nem java, e o contêiner pda-spark não tem pytest. As ferramentas do HOST são git, bash, python3, pytest e docker: pyspark NÃO entra em required_tools, porque o pré-voo confere o PATH do host com shutil.which e a tarefa que existe PARA montar o ambiente seria impedida de começar por exigir o que ela mesma vai prover — pyspark vive dentro do contêiner, que o docker levanta. Montar esse ambiente é parte desta tarefa e tem caminho declarado — infra/medalhao-evals.sh, que roda os evals num checkout limpo sem instalação manual — e os nove evals das três camadas o INVOCAM, em vez de chamar pytest direto, porque criar o script não muda o ambiente de quem executa e o eval falharia antes de testar Bronze. Sem ele a obrigação existiria sem forma reproduzível de cumpri-la, e um agente que criasse o arquivo mesmo assim receberia path_policy: fail.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
