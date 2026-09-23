---
id: T-20260922-silver-classifica-colapso
title: "Normalizar a forma e classificar a identidade colapsada"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260922-bronze-confere-ancora]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/silver.py, tests/test_silver.py]
source_note: "seamwise/legs/LEG-SILVER-PRESERVA-DEFEITO.md#T-20260922-silver-classifica-colapso"
created: "2026-09-22T00:00:00Z"
tags: []
owner: (none)
priority: P2
severity: feature
due_date: (none)
precondition: (none)
blocked_reason: (none)
security_class: (none)
source_action_item: (none)
tracker_ref: (none)
execution_backend: any
signed_off: true
signed_off_by: nobru
signed_off_at: 2026-09-23T15:47:43Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:875e7975be99bc79d862a75201f7b8fdf3a3c163f45ac49871373c7490d00f18
---

# Normalizar a forma e classificar a identidade colapsada

> **Why:** Preservar o defeito da fonte com o total intacto.

## Goal

Preservar o defeito da fonte com o total intacto.

## Context

Intent DI-PDA-MEDALHAO; seam SEAM-SILVER; swimlane LANE-SILVER; capability leg LEG-SILVER-PRESERVA-DEFEITO. Done condition: A contagem de linhas e a soma não mudam entre Bronze e Silver, e cada colapso recebe exatamente uma das seis classificações. Na competência real, enquanto o mapa código→descrição não for aprovado no contrato, 'silver classificado' sai com estado NAO_MEDIDO na competência real — a capacidade existe e é entregue, com o estado dizendo por que a cadeia para.

## Behavior

- **B-1** — GIVEN o Bronze conferido e o contrato, que declara 65 códigos, 52 descrições e 11 colapsos cobrindo 24 códigos, pré-classificados como CONFIRMED_SOURCE_DEFECT com aprovador e data WHEN Silver normaliza THEN No caminho Spark, o Context do Python NÃO governa a aritmética — medido: com prec=3 e Emax=5 no Python, o Spark somou exato, e sum() promove decimal(14,2) a decimal(24,2) por conta própria. O que governa é o DecimalType do acumulador, declarado a partir da politica_decimal do contrato, e a sessão roda com spark.sql.ansi.enabled=true DECLARADO: em modo não-ANSI, o estouro do acumulador devolve NULL sem erro, que é o Infinity da Regra 5 com outro nome. O Context(prec, rounding, traps=[], Emax, Emin) vale para o que roda em Python fora do motor. a CHAVE é o código, nunca a descrição, como o ADR 0008 exige — agrupar por descrição fundiria os 24 códigos colapsados em 11 linhas e o total continuaria batendo, com os mapas por código errados e nada acusando. A normalização é de FORMA e não de conteúdo — espaços à borda e caixa da descrição, jamais o valor monetário. e as QUATRO cardinalidades do contrato são conferidas contra o dado, não apenas a de colapsos — 65 códigos, 52 descrições, 11 colapsos e 24 códigos colapsados, cada uma comparada individualmente, porque um contrato com 51 descrições e 25 colapsados passaria numa conferência que só olha os 11. As TRÊS cardinalidades que dependem de descrição — descrições distintas, colapsos e códigos colapsados — são medidas sobre a descrição ORIGINAL, a mesma base em que o contrato as mediu; só códigos distintos independe dela. A normalização move as três em sentidos opostos: 'ABC' e 'abc' de códigos diferentes DIMINUEM as descrições distintas e AUMENTAM os códigos colapsados, e comparar medida normalizada contra contrato bruto reprovaria a partição correta ou esconderia um colapso criado pela própria camada. A CONTAGEM DE COLAPSOS é medida sobre a descrição ORIGINAL, nunca sobre a normalizada, porque a normalização pode FUNDIR descrições que a fonte publica distintas: 'ABC' e 'abc' de códigos diferentes viram um grupo só depois de igualar a caixa, e o colapso criado pela camada seria atribuído à fonte, ou uma partição correta receberia DIVERGE. A prova de que a normalização não fundiu identidades NÃO é contar grupos — é comparar, CÓDIGO A CÓDIGO, o conjunto de códigos que compartilham a descrição antes e depois de normalizar. Contar falha: se 'ABC' cobre 01 e 02 e 'abc' cobre 03, há um grupo colapsado antes e um depois, e o 03 perdeu identidade sem a contagem mudar. Todo código cujo grupo mudou é COLAPSO INTRODUZIDO PELA CAMADA, classificado como MODERN_DEFECT — porque foi a camada moderna que o criou — E bloqueante mesmo assim: classificar e autorizar são decisões independentes, como já vale para UNRESOLVED, e o contrato diz que defeito fora da lista conhecida bloqueia. A classificação dá dono à diferença; o bloqueio impede que ela siga. Silver sai BLOQUEADO, com os códigos afetados nomeados. Se as contagens diferirem, a diferença também sai nomeada — identidade criada na saída normalizada é diferença, e diferença nomeada sem classificação fica sem dono, que é o vício que a R-6 existe para fechar; ela não é somada aos 11 do contrato. E a descrição ORIGINAL é PRESERVADA no registro do defeito, não apenas usada para contar — medir sobre ela e depois gravar o texto normalizado faria 'ABC' e 'abc' virarem indistinguíveis na saída, com as contagens corretas e a prova específica perdida. A Regra 4 pede preservar o defeito, e defeito de identidade sem a identidade original não é preservação. O valor monetário atravessa como Decimal sob um contexto construído INTEIRO a partir da politica_decimal do contrato — Context(prec, rounding, traps=[], Emax, Emin) — pelo mesmo motivo que vale em Bronze e Gold: Silver SOMA, e declarar só a precisão deixa traps e limites de expoente virem do DefaultContext, que é mutável. Quando mais de uma falha vale ao mesmo tempo, a PRECEDÊNCIA de Silver é DIVERGE, depois BLOQUEADO, depois NAO_MEDIDO — o estado reporta a falha MEDIDA mais próxima da fonte, e o que não se mediu não esconde o que se mediu: cardinalidade divergente diz que a entrada não é a ancorada, colapso introduzido diz que a camada errou, e a falta do mapa só diz que uma comparação não pôde ser feita. É diferente da competência sem âncora, que nem chega às camadas — o carregador devolve o sentinela e conduzir fecha antes do callback, porque ali NENHUM controle tem referencial; aqui a cardinalidade e a normalização são medidas sem o mapa. Toda falha medida sai NOMEADA no diagnóstico, qualquer que seja o estado que vença. Silver só transforma sobre 'bronze conferido' com estado INTEGRO — DIVERGE, NAO_MEDIDO e ERRO_LEITURA PARAM a cadeia aqui, com o estado propagado sem tradução, porque um Bronze que divergiu por máximo alterado preserva soma, cardinalidades e identidades, e todas as provas de conservação de Silver passariam sobre linhas que Bronze já reprovou. A COMPETÊNCIA que Bronze leu, os CINCO CONTROLES que Bronze mediu sobre as linhas de detalhe, o HASH da procedência apresentada a Bronze e a marca PROCEDENCIA_NAO_VINCULADA, quando Bronze a emite, atravessam Silver SEM serem removidos — Gold os precisa para emitir o envelope, cujo ENVELOPE_SCHEMA exige sha256_arquivo_lido e controles, e os controles do envelope são os do DETALHE, medidos por Bronze, nunca os das 65 linhas agregadas de Gold e segue em 'silver classificado' — remover uma marca de limitação é apagar prova, não normalizar. A capacidade 'silver classificado' tem FORMA declarada, como a de Bronze, e COLUNAS NOMEADAS que Gold consome pelos mesmos nomes — especie_codigo, especie_descricao (a original), especie_descricao_normalizada, vl_liquido, competencia e classificacao — porque conteúdo sem nome deixa Silver emitir codigo/valor e Gold esperar especie_codigo/vl_liquido, com as duas passando nos próprios testes. Silver prova que consome a saída REAL de Bronze, produzida pelo módulo de Bronze, não uma fixture escrita à mão — é na fixture que o descasamento se esconde. Conteúdo: o estado, AS LINHAS normalizadas e classificadas — código, descrição original, descrição normalizada e valor — o mapa total_por_codigo em soma EXATA não quantizada, os defeitos classificados, a competência e as marcas de limitação. Sem as linhas, Gold fica sem entrada para agregar as próprias candidatas, e consumir o mapa pronto enfraqueceria a independência que o plano dele exige — Gold o consome, e sem essa declaração Gold recalcularia os dois lados com a mesma transformação, perdendo a independência que o próprio plano dele exige. A conservação provada NÃO é só a soma global: o mapa de Silver é comparado com o de Bronze CÓDIGO A CÓDIGO, porque trocar os valores de dois códigos preserva soma, chaves, cardinalidades e grupos — {'01': 10.00, '03': 20.00} virando {'01': 20.00, '03': 10.00} passa em toda prova global e altera o resultado por espécie. Toda comparação desta camada roda NO MOTOR, sobre as 41.572.553 linhas, sem coletar: o multiconjunto é comparado como diferença simétrica de contagens agrupadas por (código, descrição original, valor), e igualdade é essa diferença vazia — uma coleção Python com quarenta milhões de Decimal não cabe em memória e faria o Pass 8 cair na primeira execução real, com os testes de fixture passando. O MULTICONJUNTO de linhas de Silver é idêntico ao de Bronze no que toca código, DESCRIÇÃO ORIGINAL e valor — com a descrição dentro, porque trocar as descrições originais entre dois códigos não colapsados, ('01', 'A', 10) e ('03', 'B', 20) virando ('01', 'B', 10) e ('03', 'A', 20), mantém um multiconjunto de só código e valor, todos os totais e as quatro cardinalidades — igualdade linha a linha, não agregada: duas linhas do MESMO código e MESMA descrição, 10.00 e 20.00, virando 11.00 e 19.00 preservam contagem, soma E o mapa por código, porque o mapa agrega justamente por código e não separa linhas irmãs. Por isso a prova é sobre o multiconjunto, e a contagem de linhas de Silver é idêntica à de Bronze — soma e mapa por código não bastam: remover uma linha de valor ZERO cuja combinação código/descrição continue presente preserva a soma, o mapa, as cardinalidades e os colapsos, e a perda passaria em toda prova declarada. A soma de Silver também é comparada com a de Bronze e precisa ser IDÊNTICA — um pipeline que altera o total ao normalizar texto tem um defeito, não uma melhoria. Cada colapso recebe EXATAMENTE UMA das seis classificações e a contagem medida é conferida contra a do contrato — encontrar número diferente de 11 é DIVERGE, porque o contrato mediu na competência inteira e a divergência significa fonte diferente da ancorada, não permissão para ajustar o número
- **B-2** — GIVEN um código COLAPSADO cuja descrição diverge do mapa aprovado, ou um colapso não declarado WHEN Silver normaliza THEN a linha atravessa com o VALOR intacto e o defeito registrado, nunca descartada nem corrigida — descartar mudaria o total e corrigir destruiria a prova. Os colapsos classificados por Silver têm a MESMA granularidade que a leitura independente usa — um registro por GRUPO colapsado, com a descrição ORIGINAL e a lista ordenada dos códigos que ela cobre, onze nesta competência —, e não um por linha nem um por código, porque o juiz confronta os dois lados e granularidades diferentes divergiriam sem nenhum defeito real. Defeito não classificado BLOQUEIA a camada, e bloquear tem ESTADO de saída declarado: 'silver classificado' sai com estado BLOQUEADO, nunca INTEGRO, e a lista dos defeitos que bloquearam — porque Gold só agrega sobre INTEGRO, e um INTEGRO com UNRESOLVED dentro seria agregado sem que ninguém olhasse as classificações. Defeito não classificado BLOQUEIA a camada, e UNRESOLVED — que é uma das seis — BLOQUEIA igualmente: classificação preenchida não é defeito resolvido, e uma descrição divergente que recebesse UNRESOLVED conservaria o valor e satisfaria literalmente a condição de conclusão enquanto a diferença segue sem dono, porque a classificação é o que transforma um erro da origem em cobrança rastreável; e nenhuma classificação é inferida em silêncio, já que atribuir CONFIRMED_SOURCE_DEFECT sem aprovador transformaria juízo em default. MEDIDO no contrato: existem as cardinalidades 65/52/11/24 e a classificação global, mas NÃO existe mapa código→descrição nem a lista dos 11 grupos aprovados — e sem esse referencial 'descrição que diverge do contrato' não é verificável, porque trocar a descrição de um código mantém todas as quatro cardinalidades. Silver então NÃO INVENTA referencial e NÃO aceita o grupo novo por default: sem o mapa declarado no contrato, a comparação por identidade devolve NAO_MEDIDO, distinto de bloquear por defeito — e esse NAO_MEDIDO impede a capacidade POSITIVA — 'silver classificado' é SEMPRE entregue, como objeto, mas com estado NAO_MEDIDO e nunca INTEGRO, porque um 'classificado' INTEGRO com a identidade não medida mentiria no próprio nome, e porque Gold precisa RECEBER o estado para propagá-lo: devolver ausência quebraria o consumidor. A cadeia para aqui com o motivo nomeado, em vez de seguir e publicar com a identidade em aberto. A exigência não é escolha desta camada: é a decisão DEC-MAPA-APROVADO-OBRIGATORIO, do dono, que torna a aprovação individual do mapa condição obrigatória de publicação. Declarar esse mapa é trabalho do contrato, com aprovador e data, não desta camada — e ENQUANTO ele não existir, esta tarefa entrega apenas a capacidade CONDICIONAL: o caminho NAO_MEDIDO provado, e o caminho positivo provado contra contrato de teste, jamais contra a competência contratada. Concluir Bronze NÃO habilita a prova positiva de Silver sobre 2026-01, e o plano não finge que habilita. scripts/medir_colapso.py já mede os 11 grupos na competência inteira; falta a aprovação, que é decisão de negócio. O referencial tem ALCANCE e Silver o declara: o mapa aprovado cobre os 24 códigos colapsados; para os outros 41 o contrato só carrega cardinalidade, então Silver confere que cada um tem UMA descrição e que nenhuma se repete fora dos grupos, mas NÃO verifica o conteúdo — a troca de descrição entre dois códigos não colapsados preserva as quatro cardinalidades e passa. Estender a decisão do dono aos 41 seria requisito novo, não correção. O estado de 'silver classificado' carrega essa cobertura — códigos verificados pelo mapa e códigos só por cardinalidade — para que a limitação apareça na evidência em vez de se esconder atrás de um INTEGRO. O dinheiro não depende disso: os totais são por código.

## Success Criteria

```bash
# eval_1: Chave é o código; contagem, mapa e soma preservados, inclusive linha de valor zero
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in chave_e_codigo multiconjunto_identico linhas_irmas_com_valores_trocados linha_de_valor_zero_nao_some mapa_por_codigo_preservado contexto_declarado entrega_as_linhas_normalizadas descricao_trocada_entre_codigos multiconjunto_sem_coletar ansi_declarado_estouro_nao_vira_nulo consome_saida_real_de_bronze; do python3 -m pytest --collect-only -q tests/test_silver.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_silver.py -k "chave_e_codigo or multiconjunto_identico or linhas_irmas_com_valores_trocados or linha_de_valor_zero_nao_some or mapa_por_codigo_preservado or contexto_declarado or entrega_as_linhas_normalizadas or descricao_trocada_entre_codigos or multiconjunto_sem_coletar or ansi_declarado_estouro_nao_vira_nulo or consome_saida_real_de_bronze"'
}

# eval_2: Os 11 colapsos saem classificados e a contagem confere
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in colapso_classificado quatro_cardinalidades classificacao_unica colapsos_na_descricao_original colapso_da_normalizacao_classificado recusa_bronze_nao_integro colapso_introduzido_por_codigo_bloqueia precedencia_dos_estados_de_falha; do python3 -m pytest --collect-only -q tests/test_silver.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_silver.py -k "colapso_classificado or quatro_cardinalidades or classificacao_unica or colapsos_na_descricao_original or colapso_da_normalizacao_classificado or recusa_bronze_nao_integro or colapso_introduzido_por_codigo_bloqueia or precedencia_dos_estados_de_falha"'
}

# eval_3: Defeito não classificado bloqueia em vez de passar
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in nao_classificado_bloqueia valor_intacto atravessa_sem_descartar unresolved_bloqueia marca_atravessa sem_mapa_entrega_estado_nao_medido bloqueio_sai_como_bloqueado controles_e_hash_atravessam colapso_um_registro_por_grupo cobertura_do_referencial_declarada; do python3 -m pytest --collect-only -q tests/test_silver.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_silver.py -k "nao_classificado_bloqueia or valor_intacto or atravessa_sem_descartar or unresolved_bloqueia or marca_atravessa or sem_mapa_entrega_estado_nao_medido or bloqueio_sai_como_bloqueado or controles_e_hash_atravessam or colapso_um_registro_por_grupo or cobertura_do_referencial_declarada"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Chave é o código; contagem, mapa e soma preservados, inclusive linha de valor zero"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Os 11 colapsos saem classificados e a contagem confere"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Defeito não classificado bloqueia em vez de passar"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: true
    expected_duration_sec: 10
retry_policy:
  max_iterations: 15
  circuit_breaker_no_progress: 3
  on_terminal_failure: park_with_context
agent_contract:
  version: 2
  read: [intent, behavior, contract, guardrails]
  produce: [code, tests]
  required_tools: [git, bash, python3, pytest, docker]
  timeout_minutes: 30
  sandbox_type: host
  output_artifacts: []
  mcp_dependencies: []
  emit: [pass, fail, retry_with_reason, parked_with_context]
  backend_metadata: {}
```

## Exit Check

```bash
eval_1 && eval_2 && eval_3
```

## Rollback Plan

Remover a camada Silver e seus testes.

## Observability Hooks

colapsos classificados por competência

## Anti-Patterns

- Do not provar a conservação só com a soma global entre Bronze e Silver: trocar os valores de dois códigos preserva soma, chaves e cardinalidades — {'01': 10.00, '03': 20.00} virando {'01': 20.00, '03': 10.00} passa em toda prova global; instead comparar o mapa total_por_codigo código a código contra o de Bronze, em soma exata não quantizada.
- Do not agrupar por descrição em vez de código: funde os 24 colapsados; o total continua batendo e os mapas por código saem errados; instead usar o código como chave, sempre.
- Do not provar a conservação só com contagem, soma e mapa por código: duas linhas do mesmo código e descrição com valores trocados — 10.00 e 20.00 virando 11.00 e 19.00 — preservam os três, porque o mapa agrega por código; instead comparar o multiconjunto de (código, valor) entre Bronze e Silver, linha a linha.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`

## Open Questions

(none — this task is fully specified)
