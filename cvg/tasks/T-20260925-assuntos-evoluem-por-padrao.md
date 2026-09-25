---
id: T-20260925-assuntos-evoluem-por-padrao
title: "Os assuntos evoluem por padrão"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260925-gold-evolui-por-padrao]
supersedes: (none)
touches_paths: [src/medalhao/gold_assuntos.py, tests/test_assuntos_nome_oficial.py]
creates_paths: []
source_note: "seamwise/legs/LEG-ASSUNTOS-EVOLUEM.md#T-20260925-assuntos-evoluem-por-padrao"
created: "2026-09-25T00:00:00Z"
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
signed_off_at: 2026-09-25T18:05:46Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:3e1571f2c12460309d804e84aca6bb66a25b373d649f4586a5cfbebdfdef1226
---

# Os assuntos evoluem por padrão

> **Why:** Fazer a Gold por assuntos evoluir de forma aditiva por padrão. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Fazer a Gold por assuntos evoluir de forma aditiva por padrão. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-PRATICAS-DELTA; seam SEAM-ASSUNTOS-EVOLUEM; swimlane LANE-ASSUNTOS-EVOLUEM; capability leg LEG-ASSUNTOS-EVOLUEM. Done condition: _executar_gold_assuntos tem evolucao_aditiva=True por padrão; em tests/test_assuntos_nome_oficial.py muda só o teste nomeado e entra o novo; todos passam.

## Behavior

- **B-1** — GIVEN uma fat_especie já publicada com o schema antigo em tmp_path WHEN os assuntos publicam com nome_oficial SEM passar evolucao_aditiva THEN _executar_gold_assuntos tem evolucao_aditiva=True por padrão: a coluna nova entra e a outra competência fica intacta; com evolucao_aditiva=False explícito, recusa como antes.
- **B-2** — GIVEN o tests/test_assuntos_nome_oficial.py da receita D WHEN a tarefa atualiza os testes THEN EXATAMENTE isto: em test_fat_existente_evolui_e_outra_competencia_intacta, a asserção de recusa sem o sinalizador passa a usar evolucao_aditiva=False EXPLÍCITO; entra test_fat_evolui_por_padrao_sem_sinalizador; os demais test_* ficam como estão; test_gold_assuntos.py não é tocado. Nenhum cenário usa skip, xfail ou importorskip; os testes gravam só em tmp_path, nunca no MinIO; nenhuma função para a sessão Spark da suíte.

## Success Criteria

```bash
# eval_1: A fat evolui por padrão
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_evolui_por_padrao_sem_sinalizador fat_existente_evolui_e_outra_competencia_intacta; do python3 -m pytest --collect-only -q tests/test_assuntos_nome_oficial.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_assuntos_nome_oficial.py -k "fat_evolui_por_padrao_sem_sinalizador or fat_existente_evolui_e_outra_competencia_intacta"'
}

# eval_2: O nome da fat segue igual
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_nome_da_mesma_especie_da_gold fat_controles_iguais_com_e_sem_nome; do python3 -m pytest --collect-only -q tests/test_assuntos_nome_oficial.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_assuntos_nome_oficial.py -k "fat_nome_da_mesma_especie_da_gold or fat_controles_iguais_com_e_sem_nome"'
}

# eval_3: Os assuntos existentes seguem iguais
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_especie_fecha_com_a_ancora publica_com_replacewhere commit_nomeia_versoes_lidas; do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py -k "fat_especie_fecha_com_a_ancora or publica_com_replacewhere or commit_nomeia_versoes_lidas"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A fat evolui por padrão"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "O nome da fat segue igual"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Os assuntos existentes seguem iguais"
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

Reverter os caminhos tocados e remover os criados.

## Observability Hooks

fat recusada por coluna nova

## Anti-Patterns

- Do not tocar test_gold_assuntos.py: a guarda protege os corpos; instead só o arquivo do nome oficial.
- Do not apagar a asserção de recusa: a recusa com False explícito é contrato; instead False explícito.
- Do not overwriteSchema: proibido (test_gold_assuntos.py:245); instead mergeSchema com a guarda.

## Do-Not-Touch

- `_raw`
- `contracts`
- `cvg/docs/adrs`
- `src/pda`
- `src/ontologia`
- `src/produtor`
- `infra`
- `tests/test_gold.py`
- `tests/test_gold_assuntos.py`
- `tests/test_testes_leves.py`
- `src/medalhao/bronze.py`
- `src/medalhao/silver.py`
- `src/medalhao/ingestao.py`
- `src/medalhao/gold.py`
- `tests/test_gold_nome_oficial.py`

## Open Questions

(none — this task is fully specified)
