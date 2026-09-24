---
id: T-20260924-limpa-substituidas
title: "Limpar o preparo de execuções substituídas"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-testes-leves]
supersedes: (none)
touches_paths: [src/medalhao/limpeza.py, tests/test_limpeza.py]
creates_paths: []
source_note: "seamwise/legs/LEG-LIMPA-SUBSTITUIDAS.md#T-20260924-limpa-substituidas"
created: "2026-09-24T00:00:00Z"
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
signed_off_at: 2026-09-24T14:53:14Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:337bcbec24fc00198bf2a8dc8bd3cd3b4570ca4ccb3ca104fa6397630334e6e4
---

# Limpar o preparo de execuções substituídas

> **Why:** Não deixar sobras de execuções antigas.

## Goal

Não deixar sobras de execuções antigas.

## Context

Intent DI-PDA-PERFORMANCE; seam SEAM-LIMPA-SUBSTITUIDAS; swimlane LANE-LIMPA-SUBSTITUIDAS; capability leg LEG-LIMPA-SUBSTITUIDAS. Done condition: O preparo de execução substituída cuja publicação foi conferida é apagado; revertida, em curso ou sem commit fica.

## Behavior

- **B-1** — GIVEN o preparo de uma execução cujo commit de publicação está no histórico e foi SUBSTITUÍDO por outro posterior WHEN a limpeza roda THEN apaga o preparo dessa execução se o commit dela tem estado INTEGRO, NÃO é de reversão e nenhum commit de reversão a desfez — publicação conferida e depois substituída —, com a mesma guarda de caminho — sob a INVARIANTE declarada de que execução não é retomada: cada execução nasce com id novo e nunca reusa o preparo de outra, então um preparo cuja execução já tem commit publicado e foi substituída não está em uso —; a tabela publicada segue com a mesma versão, contagem e soma.
- **B-2** — GIVEN uma execução revertida, uma sem commit, ou um caminho fora do preparo WHEN a limpeza roda THEN preserva o preparo e diz o motivo — inclusive o da execução ATIVA, que ainda não tem commit; caminho fora de _preparo ou id vazio é RECUSADO antes de qualquer remoção; nenhum teste já existente de tests/test_limpeza.py é editado.

## Success Criteria

```bash
# eval_1: Substituída e conferida sai
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in substituida_conferida_apaga publicada_intacta_apos_limpar_substituida; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "substituida_conferida_apaga or publicada_intacta_apos_limpar_substituida"'
}

# eval_2: Revertida e em curso ficam
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in revertida_preserva sem_commit_preserva id_vazio_recusado execucao_ativa_preserva; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "revertida_preserva or sem_commit_preserva or id_vazio_recusado or execucao_ativa_preserva"'
}

# eval_3: O comportamento selado segue
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in apaga_preparo_de_execucao_publicada caminho_fora_do_preparo_recusado; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "apaga_preparo_de_execucao_publicada or caminho_fora_do_preparo_recusado"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Substituída e conferida sai"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Revertida e em curso ficam"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "O comportamento selado segue"
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

Reverter os arquivos tocados ao commit assentado; remover os criados.

## Observability Hooks

execuções com memória herdada ou cache não liberado

## Anti-Patterns

- Do not apagar preparo de execução revertida: é evidência de uma divergência; instead preservar.
- Do not montar o caminho com variável não validada: um valor vazio vira o bucket; instead montar_prefixo com partes validadas.
- Do not usar VACUUM: apaga histórico, que é evidência; instead apagar só o preparo.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/pda`

## Open Questions

(none — this task is fully specified)
