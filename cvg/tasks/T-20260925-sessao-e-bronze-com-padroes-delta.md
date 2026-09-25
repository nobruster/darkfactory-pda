---
id: T-20260925-sessao-e-bronze-com-padroes-delta
title: "A sessão declara o que herdava, e a Bronze evolui por padrão"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [src/medalhao/bronze.py]
creates_paths: [tests/test_delta_padroes.py]
source_note: "seamwise/legs/LEG-SESSAO-E-BRONZE.md#T-20260925-sessao-e-bronze-com-padroes-delta"
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
signed_off_at: 2026-09-25T18:02:01Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:d429a8c1aece7b9dca52d0acf3250a97f3662cdfd9ab24690129466f9db7ce11
---

# A sessão declara o que herdava, e a Bronze evolui por padrão

> **Why:** Fazer criar_sessao declarar as práticas do KB e a retenção de tabela nova, e a Bronze evoluir de forma aditiva por padrão. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Fazer criar_sessao declarar as práticas do KB e a retenção de tabela nova, e a Bronze evoluir de forma aditiva por padrão. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-PRATICAS-DELTA; seam SEAM-SESSAO-E-BRONZE; swimlane LANE-SESSAO-E-BRONZE; capability leg LEG-SESSAO-E-BRONZE. Done condition: criar_sessao declara as cinco chaves; executar_leitura e publicar_bronze têm evolucao_aditiva=True por padrão; publicar_competencia segue False; os testes de tests/test_delta_padroes.py passam.

## Behavior

- **B-1** — GIVEN uma sessão criada por bronze.criar_sessao e tabelas Delta em tmp_path WHEN a sessão é criada e a Bronze publica THEN criar_sessao declara, no builder E por spark.conf.set (getOrCreate reaproveita sessão), spark.databricks.delta.schema.autoMerge.enabled=false, spark.databricks.delta.retentionDurationCheck.enabled=true, spark.databricks.delta.replaceWhere.constraintCheck.enabled=true, spark.databricks.delta.properties.defaults.logRetentionDuration='interval 1825 days' e spark.databricks.delta.properties.defaults.deletedFileRetentionDuration='interval 1825 days', com a retenção numa constante nomeada RETENCAO_PADRAO; uma tabela Delta NOVA nasce com as duas propriedades; uma tabela já existente reentrada por createIfNotExists não ganha propriedade nem commit; executar_leitura e publicar_bronze passam a ter evolucao_aditiva=True por padrão — coluna nova entra —, e a guarda verificar_evolucao continua recusando troca de tipo e coluna removida mesmo por padrão; publicar_competencia MANTÉM evolucao_aditiva=False.
- **B-2** — GIVEN o test_bronze.py e o test_performance.py selados WHEN a tarefa termina THEN nenhum teste existente muda e todos passam — test_schema_evolucao_so_aditiva segue válido porque exercita publicar_competencia, que fica False; em tests/test_delta_padroes.py entram test_sessao_declara_as_tres_praticas, test_tabela_nova_nasce_com_retencao_de_cinco_anos, test_tabela_existente_reentrada_sem_commit, test_bronze_evolui_coluna_nova_por_padrao, test_bronze_troca_de_tipo_recusada_mesmo_por_padrao, test_bronze_coluna_removida_recusada, test_bronze_evolucao_desligada_recusa e test_publicar_competencia_segue_desligado. Nenhum cenário usa skip, xfail ou importorskip; os testes gravam só em tmp_path, nunca no MinIO; nenhuma função para a sessão Spark da suíte.

## Success Criteria

```bash
# eval_1: A sessão e a retenção de tabela nova
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sessao_declara_as_tres_praticas tabela_nova_nasce_com_retencao_de_cinco_anos tabela_existente_reentrada_sem_commit; do python3 -m pytest --collect-only -q tests/test_delta_padroes.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_delta_padroes.py -k "sessao_declara_as_tres_praticas or tabela_nova_nasce_com_retencao_de_cinco_anos or tabela_existente_reentrada_sem_commit"'
}

# eval_2: A Bronze evolui por padrão, com a guarda
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in bronze_evolui_coluna_nova_por_padrao bronze_troca_de_tipo_recusada_mesmo_por_padrao bronze_coluna_removida_recusada bronze_evolucao_desligada_recusa publicar_competencia_segue_desligado; do python3 -m pytest --collect-only -q tests/test_delta_padroes.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_delta_padroes.py -k "bronze_evolui_coluna_nova_por_padrao or bronze_troca_de_tipo_recusada_mesmo_por_padrao or bronze_coluna_removida_recusada or bronze_evolucao_desligada_recusa or publicar_competencia_segue_desligado"'
}

# eval_3: O que existia segue igual
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in schema_evolucao_so_aditiva replacewhere_nao_toca_outra_competencia commit_carrega_a_forma; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "schema_evolucao_so_aditiva or replacewhere_nao_toca_outra_competencia or commit_carrega_a_forma"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A sessão e a retenção de tabela nova"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "A Bronze evolui por padrão, com a guarda"
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

sessões e tabelas sem as práticas declaradas

## Anti-Patterns

- Do not mudar o padrão de publicar_competencia: ligaria a evolução em silêncio nos preparos e na especie; instead só as funções de entrada.
- Do not ligar schema.autoMerge: é mergeSchema sem guarda; instead declarar false.
- Do not ALTER TABLE dentro de _garantir_tabela: quebra reentrada sem commit; instead propriedade padrão da sessão.

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
- `src/medalhao/silver.py`
- `src/medalhao/ingestao.py`
- `src/medalhao/gold.py`
- `src/medalhao/gold_assuntos.py`

## Open Questions

(none — this task is fully specified)
