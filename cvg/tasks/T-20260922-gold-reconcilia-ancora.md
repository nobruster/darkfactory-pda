---
id: T-20260922-gold-reconcilia-ancora
title: "Agregar por código e reconciliar com a âncora"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260922-silver-classifica-colapso]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/gold.py, tests/test_gold.py]
source_note: "seamwise/legs/LEG-GOLD-RECONCILIA.md#T-20260922-gold-reconcilia-ancora"
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
signed_off_sig: hmac-sha256-v3:85d3c104:948e366841dc711b8b83a8b8aa5ee23c4803ed80e34f47c217418fd7a6d9d806
---

# Agregar por código e reconciliar com a âncora

> **Why:** Fazer o agregado provar que fecha, em vez de afirmar.

## Goal

Fazer o agregado provar que fecha, em vez de afirmar.

## Context

Intent DI-PDA-MEDALHAO; seam SEAM-GOLD; swimlane LANE-GOLD; capability leg LEG-GOLD-RECONCILIA. Done condition: A soma das linhas de Gold é igual à âncora ao centavo, com arredondamento único no total.

## Behavior

- **B-1** — GIVEN o Silver classificado e o contrato, com a política decimal declarada — HALF_EVEN, escala 2, e a precisão DERIVADA conforme o ADR 0009, que nesta competência dá 14 WHEN Gold agrega por código THEN o arredondamento acontece UMA VEZ, sobre o total, como o ADR 0003 exige, na camada que o 0007 e o 0009 preservaram — arredondar cada código antes de somar dá resultado diferente, e a diferença é sistemática, não ruído — 2,345 + 2,345 dá 4,68 por campo e 4,69 no total, ambos meio-para-par. O modo é HALF_EVEN, decidido pelo ADR 0003 e preservado pelo 0009, lido do CONTRATO, nunca escolhido aqui, porque meio-para-cima empurra todo empate na mesma direção e vira tendência em volume. A precisão é a declarada e o contexto é CONSTRUÍDO DO ZERO — localcontext(Context(prec, rounding, traps=[])) — as TRAPS são declaradas, não deixadas por conta do construtor. localcontext() sozinho COPIA o contexto global e herda as traps junto; e Context(prec, rounding) sem declarar traps preenche o que foi omitido a partir de DefaultContext, que é IGUALMENTE mutável, então uma biblioteca que ligue DefaultContext.traps[Inexact] derruba também essa construção. O que não se declara, se herda: com traps[Inexact] ligada por qualquer biblioteca importada, Decimal('2.345').quantize(Decimal('.01')) LEVANTA Inexact dentro de um localcontext que declarou prec e rounding, e o arredondamento que o contrato PERMITE encerra a operação. O ADR 0006 diz que a precisão é declarada e não herdada; as traps são herdadas do mesmo jeito, e declarar prec e rounding não basta. Depois de agregar, a soma das linhas de Gold é RECONCILIADA com a âncora do contrato e a igualdade é exata ao centavo. Soma e cardinalidade NÃO BASTAM: uma redistribuição compensada entre códigos preserva as duas e troca os valores de lugar — {'01': 10.00, '03': 20.00} e {'01': 11.00, '03': 19.00} têm a mesma soma e as mesmas chaves, e acrescentar os outros 63 códigos idênticos aos dois mantém o contraexemplo com os 65. Por isso o MAPA total_por_codigo de Gold é comparado, código a código, contra o mapa que a camada anterior produziu, em soma EXATA não quantizada; com um mapa só, deslocar valor entre códigos seria aprovado por comparação consigo mesmo; Gold que não reconcilia devolve DIVERGE e NÃO publica, porque um agregado publicado sem reconciliar é exatamente o que a âncora existe para impedir. A reconciliação é recalculada a partir das linhas CANDIDATAS — materializadas em local privado, jamais no caminho que os consumidores leem — e não herdada de Bronze, senão Gold provaria a conta de outra camada. A publicação é um passo POSTERIOR e condicionado ao veredito, e o veredito CONSOME a marca PROCEDENCIA_NAO_VINCULADA que Bronze emite e Silver preserva — Gold recusa publicar sob ela, e a recusa tem eval próprio, senão cada camada cumpre o seu e a marca se perde na transformação: se as candidatas fossem escritas no destino para depois serem relidas, o dado divergente já teria ficado exposto antes de qualquer veredito, e remover depois não desfaz a exposição. Um teste que confira só o resultado final ou a ausência de arquivos ao término não vê isso — o eval observa que o caminho de destino permanece inalterado DURANTE a reconciliação. E a publicação em si é uma transição INDIVISÍVEL de visibilidade: o conjunto publicado é exatamente o conjunto reconciliado, tudo ou nada. Copiar vários arquivos expondo-os à medida que chegam deixaria um consumidor lendo parte das candidatas, ou misturadas com as da execução anterior, com a reconciliação correta e o total lido por ninguém aprovado — e uma interrupção no meio congela esse estado. Publicação interrompida deixa o destino como estava antes
- **B-2** — GIVEN um Silver cujo total não reproduz a âncora, ou uma competência sem âncora no contrato WHEN Gold agrega THEN devolve DIVERGE quando o total não bate e NAO_MEDIDO quando não há âncora, dois estados distintos que nunca colapsam num só — sem âncora não é divergência, é ausência de referencial, e tratá-los igual faria a fábrica parecer que mediu quando não tinha contra o que medir. Nenhum dos dois publica, o motivo sai nomeado, e cada diferença recebe EXATAMENTE UMA das seis classificações da R-6 — inclusive a introduzida DEPOIS de Bronze, que é justamente a que nenhuma camada anterior viu. Devolver só estado e motivo cumpriria este plano e violaria a especificação; diferença que Gold não saiba classificar recebe UNRESOLVED, que bloqueia; a contagem de códigos de Gold é conferida contra os 65 do contrato, e o GRÃO das linhas publicadas é UMA por código — reagrupar candidatas para construir o mapa esconderia código duplicado no resultado materializado, já que ('01', 30.00) e o par ('01', 10.00) mais ('01', 20.00) produzem o mesmo mapa e a mesma contagem de códigos distintos; a prova é sobre as linhas EFETIVAMENTE publicadas, não sobre o mapa derivado delas, porque um agregado com menos códigos que a fonte pode somar o mesmo total e ainda assim ter perdido uma categoria inteira

## Success Criteria

```bash
# eval_1: Arredondamento único, precisão declarada, e recusa sob procedência não vinculada
eval_1() {
  bash infra/medalhao-evals.sh tests/test_gold.py -k "arredonda_uma_vez or half_even_do_contrato or nao_arredonda_por_campo or traps_declaradas or recusa_sob_procedencia_nao_vinculada"
}

# eval_2: Reconcilia recalculando, compara o mapa por código e confere os 65
eval_2() {
  bash infra/medalhao-evals.sh tests/test_gold.py -k "reconcilia_recalculando or mapa_por_codigo or redistribuicao_compensada or contagem_de_codigos or uma_linha_por_codigo"
}

# eval_3: DIVERGE e NAO_MEDIDO são estados distintos e nenhum publica
eval_3() {
  bash infra/medalhao-evals.sh tests/test_gold.py -k "diverge_nao_publica or sem_ancora_nao_medido or destino_inalterado_durante or classifica_diferenca_das_seis"
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Arredondamento único, precisão declarada, e recusa sob procedência não vinculada"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Reconcilia recalculando, compara o mapa por código e confere os 65"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "DIVERGE e NAO_MEDIDO são estados distintos e nenhum publica"
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

Remover a camada Gold e seus testes.

## Observability Hooks

agregados recusados por não reconciliar

## Anti-Patterns

- Do not construir o contexto decimal sem declarar as traps, seja com localcontext() sozinho ou com Context(prec, rounding): localcontext() copia o contexto global, e Context() preenche o omitido a partir de DefaultContext — os dois mutáveis; com traps[Inexact] ligada, quantize levanta e o arredondamento que o contrato permite encerra a operação; instead localcontext(Context(prec=..., rounding=..., traps=[])).
- Do not provar a agregação só com a soma total e a contagem de códigos: uma redistribuição compensada entre códigos preserva as duas e troca os valores de lugar — contraexemplo executado com {'01': 10.00, '03': 20.00} contra {'01': 11.00, '03': 19.00}; instead comparar o mapa total_por_codigo código a código contra o da camada anterior, em soma exata não quantizada.
- Do not tratar falta de âncora como divergência: ausência de referencial vira medição com resultado ruim, e a fábrica parece ter medido; instead devolver NAO_MEDIDO, distinto de DIVERGE.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`

## Open Questions

(none — this task is fully specified)
