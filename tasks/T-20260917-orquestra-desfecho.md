---
id: T-20260917-orquestra-desfecho
title: "Decidir o desfecho e garantir o pacote em todo caminho"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260917-evidencia-packet]
supersedes: (none)
touches_paths: []
creates_paths: [src/fabrica/orquestracao.py, tests/test_orquestracao.py]
source_note: "seamwise/legs/LEG-DESFECHO-SEMPRE-COM-PACOTE.md#T-20260917-orquestra-desfecho"
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

# Decidir o desfecho e garantir o pacote em todo caminho

> **Why:** Dar dono ao fluxo — sem ele a lacuna migra de costura em costura.

## Goal

Dar dono ao fluxo — sem ele a lacuna migra de costura em costura.

## Context

Intent DI-FABRICA-COMPETENCIA; seam SEAM-ORQUESTRACAO; swimlane LANE-ORQUESTRACAO; capability leg LEG-DESFECHO-SEMPRE-COM-PACOTE. Done condition: Os quatro desfechos gravam pacote e saem com código próprio; a execução completa é medida contra os 600s de R-6.

## Behavior

- **B-1** — GIVEN execução sem âncora, execução ancorada que bate, e o ARQUIVO com uma linha corrompida em um centavo WHEN a orquestração conduz o fluxo inteiro e decide o desfecho THEN as três gravam pacote — ACEITO_SEM_ANCORA com causa NAO_MEDIDO, ACEITO, e RECUSADO — com códigos de saída distintos; o centavo corrompido chega ao juízo e é recusado PONTA A PONTA, e só ACEITO autoriza publicar
- **B-2** — GIVEN uma exceção REAL levantada dentro da leitura, e um caso em que a leitura cabe no limite mas o resto estoura WHEN a orquestração conduz a execução THEN a exceção vira desfecho ERRO com pacote gravado — não escapa encerrando o processo; e R-6 reprova acima de 600s no TOTAL, etapa rápida com o resto lento não passa. Falha do próprio gravador é o único caso sem pacote, e sai com código distinto

## Success Criteria

```bash
# eval_1: Os quatro desfechos gravam pacote com código de saída próprio
eval_1() {
  pytest -q tests/test_orquestracao.py -k desfechos
}

# eval_2: Exceção real vira ERRO com pacote; R-6 mede o total, não a etapa
eval_2() {
  pytest -q tests/test_orquestracao.py -k "excecao_vira_erro or tempo_total"
}

# eval_3: Só ACEITO autoriza publicar
eval_3() {
  pytest -q tests/test_orquestracao.py -k autoriza_publicar
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Os quatro desfechos gravam pacote com código de saída próprio"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Exceção real vira ERRO com pacote; R-6 mede o total, não a etapa"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Só ACEITO autoriza publicar"
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

Remover a orquestração e seus testes.

## Observability Hooks

desfechos por tipo e segundos da leitura ao veredito

## Anti-Patterns

- Do not encerrar o processo dentro de uma etapa: o pacote prometido nunca é gravado; instead retornar o veredito e deixar a orquestração decidir.
- Do not medir o tempo por etapa: leitura em 530s mais o resto em 120s viola R-6 e passa; instead medir do início da leitura ao veredito.
- Do not tratar ACEITO_SEM_ANCORA como autorização: a palavra aceito nomeia o término, não a prova; instead só ACEITO autoriza, e só com os cinco controles conferidos.

## Do-Not-Touch

- `cvg/docs/adrs`

## Open Questions

(none — this task is fully specified)
