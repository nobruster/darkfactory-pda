---
id: T-20260923-limpa-preparo
title: "Apagar o preparo de execuções publicadas e conferidas"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260923-gold-le-silver]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/limpeza.py, tests/test_limpeza.py]
source_note: "seamwise/legs/LEG-LIMPA-PREPARO.md#T-20260923-limpa-preparo"
created: "2026-09-23T00:00:00Z"
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
signed_off_at: 2026-09-23T21:44:04Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:04d6d3c4863134d091cd15f1963e209660fa12a22b490703b505a4b9395ee12f
---

# Apagar o preparo de execuções publicadas e conferidas

> **Why:** Não deixar o estágio privado ocupar o armazenamento.

## Goal

Não deixar o estágio privado ocupar o armazenamento.

## Context

Intent DI-PDA-MEDALHAO-V4; seam SEAM-LIMPA-PREPARO; swimlane LANE-LIMPA-PREPARO; capability leg LEG-LIMPA-PREPARO. Done condition: Para cada camada, o preparo de uma execução é apagado só se o histórico da tabela publicada tem o commit daquela execução; qualquer outro caso preserva o preparo e diz por quê.

## Behavior

- **B-1** — GIVEN o preparo de uma execução cujo commit está no histórico da tabela publicada WHEN a limpeza roda para a camada e a execução THEN confere que o ÚLTIMO commit que nomeia a competência no userMetadata é o dessa execução, com estado de publicação e NÃO de reversão — um commit revertido ou seguido de outro não é publicação conferida —, apaga SÓ o prefixo <camada>/_preparo/.../execucao=<id> — um caminho montado de partes validadas, recusado se vier vazio ou fora de _preparo —, e confere depois que a tabela publicada mantém a mesma versão, a mesma contagem e a mesma soma.
- **B-2** — GIVEN uma execução sem commit no histórico, um id vazio ou um caminho fora do preparo WHEN a limpeza roda THEN não apaga nada e devolve o motivo: execução não publicada preserva o preparo; id vazio ou caminho fora de _preparo é RECUSADO antes de qualquer remoção, porque um prefixo vazio já montou uma vez o caminho do bucket inteiro.

## Success Criteria

```bash
# eval_1: Apaga só o preparo conferido
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in apaga_preparo_de_execucao_publicada publicada_intacta_depois; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "apaga_preparo_de_execucao_publicada or publicada_intacta_depois"'
}

# eval_2: Guarda de caminho
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in id_vazio_recusado caminho_fora_do_preparo_recusado execucao_nao_publicada_preserva commit_revertido_preserva; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "id_vazio_recusado or caminho_fora_do_preparo_recusado or execucao_nao_publicada_preserva or commit_revertido_preserva"'
}

# eval_3: Nada além do prefixo da execução
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in outra_execucao_intacta prefixo_montado_de_partes_validadas; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "outra_execucao_intacta or prefixo_montado_de_partes_validadas"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Apaga só o preparo conferido"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Guarda de caminho"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Nada além do prefixo da execução"
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

Remover limpeza.py e seu teste; o preparo apagado é regenerável rodando a camada.

## Observability Hooks

preparos de execuções já publicadas

## Anti-Patterns

- Do not montar o caminho a apagar com variável não validada: um valor vazio vira o bucket inteiro; instead validar cada parte e exigir o prefixo _preparo/…/execucao=<id>.
- Do not apagar preparo de execução sem commit publicado: pode ser uma execução ainda em curso; instead exigir o commit da execução no histórico.
- Do not usar VACUUM para liberar espaço: VACUUM apaga histórico, que é evidência; instead apagar só o preparo, que não é histórico de tabela publicada.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`

## Open Questions

(none — this task is fully specified)
