---
id: T-20260925-gold-evolui-por-padrao
title: "A Gold evolui por padrão"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260925-silver-e-ingestao-evoluem-por-padrao]
supersedes: (none)
touches_paths: [src/medalhao/gold.py, tests/test_gold_nome_oficial.py]
creates_paths: []
source_note: "seamwise/legs/LEG-GOLD-EVOLUI.md#T-20260925-gold-evolui-por-padrao"
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
signed_off_at: 2026-09-25T18:03:17Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:879829b5b138f3fd9c4695fcdcaf181f821d62bd640f93471fe6cb68f7066ba1
---

# A Gold evolui por padrão

> **Why:** Fazer a Gold principal evoluir de forma aditiva por padrão. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Fazer a Gold principal evoluir de forma aditiva por padrão. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-PRATICAS-DELTA; seam SEAM-GOLD-EVOLUI; swimlane LANE-GOLD-EVOLUI; capability leg LEG-GOLD-EVOLUI. Done condition: publicar, executar_gold e executar_gold_da_silver têm evolucao_aditiva=True por padrão; em tests/test_gold_nome_oficial.py muda só o teste nomeado e entra o novo; todos passam.

## Behavior

- **B-1** — GIVEN uma Gold de 4 colunas já publicada em tmp_path WHEN a Gold publica com nome_oficial SEM passar evolucao_aditiva THEN publicar, executar_gold e executar_gold_da_silver têm evolucao_aditiva=True por padrão: a coluna nova entra e a outra competência fica intacta; com evolucao_aditiva=False explícito, recusa como antes; a guarda recusa troca de tipo.
- **B-2** — GIVEN o tests/test_gold_nome_oficial.py da receita D, que esperava recusa SEM o sinalizador WHEN a tarefa atualiza os testes THEN EXATAMENTE isto, e nada mais: em test_tabela_de_quatro_colunas_evolui_aditiva, a asserção de recusa sem o sinalizador passa a usar evolucao_aditiva=False EXPLÍCITO; entra test_gold_evolui_por_padrao_sem_sinalizador, que chama executar_gold_da_silver — a entrada da carga real — sem passar evolucao_aditiva, e não só publicar; os demais test_* do arquivo ficam como estão; test_gold.py não é tocado. Nenhum cenário usa skip, xfail ou importorskip; os testes gravam só em tmp_path, nunca no MinIO; nenhuma função para a sessão Spark da suíte.

## Success Criteria

```bash
# eval_1: A Gold evolui por padrão
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_evolui_por_padrao_sem_sinalizador tabela_de_quatro_colunas_evolui_aditiva; do python3 -m pytest --collect-only -q tests/test_gold_nome_oficial.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_nome_oficial.py -k "gold_evolui_por_padrao_sem_sinalizador or tabela_de_quatro_colunas_evolui_aditiva"'
}

# eval_2: O nome oficial segue igual
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in nome_oficial_vem_da_silver_especie controles_iguais_com_e_sem_nome; do python3 -m pytest --collect-only -q tests/test_gold_nome_oficial.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_nome_oficial.py -k "nome_oficial_vem_da_silver_especie or controles_iguais_com_e_sem_nome"'
}

# eval_3: A Gold existente segue igual
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in commit_carrega_a_forma publica_em_um_unico_commit reconfere_multiconjunto_das_linhas; do python3 -m pytest --collect-only -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold.py -k "commit_carrega_a_forma or publica_em_um_unico_commit or reconfere_multiconjunto_das_linhas"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A Gold evolui por padrão"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "O nome oficial segue igual"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A Gold existente segue igual"
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

Gold recusada por coluna nova

## Anti-Patterns

- Do not tocar test_gold.py: a guarda test_testes_leves protege os corpos; instead só o arquivo do nome oficial.
- Do not apagar a asserção de recusa: a recusa com False explícito continua sendo contrato; instead trocar para False explícito.
- Do not desligar a guarda: Regra 5; instead manter verificar_evolucao.

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
- `src/medalhao/gold_assuntos.py`
- `tests/test_assuntos_nome_oficial.py`

## Open Questions

(none — this task is fully specified)
