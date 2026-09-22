> Projetado de `LEG-SILVER-PRESERVA-DEFEITO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `95de745f037525ce519b4c3551d4ba9d20c81fd3f1b86f6f20f2fec47274e04e`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-SILVER-PRESERVA-DEFEITO
seam_id: SEAM-SILVER
swimlane_id: LANE-SILVER
observable_state: Silver classifica o defeito e conserva o total
proof: A soma de Silver é idêntica à de Bronze, e os 11 colapsos saem classificados em vez de corrigidos.
requires:
- bronze conferido
- totais por código de Bronze
produces:
- silver classificado
- totais por código de Silver
tasks:
- id: T-20260922-silver-classifica-colapso
  title: Normalizar a forma e classificar a identidade colapsada
  goal: Preservar o defeito da fonte com o total intacto.
  done_condition: A soma não muda entre Bronze e Silver, e cada colapso recebe exatamente uma das seis
    classificações.
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
  depends_on:
  - T-20260922-bronze-confere-ancora
  touches_paths: []
  creates_paths:
  - src/medalhao/silver.py
  - tests/test_silver.py
  behavior:
  - id: B-1
    given: o Bronze conferido e o contrato, que declara 65 códigos, 52 descrições e 11 colapsos cobrindo
      24 códigos, pré-classificados como CONFIRMED_SOURCE_DEFECT com aprovador e data
    when: Silver normaliza
    then: 'a CHAVE é o código, nunca a descrição, como o ADR 0008 exige — agrupar por descrição fundiria
      os 24 códigos colapsados em 11 linhas e o total continuaria batendo, com os mapas por código errados
      e nada acusando. A normalização é de FORMA e não de conteúdo — espaços à borda e caixa da descrição,
      jamais o valor monetário. E a CONTAGEM DE COLAPSOS é medida sobre a descrição ORIGINAL, nunca sobre
      a normalizada, porque a normalização pode FUNDIR descrições que a fonte publica distintas: ''ABC''
      e ''abc'' de códigos diferentes viram um grupo só depois de igualar a caixa, e o colapso criado
      pela camada seria atribuído à fonte, ou uma partição correta receberia DIVERGE. Se as duas contagens
      diferirem, a diferença é da normalização e sai nomeada, não somada aos 11 do contrato. E a descrição
      ORIGINAL é PRESERVADA no registro do defeito, não apenas usada para contar — medir sobre ela e depois
      gravar o texto normalizado faria ''ABC'' e ''abc'' virarem indistinguíveis na saída, com as contagens
      corretas e a prova específica perdida. A Regra 4 pede preservar o defeito, e defeito de identidade
      sem a identidade original não é preservação, que atravessa como Decimal com a precisão declarada.
      A marca PROCEDENCIA_NAO_VINCULADA, quando Bronze a emite, atravessa Silver SEM ser removida e segue
      em ''silver classificado'' — remover uma marca de limitação é apagar prova, não normalizar. Silver
      PRODUZ o mapa total_por_codigo, em soma EXATA não quantizada, e ele é parte declarada de ''silver
      classificado'' — Gold o consome, e sem essa declaração Gold recalcularia os dois lados com a mesma
      transformação, perdendo a independência que o próprio plano dele exige. A conservação provada NÃO
      é só a soma global: o mapa de Silver é comparado com o de Bronze CÓDIGO A CÓDIGO, porque trocar
      os valores de dois códigos preserva soma, chaves, cardinalidades e grupos — {''01'': 10.00, ''03'':
      20.00} virando {''01'': 20.00, ''03'': 10.00} passa em toda prova global e altera o resultado por
      espécie. A soma de Silver também é comparada com a de Bronze e precisa ser IDÊNTICA — um pipeline
      que altera o total ao normalizar texto tem um defeito, não uma melhoria. Cada colapso recebe EXATAMENTE
      UMA das seis classificações e a contagem medida é conferida contra a do contrato — encontrar número
      diferente de 11 é DIVERGE, porque o contrato mediu na competência inteira e a divergência significa
      fonte diferente da ancorada, não permissão para ajustar o número'
  - id: B-2
    given: um código cuja descrição diverge do contrato, ou um colapso não declarado
    when: Silver normaliza
    then: 'a linha atravessa com o VALOR intacto e o defeito registrado, nunca descartada nem corrigida
      — descartar mudaria o total e corrigir destruiria a prova. Defeito não classificado BLOQUEIA a camada,
      e UNRESOLVED — que é uma das seis — BLOQUEIA igualmente: classificação preenchida não é defeito
      resolvido, e uma descrição divergente que recebesse UNRESOLVED conservaria o valor e satisfaria
      literalmente a condição de conclusão enquanto a diferença segue sem dono, porque a classificação
      é o que transforma um erro da origem em cobrança rastreável; e nenhuma classificação é inferida
      em silêncio, já que atribuir CONFIRMED_SOURCE_DEFECT sem aprovador transformaria juízo em default.
      MEDIDO no contrato: existem as cardinalidades 65/52/11/24 e a classificação global, mas NÃO existe
      mapa código→descrição nem a lista dos 11 grupos aprovados — e sem esse referencial ''descrição que
      diverge do contrato'' não é verificável, porque trocar a descrição de um código mantém todas as
      quatro cardinalidades. Silver então NÃO INVENTA referencial e NÃO aceita o grupo novo por default:
      sem o mapa declarado no contrato, a comparação por identidade devolve NAO_MEDIDO, distinto de bloquear
      por defeito — e esse NAO_MEDIDO IMPEDE produzir ''silver classificado'', porque uma capacidade chamada
      ''classificado'' que sai com a identidade não medida mente no próprio nome. A cadeia para aqui com
      o motivo nomeado, em vez de seguir e publicar com a identidade em aberto. Declarar esse mapa é trabalho
      do contrato, com aprovador e data, não desta camada.'
  evals:
  - id: eval_1
    description: A chave é o código, o mapa por código é preservado e a soma não muda
    bash: bash infra/medalhao-evals.sh tests/test_silver.py -k "chave_e_codigo or soma_identica or nao_agrupa_por_descricao
      or mapa_por_codigo_preservado or valores_trocados_entre_codigos"
    verifies:
    - B-1
  - id: eval_2
    description: Os 11 colapsos saem classificados e a contagem confere
    bash: bash infra/medalhao-evals.sh tests/test_silver.py -k "colapso_classificado or contagem_de_colapsos
      or classificacao_unica or colapsos_na_descricao_original"
    verifies:
    - B-1
  - id: eval_3
    description: Defeito não classificado bloqueia em vez de passar
    bash: bash infra/medalhao-evals.sh tests/test_silver.py -k "nao_classificado_bloqueia or valor_intacto
      or atravessa_sem_descartar or unresolved_bloqueia or sem_mapa_nao_produz_capacidade"
    verifies:
    - B-2
  anti_patterns:
  - action: provar a conservação só com a soma global entre Bronze e Silver
    reason: 'trocar os valores de dois códigos preserva soma, chaves e cardinalidades — {''01'': 10.00,
      ''03'': 20.00} virando {''01'': 20.00, ''03'': 10.00} passa em toda prova global'
    instead: comparar o mapa total_por_codigo código a código contra o de Bronze, em soma exata não quantizada
  - action: agrupar por descrição em vez de código
    reason: funde os 24 colapsados; o total continua batendo e os mapas por código saem errados
    instead: usar o código como chave, sempre
  - action: descartar a linha cuja descrição diverge do contrato
    reason: muda o total em silêncio, que é o defeito que a âncora existe para pegar
    instead: atravessar com o valor intacto e o defeito registrado
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  rollback: Remover a camada Silver e seus testes.
  observability: colapsos classificados por competência
source_seam_sha256: 09e7f12a2f9e6f9ba5afa1119b2f6eca8db4501d9a520c85b27bed0d16f8d911
---
# Silver classifica o defeito e conserva o total

## Observable proof

A soma de Silver é idêntica à de Bronze, e os 11 colapsos saem classificados em vez de corrigidos.

## Runnable leaves

- `T-20260922-silver-classifica-colapso` — Normalizar a forma e classificar a identidade colapsada: A soma não muda entre Bronze e Silver, e cada colapso recebe exatamente uma das seis classificações.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
