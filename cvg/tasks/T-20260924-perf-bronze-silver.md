---
id: T-20260924-perf-bronze-silver
title: "Memória declarada, cache liberado e reconferência numa passada"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [src/medalhao/bronze.py, src/medalhao/silver.py]
creates_paths: [tests/test_performance.py]
source_note: "seamwise/legs/LEG-PERF-BRONZE-SILVER.md#T-20260924-perf-bronze-silver"
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
signed_off_at: 2026-09-24T14:45:18Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:d6d7c6fc998c8191c20c844f24ce201b4ac87ab6e4679901001811b5574ecb7a
---

# Memória declarada, cache liberado e reconferência numa passada

> **Why:** Baixar executor, shuffle e spill da Bronze e da Silver sem mudar a saída.

## Goal

Baixar executor, shuffle e spill da Bronze e da Silver sem mudar a saída.

## Context

Intent DI-PDA-PERFORMANCE; seam SEAM-PERF-BRONZE-SILVER; swimlane LANE-PERF-BRONZE-SILVER; capability leg LEG-PERF-BRONZE-SILVER. Done condition: Bronze e Silver reais saem idênticas à produção. O PERF=MELHOR contra perf/ é VERIFICAÇÃO PÓS-ASSENTAMENTO: roda na execução real com a skill spark-perf, fora do loop, porque tempo medido dentro de eval é instável; a entrega exige saída idêntica e o comportamento declarado.

## Behavior

- **B-1** — GIVEN a sessão criada por criar_sessao e as leituras e gravações da Bronze e da Silver WHEN Bronze e Silver rodam THEN criar_sessao DECLARA spark.driver.memory, spark.sql.adaptive.enabled e spark.sql.shuffle.partitions a partir de parâmetros com padrão explícito — nunca herda — e confere depois de criar o heap EFETIVO da JVM — Runtime.getRuntime().maxMemory() por spark._jvm, não a propriedade de configuração, que não prova nada numa JVM já iniciada —, recusando sessão cujo heap efetivo seja menor que o declarado; todo DataFrame persistido é liberado com unpersist num finally, em TODOS os caminhos — publicado, divergente, CHECK que recusou ou exceção de escrita —, e nunca antes da reconferência, inclusive no caminho INTEGRO; e a reconferência de _conferir_tabela passa a UMA passada: um exceptAll e a igualdade das contagens — multiconjuntos de mesmo tamanho em que um está contido no outro são iguais —, provando o mesmo que os dois exceptAll. O ganho só vale com o gate da skill spark-perf: PERF=MELHOR contra a baseline gravada em perf/, com a saída IDÊNTICA à de produção — controles e multiconjunto 0/0. Otimização que muda o número é defeito, não ganho; nenhuma reconferência é removida, só barateada.
- **B-2** — GIVEN uma saída alterada — linha trocada, centavo a mais ou linha a menos WHEN a reconferência numa passada roda THEN acusa exatamente o que os dois exceptAll acusavam: DIVERGE com a diferença nomeada, e nada é publicado; nenhum teste já existente de tests/test_bronze.py ou tests/test_silver.py é editado.

## Success Criteria

```bash
# eval_1: Memória declarada e cache liberado
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sessao_declara_memoria sessao_com_memoria_herdada_recusada unpersist_depois_de_publicar heap_efetivo_conferido_pela_jvm unpersist_tambem_na_falha; do python3 -m pytest --collect-only -q tests/test_performance.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_performance.py -k "sessao_declara_memoria or sessao_com_memoria_herdada_recusada or unpersist_depois_de_publicar or heap_efetivo_conferido_pela_jvm or unpersist_tambem_na_falha"'
}

# eval_2: Uma passada prova o mesmo que duas
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in uma_passada_igual_a_duas linha_trocada_diverge centavo_a_mais_diverge linha_a_menos_diverge; do python3 -m pytest --collect-only -q tests/test_performance.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_performance.py -k "uma_passada_igual_a_duas or linha_trocada_diverge or centavo_a_mais_diverge or linha_a_menos_diverge"'
}

# eval_3: Nada do comportamento selado mudou
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in cinco_controles reconfere_no_preparo_antes_de_publicar reverte_so_a_competencia; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "cinco_controles or reconfere_no_preparo_antes_de_publicar or reverte_so_a_competencia"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Memória declarada e cache liberado"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Uma passada prova o mesmo que duas"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Nada do comportamento selado mudou"
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

- Do not remover um exceptAll sem a igualdade de contagem: prova só um sentido; instead um exceptAll E contagens iguais.
- Do not definir a memória por PYSPARK_SUBMIT_ARGS no código: esconde a declaração fora da sessão; instead declarar no builder de criar_sessao e conferir.
- Do not chamar unpersist antes de reconferir: a reconferência releria da origem; instead liberar só depois de publicado e reconferido.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/pda`

## Open Questions

(none — this task is fully specified)
