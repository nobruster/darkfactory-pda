> Projetado de `LEG-SILVER-PRESERVA-DEFEITO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `d34fa9a8233891687a5dbb27a14a4dfc721986410f472058540eb38173b5a2a4`

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
produces:
- silver classificado
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
      diferirem, a diferença é da normalização e sai nomeada, não somada aos 11 do contrato, que atravessa
      como Decimal com a precisão declarada. A marca PROCEDENCIA_NAO_VINCULADA, quando Bronze a emite,
      atravessa Silver SEM ser removida e segue em ''silver classificado'' — remover uma marca de limitação
      é apagar prova, não normalizar. A soma de Silver é comparada com a de Bronze e precisa ser IDÊNTICA
      — um pipeline que altera o total ao normalizar texto tem um defeito, não uma melhoria. Cada colapso
      recebe EXATAMENTE UMA das seis classificações e a contagem medida é conferida contra a do contrato
      — encontrar número diferente de 11 é DIVERGE, porque o contrato mediu na competência inteira e a
      divergência significa fonte diferente da ancorada, não permissão para ajustar o número'
  - id: B-2
    given: um código cuja descrição diverge do contrato, ou um colapso não declarado
    when: Silver normaliza
    then: 'a linha atravessa com o VALOR intacto e o defeito registrado, nunca descartada nem corrigida
      — descartar mudaria o total e corrigir destruiria a prova. Defeito não classificado BLOQUEIA a camada,
      porque a classificação é o que transforma um erro da origem em cobrança rastreável; e nenhuma classificação
      é inferida em silêncio, já que atribuir CONFIRMED_SOURCE_DEFECT sem aprovador transformaria juízo
      em default. MEDIDO no contrato: existem as cardinalidades 65/52/11/24 e a classificação global,
      mas NÃO existe mapa código→descrição nem a lista dos 11 grupos aprovados — e sem esse referencial
      ''descrição que diverge do contrato'' não é verificável, porque trocar a descrição de um código
      mantém todas as quatro cardinalidades. Silver então NÃO INVENTA referencial e NÃO aceita o grupo
      novo por default: sem o mapa declarado no contrato, a comparação por identidade devolve NAO_MEDIDO,
      distinto de bloquear por defeito — e esse NAO_MEDIDO IMPEDE produzir ''silver classificado'', porque
      uma capacidade chamada ''classificado'' que sai com a identidade não medida mente no próprio nome.
      A cadeia para aqui com o motivo nomeado, em vez de seguir e publicar com a identidade em aberto.
      Declarar esse mapa é trabalho do contrato, com aprovador e data, não desta camada.'
  evals:
  - id: eval_1
    description: A chave é o código e a soma não muda entre camadas
    bash: pytest -q tests/test_silver.py -k "chave_e_codigo or soma_identica or nao_agrupa_por_descricao"
    verifies:
    - B-1
  - id: eval_2
    description: Os 11 colapsos saem classificados e a contagem confere
    bash: pytest -q tests/test_silver.py -k "colapso_classificado or contagem_de_colapsos or classificacao_unica
      or colapsos_na_descricao_original"
    verifies:
    - B-1
  - id: eval_3
    description: Defeito não classificado bloqueia em vez de passar
    bash: pytest -q tests/test_silver.py -k "nao_classificado_bloqueia or valor_intacto or atravessa_sem_descartar
      or sem_mapa_nao_produz_capacidade or marca_atravessa"
    verifies:
    - B-2
  anti_patterns:
  - action: deduplicar as descrições colapsadas
    reason: destrói a prova de que a origem publica 24 códigos sob 11 descrições
    instead: classificar como CONFIRMED_SOURCE_DEFECT e preservar as linhas
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
source_seam_sha256: 97fccd19f40133f97f0ef421d33ad21746f9005268f95eec00d3e51daceb0797
---
# Silver classifica o defeito e conserva o total

## Observable proof

A soma de Silver é idêntica à de Bronze, e os 11 colapsos saem classificados em vez de corrigidos.

## Runnable leaves

- `T-20260922-silver-classifica-colapso` — Normalizar a forma e classificar a identidade colapsada: A soma não muda entre Bronze e Silver, e cada colapso recebe exatamente uma das seis classificações.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
