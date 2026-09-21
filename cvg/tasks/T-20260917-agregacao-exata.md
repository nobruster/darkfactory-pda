---
id: T-20260917-agregacao-exata
title: "Somar valores monetários com meio-para-par"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260917-leitura-competencia]
supersedes: (none)
touches_paths: []
creates_paths: [src/fabrica/agregacao.py, tests/test_agregacao.py]
source_note: "seamwise/legs/LEG-AGREGADO-EXATO.md#T-20260917-agregacao-exata"
created: "2026-09-17T00:00:00Z"
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
signed_off_at: 2026-09-21T17:56:52Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:42572d07:91ce63a6386106f969ceb35394ffd7ef8a68a118e0ce395cb797c5aca552478f
---

# Somar valores monetários com meio-para-par

> **Why:** Tornar a regra de arredondamento explícita e verificável.

## Goal

Tornar a regra de arredondamento explícita e verificável.

## Context

Intent DI-FABRICA-COMPETENCIA; seam SEAM-AGREGACAO; swimlane LANE-AGREGACAO; capability leg LEG-AGREGADO-EXATO. Done condition: Float é recusado na entrada e o total usa meio-para-par a duas casas.

## Behavior

- **B-1** — GIVEN um valor de ponto flutuante em campo monetário WHEN o agregado é calculado THEN a entrada é recusada com erro explícito E o agregado é devolvido mesmo assim, com os CINCO controles nomeados (count_linhas, sum_vl_liquido, min_vl_liquido, max_vl_liquido, linhas_invalidas) e o campo monetário recusado contado em linhas_invalidas — recusar não é devolver nada
- **B-2** — GIVEN valores em empate exato, um contexto cujo default já é meio-para-par, um contexto com prec=6, e a alternativa de arredondar por campo WHEN o total é calculado THEN precisão E modo são DECLARADOS, não herdados — com prec=6 a soma acusa a perda (10000.00 + 0.01 vira 10000.0, e quantizar depois não recupera, ADR 0006); trocar o default do contexto para meio-para-cima faz o teste falhar se a implementação o herdar; e arredondar por campo dá 4,68 contra 4,69 no total (ADR 0004)

## Success Criteria

```bash
# eval_1: Float recusado; o agregado traz os cinco controles nomeados
eval_1() {
  pytest -q tests/test_agregacao.py -k "recusa_float or cinco_controles"
}

# eval_2: Precisão e modo declarados; prec=6 acusa; granularidade do total
eval_2() {
  pytest -q tests/test_agregacao.py -k "precisao_declarada or modo_explicito or granularidade"
}

# eval_3: O total de 2026-03 reproduz a âncora medida
eval_3() {
  pytest -q tests/test_agregacao.py -k total_ancora
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Float recusado; o agregado traz os cinco controles nomeados"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Precisão e modo declarados; prec=6 acusa; granularidade do total"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "O total de 2026-03 reproduz a âncora medida"
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

total agregado por competência

## Anti-Patterns

- Do not herdar o arredondamento padrão da linguagem: defaults divergem e o erro fica estruturalmente verde; instead declarar a regra no contrato e testá-la.
- Do not converter float para decimal silenciosamente: o centavo já se perdeu antes da conversão; instead recusar float na entrada.
- Do not arredondar a cada soma parcial: o erro de arredondamento acumula linha a linha; instead somar exato e arredondar uma vez no final.

## Do-Not-Touch

- `cvg/docs/adrs`

## Open Questions

(none — this task is fully specified)
