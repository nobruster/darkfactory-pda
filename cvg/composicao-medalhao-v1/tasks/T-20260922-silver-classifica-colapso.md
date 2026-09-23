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
signed_off_at: 2026-09-23T03:57:01Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:54e7dddaa46dd44ed091c354b9c97542376d6c330aa0e2926f09099a89985a7c
---

# Normalizar a forma e classificar a identidade colapsada

> **Why:** Preservar o defeito da fonte com o total intacto.

## Goal

Preservar o defeito da fonte com o total intacto.

## Context

Intent DI-PDA-MEDALHAO; seam SEAM-SILVER; swimlane LANE-SILVER; capability leg LEG-SILVER-PRESERVA-DEFEITO. Done condition: A contagem de linhas e a soma não mudam entre Bronze e Silver, e cada colapso recebe exatamente uma das seis classificações.

## Behavior

- **B-1** — GIVEN o Bronze conferido e o contrato, que declara 65 códigos, 52 descrições e 11 colapsos cobrindo 24 códigos, pré-classificados como CONFIRMED_SOURCE_DEFECT com aprovador e data WHEN Silver normaliza THEN a CHAVE é o código, nunca a descrição, como o ADR 0008 exige — agrupar por descrição fundiria os 24 códigos colapsados em 11 linhas e o total continuaria batendo, com os mapas por código errados e nada acusando. A normalização é de FORMA e não de conteúdo — espaços à borda e caixa da descrição, jamais o valor monetário. E a CONTAGEM DE COLAPSOS é medida sobre a descrição ORIGINAL, nunca sobre a normalizada, porque a normalização pode FUNDIR descrições que a fonte publica distintas: 'ABC' e 'abc' de códigos diferentes viram um grupo só depois de igualar a caixa, e o colapso criado pela camada seria atribuído à fonte, ou uma partição correta receberia DIVERGE. Se as duas contagens diferirem, a diferença é da normalização, sai nomeada E RECEBE uma das seis classificações da R-6 como qualquer outra — identidade criada na saída normalizada é diferença, e diferença nomeada sem classificação fica sem dono, que é o vício que a R-6 existe para fechar; ela não é somada aos 11 do contrato. E a descrição ORIGINAL é PRESERVADA no registro do defeito, não apenas usada para contar — medir sobre ela e depois gravar o texto normalizado faria 'ABC' e 'abc' virarem indistinguíveis na saída, com as contagens corretas e a prova específica perdida. A Regra 4 pede preservar o defeito, e defeito de identidade sem a identidade original não é preservação, que atravessa como Decimal com a precisão declarada. A marca PROCEDENCIA_NAO_VINCULADA, quando Bronze a emite, atravessa Silver SEM ser removida e segue em 'silver classificado' — remover uma marca de limitação é apagar prova, não normalizar. Silver PRODUZ o mapa total_por_codigo, em soma EXATA não quantizada, e ele é parte declarada de 'silver classificado' — Gold o consome, e sem essa declaração Gold recalcularia os dois lados com a mesma transformação, perdendo a independência que o próprio plano dele exige. A conservação provada NÃO é só a soma global: o mapa de Silver é comparado com o de Bronze CÓDIGO A CÓDIGO, porque trocar os valores de dois códigos preserva soma, chaves, cardinalidades e grupos — {'01': 10.00, '03': 20.00} virando {'01': 20.00, '03': 10.00} passa em toda prova global e altera o resultado por espécie. O MULTICONJUNTO de linhas de Silver é idêntico ao de Bronze no que toca código e valor — igualdade linha a linha, não agregada: duas linhas do MESMO código e MESMA descrição, 10.00 e 20.00, virando 11.00 e 19.00 preservam contagem, soma E o mapa por código, porque o mapa agrega justamente por código e não separa linhas irmãs. Por isso a prova é sobre o multiconjunto, e a contagem de linhas de Silver é idêntica à de Bronze — soma e mapa por código não bastam: remover uma linha de valor ZERO cuja combinação código/descrição continue presente preserva a soma, o mapa, as cardinalidades e os colapsos, e a perda passaria em toda prova declarada. A soma de Silver também é comparada com a de Bronze e precisa ser IDÊNTICA — um pipeline que altera o total ao normalizar texto tem um defeito, não uma melhoria. Cada colapso recebe EXATAMENTE UMA das seis classificações e a contagem medida é conferida contra a do contrato — encontrar número diferente de 11 é DIVERGE, porque o contrato mediu na competência inteira e a divergência significa fonte diferente da ancorada, não permissão para ajustar o número
- **B-2** — GIVEN um código cuja descrição diverge do contrato, ou um colapso não declarado WHEN Silver normaliza THEN a linha atravessa com o VALOR intacto e o defeito registrado, nunca descartada nem corrigida — descartar mudaria o total e corrigir destruiria a prova. Defeito não classificado BLOQUEIA a camada, e UNRESOLVED — que é uma das seis — BLOQUEIA igualmente: classificação preenchida não é defeito resolvido, e uma descrição divergente que recebesse UNRESOLVED conservaria o valor e satisfaria literalmente a condição de conclusão enquanto a diferença segue sem dono, porque a classificação é o que transforma um erro da origem em cobrança rastreável; e nenhuma classificação é inferida em silêncio, já que atribuir CONFIRMED_SOURCE_DEFECT sem aprovador transformaria juízo em default. MEDIDO no contrato: existem as cardinalidades 65/52/11/24 e a classificação global, mas NÃO existe mapa código→descrição nem a lista dos 11 grupos aprovados — e sem esse referencial 'descrição que diverge do contrato' não é verificável, porque trocar a descrição de um código mantém todas as quatro cardinalidades. Silver então NÃO INVENTA referencial e NÃO aceita o grupo novo por default: sem o mapa declarado no contrato, a comparação por identidade devolve NAO_MEDIDO, distinto de bloquear por defeito — e esse NAO_MEDIDO IMPEDE produzir 'silver classificado', porque uma capacidade chamada 'classificado' que sai com a identidade não medida mente no próprio nome. A cadeia para aqui com o motivo nomeado, em vez de seguir e publicar com a identidade em aberto. Declarar esse mapa é trabalho do contrato, com aprovador e data, não desta camada — e ENQUANTO ele não existir, esta tarefa entrega apenas a capacidade CONDICIONAL: o caminho NAO_MEDIDO provado, e o caminho positivo provado contra contrato de teste, jamais contra a competência contratada. Concluir Bronze NÃO habilita a prova positiva de Silver sobre 2026-01, e o plano não finge que habilita. scripts/medir_colapso.py já mede os 11 grupos na competência inteira; falta a aprovação, que é decisão de negócio.

## Success Criteria

```bash
# eval_1: Chave é o código; contagem, mapa e soma preservados, inclusive linha de valor zero
eval_1() {
  bash infra/medalhao-evals.sh tests/test_silver.py -k "chave_e_codigo or multiconjunto_identico or linhas_irmas_com_valores_trocados or linha_de_valor_zero_nao_some or mapa_por_codigo_preservado"
}

# eval_2: Os 11 colapsos saem classificados e a contagem confere
eval_2() {
  bash infra/medalhao-evals.sh tests/test_silver.py -k "colapso_classificado or contagem_de_colapsos or classificacao_unica or colapsos_na_descricao_original or colapso_da_normalizacao_classificado"
}

# eval_3: Defeito não classificado bloqueia em vez de passar
eval_3() {
  bash infra/medalhao-evals.sh tests/test_silver.py -k "nao_classificado_bloqueia or valor_intacto or atravessa_sem_descartar or unresolved_bloqueia or sem_mapa_nao_produz_capacidade"
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
