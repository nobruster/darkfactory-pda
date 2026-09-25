---
id: T-20260925-silver-e-ingestao-evoluem-por-padrao
title: "A Silver e a ingestão evoluem por padrão"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260925-sessao-e-bronze-com-padroes-delta]
supersedes: (none)
touches_paths: [src/medalhao/silver.py, src/medalhao/ingestao.py]
creates_paths: [tests/test_delta_padroes_silver.py]
source_note: "seamwise/legs/LEG-SILVER-E-INGESTAO-EVOLUEM.md#T-20260925-silver-e-ingestao-evoluem-por-padrao"
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
signed_off_at: 2026-09-25T18:02:19Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-25T18:34:31Z
signed_off_sig: hmac-sha256-v3:85d3c104:6d6de6251f4c95f2c6fe82bdd7e16c03a9473d7ab9f749cf81c3831c37aa0923
accepted_tier: 1
accepted_attempt_id: 2690a457-2fce-4ebf-bc95-36fd3efe6c60
accepted_authorization_ref: hmac-sha256-v3:85d3c104:6d6de6251f4c95f2c6fe82bdd7e16c03a9473d7ab9f749cf81c3831c37aa0923
acceptance_record_digest: sha256:0263b8dcb969bfeb15be3e71e29ff1a6e34144dbd4d9fe9bc08cb34520ef0182
---

# A Silver e a ingestão evoluem por padrão

> **Why:** Fazer a Silver e a ingestão evoluírem de forma aditiva por padrão, com a guarda. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Fazer a Silver e a ingestão evoluírem de forma aditiva por padrão, com a guarda. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-PRATICAS-DELTA; seam SEAM-SILVER-E-INGESTAO-EVOLUEM; swimlane LANE-SILVER-E-INGESTAO-EVOLUEM; capability leg LEG-SILVER-E-INGESTAO-EVOLUEM. Done condition: executar_classificacao e executar_ingestao têm evolucao_aditiva=True por padrão; os testes de tests/test_delta_padroes_silver.py passam.

## Behavior

- **B-1** — GIVEN uma Bronze de fixture em tmp_path WHEN a Silver (executar_classificacao) e a ingestão (executar_ingestao) publicam THEN as duas passam a ter evolucao_aditiva=True por padrão: coluna nova entra; troca de tipo e coluna removida continuam recusadas pela guarda verificar_evolucao; evolucao_aditiva=False explícito recusa coluna nova; a ingestão repassa o valor recebido à Bronze.
- **B-2** — GIVEN os testes selados de test_silver.py, test_ingestao.py e test_orquestracao.py WHEN a tarefa termina THEN nenhum teste existente muda e todos passam; em tests/test_delta_padroes_silver.py entram test_silver_evolui_por_padrao, test_silver_troca_de_tipo_recusada, test_silver_coluna_removida_recusada, test_silver_evolucao_desligada_recusa, test_ingestao_evolui_por_padrao e test_ingestao_repassa_o_sinalizador. Nenhum cenário usa skip, xfail ou importorskip; os testes gravam só em tmp_path, nunca no MinIO; nenhuma função para a sessão Spark da suíte.

## Success Criteria

```bash
# eval_1: A Silver evolui por padrão
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in silver_evolui_por_padrao silver_troca_de_tipo_recusada silver_coluna_removida_recusada silver_evolucao_desligada_recusa; do python3 -m pytest --collect-only -q tests/test_delta_padroes_silver.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_delta_padroes_silver.py -k "silver_evolui_por_padrao or silver_troca_de_tipo_recusada or silver_coluna_removida_recusada or silver_evolucao_desligada_recusa"'
}

# eval_2: A ingestão evolui e repassa
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in ingestao_evolui_por_padrao ingestao_repassa_o_sinalizador; do python3 -m pytest --collect-only -q tests/test_delta_padroes_silver.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_delta_padroes_silver.py -k "ingestao_evolui_por_padrao or ingestao_repassa_o_sinalizador"'
}

# eval_3: O que existia segue igual
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in resolve_versao_uma_vez metadados_do_commit_dono_da_competencia reverte_so_a_competencia; do python3 -m pytest --collect-only -q tests/test_silver.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_silver.py -k "resolve_versao_uma_vez or metadados_do_commit_dono_da_competencia or reverte_so_a_competencia"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A Silver evolui por padrão"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "A ingestão evolui e repassa"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "O que existia segue igual"
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

cargas da Silver recusadas por coluna nova

## Anti-Patterns

- Do not desligar a guarda verificar_evolucao: troca de tipo passaria (Regra 5); instead manter antes do mergeSchema.
- Do not editar um teste existente: acrescentar, não mudar; instead arquivo novo.
- Do not mudar publicar_competencia: fica False por decisão (ADR 0017); instead só as entradas.

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
- `src/medalhao/gold.py`
- `src/medalhao/gold_assuntos.py`
- `tests/test_delta_padroes.py`

## Open Questions

(none — this task is fully specified)
