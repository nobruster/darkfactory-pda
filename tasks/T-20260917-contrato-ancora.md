---
id: T-20260917-contrato-ancora
title: "Carregar o contrato e recusar competência sem âncora"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: []
creates_paths: [src/fabrica/contrato.py, tests/test_contrato.py, contracts/competencia.yaml]
source_note: "seamwise/legs/LEG-CONTRATO-RECUSA-SEM-ANCORA.md#T-20260917-contrato-ancora"
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
signed_off: false
signed_off_by: (none)
signed_off_at: (none)
accepted: false
accepted_by: (none)
accepted_at: (none)
---

# Carregar o contrato e recusar competência sem âncora

> **Why:** Fazer a ausência de prova bloquear, em vez de virar verde.

## Goal

Fazer a ausência de prova bloquear, em vez de virar verde.

## Context

Intent DI-FABRICA-COMPETENCIA; seam SEAM-CONTRATO-ANCORA; swimlane LANE-CONTRATO; capability leg LEG-CONTRATO-RECUSA-SEM-ANCORA. Done condition: A tarefa entrega o contrato em disco — a fonte real não está neste workspace, e o fixture de competência é entregue pela leitura, que é quem lê arquivo. Competência com âncora carrega os cinco controles; sem âncora retorna NAO_MEDIDO como valor.

## Behavior

- **B-1** — GIVEN um contrato com os cinco números nomeados (count_linhas, sum_vl_liquido, min, max, linhas_invalidas), a procedência (aprovador, data, comando que mediu) E o layout de leitura (posições, formato monetário, chave do registro) WHEN o contrato é carregado THEN âncora, procedência e layout saem juntos, com os cinco controles sob os MESMOS nomes que o agregado usa — count_linhas, sum_vl_liquido, min_vl_liquido, max_vl_liquido, linhas_invalidas; a MESMA âncora sem aprovador, sem data ou sem layout resulta em NAO_MEDIDO
- **B-2** — GIVEN uma competência sem âncora no contrato WHEN o contrato é carregado THEN RETORNA o veredito NAO_MEDIDO como valor — não grava nem encerra o processo; quem persiste é a evidência, e quem encerra é o orquestrador

## Success Criteria

```bash
# eval_1: Cinco valores nomeados com procedência; sem aprovador ou data vira NAO_MEDIDO
eval_1() {
  pytest -q tests/test_contrato.py -k "ancorada or sem_procedencia"
}

# eval_2: Sem âncora retorna NAO_MEDIDO como valor, sem escrever em disco
eval_2() {
  pytest -q tests/test_contrato.py -k "nao_medido and not evidencia"
}

# eval_3: A âncora carregada bate com o contrato em disco
eval_3() {
  pytest -q tests/test_contrato.py -k integridade
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Cinco valores nomeados com procedência; sem aprovador ou data vira NAO_MEDIDO"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Sem âncora retorna NAO_MEDIDO como valor, sem escrever em disco"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A âncora carregada bate com o contrato em disco"
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

Remover o carregador de contrato e seus testes.

## Observability Hooks

contagem de competências ancoradas no contrato

## Anti-Patterns

- Do not gerar a âncora automaticamente quando ela falta: um número que ninguém viu medir é um palpite; instead retornar NAO_MEDIDO e parar.
- Do not tratar âncora ausente como zero: o gate compararia contra nada e publicaria ACEITO; instead distinguir ausência de valor.
- Do not editar a âncora para um veredito passar: falsifica a verdade contra a qual tudo é medido; instead investigar; âncora revista exige nova aprovação.

## Do-Not-Touch

- `cvg/docs/adrs`

## Open Questions

(none — this task is fully specified)
