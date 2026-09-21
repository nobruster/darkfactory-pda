---
id: T-20260917-evidencia-packet
title: "Gravar o pacote de evidência por execução"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260917-juizo-classifica]
supersedes: (none)
touches_paths: []
creates_paths: [src/fabrica/evidencia.py, tests/test_evidencia.py]
source_note: "seamwise/legs/LEG-EVIDENCIA-RECONSTROI.md#T-20260917-evidencia-packet"
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

# Gravar o pacote de evidência por execução

> **Why:** Tornar o veredito auditável sem reexecutar o pipeline.

## Goal

Tornar o veredito auditável sem reexecutar o pipeline.

## Context

Intent DI-FABRICA-COMPETENCIA; seam SEAM-EVIDENCIA; swimlane LANE-EVIDENCIA; capability leg LEG-EVIDENCIA-RECONSTROI. Done condition: O pacote contém veredito, causa, âncora, agregado, classificações e a duração observada com o limite aplicado; distingue os quatro desfechos e marca como ausente o que não foi percorrido.

## Behavior

- **B-1** — GIVEN uma execução com âncora medida, e uma que terminou antes da leitura (sem agregado nem classificações) WHEN o pacote é lido de volta THEN o veredito é reconstruído sem reexecutar, incluindo a DURAÇÃO observada e o limite aplicado — uma recusa por tempo é distinguível de uma recusa por controle sem reexecutar; campos que não existiam no caminho percorrido são AUSENTES e assim marcados, nunca preenchidos com zero ou valor artificial
- **B-2** — GIVEN qualquer um dos quatro vereditos terminais — ACEITO, ACEITO_SEM_ANCORA, RECUSADO ou ERRO WHEN o pacote é gravado THEN o pacote registra o VEREDITO e, separadamente, a CAUSA — NAO_MEDIDO por exemplo — conforme ADR 0005; a recusa com âncora grava como RECUSADO, e NAO_MEDIDO nunca aparece no campo veredito

## Success Criteria

```bash
# eval_1: O pacote reconstrói o veredito
eval_1() {
  pytest -q tests/test_evidencia.py -k reconstroi
}

# eval_2: Sem âncora nunca vira ACEITO
eval_2() {
  pytest -q tests/test_evidencia.py -k sem_ancora
}

# eval_3: O pacote registra âncora, agregado e classificações
eval_3() {
  pytest -q tests/test_evidencia.py -k campos_obrigatorios
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "O pacote reconstrói o veredito"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Sem âncora nunca vira ACEITO"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "O pacote registra âncora, agregado e classificações"
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

Remover o gravador de evidência e seus testes.

## Observability Hooks

pacotes gravados por competência

## Anti-Patterns

- Do not gravar ACEITO com gate de âncora falso dentro: foi a objeção 28 — 82 milhões de linhas sem conferência; instead publicar ACEITO_SEM_ANCORA de forma visível.
- Do not editar um pacote antigo para corrigir o histórico: falsifica evidência; instead gravar evidência nova e manter a antiga.
- Do not gravar só o veredito, sem os números: ninguém consegue reconstruir por que aquilo foi aceito; instead registrar âncora, agregado e cada classificação.

## Do-Not-Touch

- `evidence`

## Open Questions

(none — this task is fully specified)
