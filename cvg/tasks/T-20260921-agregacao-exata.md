---
id: T-20260921-agregacao-exata
title: "Somar com precisão declarada e agrupar pelo código"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260921-leitura-posicional]
supersedes: (none)
touches_paths: []
creates_paths: [src/pda/agregacao.py, tests/test_agregacao.py]
source_note: "seamwise/legs/LEG-AGREGADO-EXATO.md#T-20260921-agregacao-exata"
created: "2026-09-21T00:00:00Z"
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
signed_off_at: 2026-09-22T02:47:10Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:5c0efa2c69265cfdeaf29cc52008908b3d2299740427fdf7fb471e2397054e53
---

# Somar com precisão declarada e agrupar pelo código

> **Why:** Tornar as três decisões de decimal explícitas e verificáveis.

## Goal

Tornar as três decisões de decimal explícitas e verificáveis.

## Context

Intent DI-PDA-BENEFICIOS; seam SEAM-AGREGACAO; swimlane LANE-AGREGACAO; capability leg LEG-AGREGADO-EXATO. Done condition: Float recusado na entrada; os cinco controles saem nomeados; agrupar por descrição diverge de agrupar por código.

## Behavior

- **B-1** — GIVEN um valor de ponto flutuante em campo monetário, e um lote com registros ilegíveis misturados aos válidos WHEN o agregado é calculado THEN o float é recusado com erro explícito; os cinco controles são DOIS de contagem e TRÊS monetários, e só sum_vl_liquido é soma — count_linhas conta todo registro lido, linhas_invalidas conta só os ilegíveis, e sum, min e max ignoram o ilegível em vez de tratá-lo como 0.00; o teste prova que o ilegível foi EXCLUÍDO, nunca comparando totais, porque preencher com 0.00 não muda a soma, não muda max e não muda min — min já é 0.00 na fonte — e passaria despercebido pelos três. No limite em que NENHUM registro é legível, min e max não têm valor e o agregado os marca AUSENTES, com sum=0.00 e a contagem de inválidos igual à de lidos — zero inventaria extremos que não existem, e levantar exceção decidiria por conta própria que defeito de fonte interrompe o processamento, coisa que nem a tech-spec nem o juízo pediram; a ausência é representada e atravessa a fronteira e a evidência, que já marcam campo não percorrido como ausente
- **B-2** — GIVEN um contexto decimal de precisão baixa, valores em empate exato, e a alternativa meio-para-cima WHEN o total é calculado THEN o resultado é o de HALF_EVEN a duas casas — comparado contra o valor que HALF_UP produziria, e RECUSANDO-o; declarar um modo não basta, o teste falha se a implementação usar meio-para-cima. O contexto do agregador é PRÓPRIO e COMPLETO como o da leitura — precisão, arredondamento, Emax, Emin e traps declarados, com teste sob global adverso nos três eixos; declarar só precisão e modo deixaria uma biblioteca externa transformar execução válida em ERRO, e a exigência de contexto completo escrita só na leitura protege o mapa de referência, não quem soma. A perda por precisão baixa também é acusada, e arredondar por campo difere de arredondar no total. E a SAÍDA do agregador preserva os códigos distintos — tantos quantos a competência tiver, conferidos contra a cardinalidade ancorada no contrato e NÃO contra os 51 do ADR 0004, que foram medidos em ~3 milhões de linhas; na competência inteira são 65, e fixar 51 recusaria o arquivo correto. Cada VALOR por código é conferido contra os totais por código da leitura, não só a chave presente — um agregador que somasse por descrição, atribuísse o total ao primeiro código e emitisse zero nos demais conservaria todas as chaves e todos os controles globais, e a demonstração de que descrição e código têm cardinalidades diferentes continuaria verdadeira; se esse agregador fornecesse a referência da fronteira, o defeito contaminaria a conferência também

## Success Criteria

```bash
# eval_1: Float recusado; ilegível excluído e não zerado; nenhum legível marca extremos ausentes
eval_1() {
  pytest -q tests/test_agregacao.py -k "recusa_float or ilegivel_excluido_nao_zerado or nenhum_legivel_extremos_ausentes"
}

# eval_2: HALF_EVEN recusa o valor que HALF_UP daria; precisão e granularidade
eval_2() {
  pytest -q tests/test_agregacao.py -k "recusa_half_up or precisao_declarada or granularidade"
}

# eval_3: A saída preserva a cardinalidade ancorada; chave por descrição faz falhar
eval_3() {
  pytest -q tests/test_agregacao.py -k "chave_e_codigo or cardinalidade_ancorada"
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Float recusado; ilegível excluído e não zerado; nenhum legível marca extremos ausentes"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "HALF_EVEN recusa o valor que HALF_UP daria; precisão e granularidade"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A saída preserva a cardinalidade ancorada; chave por descrição faz falhar"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
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
  required_tools: [git, bash, python3, pytest]
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

Remover o agregador e seus testes.

## Observability Hooks

total agregado e espécies distintas

## Anti-Patterns

- Do not herdar o arredondamento padrão da linguagem: defaults divergem e o erro fica estruturalmente verde; instead declarar precisão, granularidade e regra.
- Do not agrupar por descricao_especie: quatro espécies virariam uma linha e o total bateria; instead agrupar pelo código da posição 12.
- Do not arredondar a cada soma parcial: o erro de arredondamento acumula linha a linha; instead somar exato e arredondar uma vez no final.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`

## Open Questions

(none — this task is fully specified)
