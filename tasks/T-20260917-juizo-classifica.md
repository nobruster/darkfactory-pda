---
id: T-20260917-juizo-classifica
title: "Comparar contra a âncora e classificar a diferença"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260917-agregacao-exata]
supersedes: (none)
touches_paths: []
creates_paths: [src/fabrica/juizo.py, tests/test_juizo.py]
source_note: "seamwise/legs/LEG-JUIZO-ACUSA-CENTAVO.md#T-20260917-juizo-classifica"
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

# Comparar contra a âncora e classificar a diferença

> **Why:** Fazer o juiz acusar, não apenas aprovar.

## Goal

Fazer o juiz acusar, não apenas aprovar.

## Context

Intent DI-FABRICA-COMPETENCIA; seam SEAM-JUIZO; swimlane LANE-JUIZO; capability leg LEG-JUIZO-ACUSA-CENTAVO. Done condition: Um centavo alterado é recusado, e diferença sem classificação bloqueia a publicação.

## Behavior

- **B-1** — GIVEN um agregado derivado de arquivo com UMA LINHA corrompida em um centavo, e outro que redistribui valores mantendo soma e contagem WHEN o juízo compara contra a âncora THEN os CINCO controles são comparados individualmente (count_linhas, sum_vl_liquido, min_vl_liquido, max_vl_liquido, linhas_invalidas) e qualquer divergência recusa — soma e contagem iguais não bastam
- **B-2** — GIVEN uma diferença de cada uma das seis classificações, incluindo um controle divergente classificado como CONFIRMED_SOURCE_DEFECT, e o mesmo dado agregado com meio-para-cima WHEN o veredito é calculado THEN PRECEDÊNCIA — divergência em qualquer dos cinco controles RECUSA, mesmo classificada como CONFIRMED ou APPROVED; a classificação explica, nunca autoriza. Fora dos controles, MODERN_DEFECT, CONTRACT_AMBIGUITY e UNRESOLVED bloqueiam e as três CONFIRMED/APPROVED apenas registram. E o arredondamento errado muda o VEREDITO, não só o total

## Success Criteria

```bash
# eval_1: Um centavo na linha recusa; extremos alterados com soma igual também
eval_1() {
  pytest -q tests/test_juizo.py -k "um_centavo_na_linha or cinco_controles"
}

# eval_2: Cada uma das seis decide publicar ou bloquear; arredondamento muda o veredito
eval_2() {
  pytest -q tests/test_juizo.py -k "politica_por_classificacao or arredondamento_muda_veredito"
}

# eval_3: Defeito observado sem classificação bloqueia; nenhum é ignorado
eval_3() {
  pytest -q tests/test_juizo.py -k "classificacoes or defeito_sem_classe"
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Um centavo na linha recusa; extremos alterados com soma igual também"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Cada uma das seis decide publicar ou bloquear; arredondamento muda o veredito"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Defeito observado sem classificação bloqueia; nenhum é ignorado"
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

Remover o juízo e seus testes.

## Observability Hooks

vereditos por classificação

## Anti-Patterns

- Do not introduzir parâmetro de tolerância: um centavo inexplicado viraria um centavo aceito; instead classificar a diferença ou consertar o pipeline.
- Do not editar a âncora para o veredito passar: falsifica a prova em vez de investigar; instead investigar; âncora revista exige nova aprovação.
- Do not classificar como UNRESOLVED para destravar: UNRESOLVED bloqueia; usá-lo como atalho esconde a causa; instead medir a diferença e atribuir a classificação certa.

## Do-Not-Touch

- `cvg/docs/adrs`
- `contracts`

## Open Questions

(none — this task is fully specified)
