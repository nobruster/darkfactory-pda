---
id: T-20260924-perf-gold
title: "Cache liberado e constraints num commit só na Gold"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [src/medalhao/gold.py, src/medalhao/gold_assuntos.py]
creates_paths: [tests/test_performance_gold.py]
source_note: "seamwise/legs/LEG-PERF-GOLD.md#T-20260924-perf-gold"
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
signed_off_at: 2026-09-24T16:05:43Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:34117010bd08a87c77237f73ecf4930dbc13625382796de2c10065a70f1a11fd
---

# Cache liberado e constraints num commit só na Gold

> **Why:** Baixar o custo da Gold e dos assuntos sem mudar a saída. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>` — outras formas são recusadas pela permissão.

## Goal

Baixar o custo da Gold e dos assuntos sem mudar a saída. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>` — outras formas são recusadas pela permissão.

## Context

Intent DI-PDA-PERFORMANCE; seam SEAM-PERF-GOLD; swimlane LANE-PERF-GOLD; capability leg LEG-PERF-GOLD. Done condition: A Gold e os assuntos reais saem idênticos à produção. O PERF=MELHOR contra perf/ é VERIFICAÇÃO PÓS-ASSENTAMENTO: roda na execução real com a skill spark-perf, fora do loop, porque tempo medido dentro de eval é instável; a entrega exige saída idêntica e o comportamento declarado.

## Behavior

- **B-1** — GIVEN a Gold principal e os assuntos publicando a competência WHEN rodam THEN todo DataFrame persistido é liberado com unpersist num finally, em TODOS os caminhos — publicado, divergente, CHECK que recusou ou exceção de escrita —, e nunca antes da reconferência; uma tabela NOVA de assuntos nasce com os CHECK POR COLUNA — os mesmos nomes <coluna>_nao_negativo que já existem — declarados NO PRÓPRIO CREATE, pelo builder do Delta: um commit em vez de sete, e medido que o Delta 3.2.1 aceita e aplica; uma tabela que já existe com esses CHECK é reconhecida como protegida, sem receber constraint nova nem perder as antigas, e a reentrada não adiciona nada; a reconferência passa a uma passada como na Bronze. O ganho só vale com o gate da skill spark-perf: PERF=MELHOR contra a baseline gravada em perf/, com a saída IDÊNTICA à de produção — controles e multiconjunto 0/0. Otimização que muda o número é defeito, não ganho; nenhuma reconferência é removida, só barateada.
- **B-2** — GIVEN uma saída com valor monetário negativo ou uma linha trocada WHEN a publicação roda THEN os CHECK criados no CREATE recusam o negativo exatamente como os adicionados por ALTER recusavam, e a reconferência numa passada devolve DIVERGE; nada é publicado; nenhum teste já existente de tests/test_gold.py ou tests/test_gold_assuntos.py é editado.

## Success Criteria

```bash
# eval_1: Cache liberado e um CHECK só
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_unpersist_depois_de_publicar checks_no_proprio_create tabela_existente_reconhecida gold_unpersist_tambem_na_falha; do python3 -m pytest --collect-only -q tests/test_performance_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_performance_gold.py -k "gold_unpersist_depois_de_publicar or checks_no_proprio_create or tabela_existente_reconhecida or gold_unpersist_tambem_na_falha"'
}

# eval_2: A proteção é a mesma
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in checks_do_create_recusam_negativo gold_uma_passada_diverge_linha_trocada; do python3 -m pytest --collect-only -q tests/test_performance_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_performance_gold.py -k "checks_do_create_recusam_negativo or gold_uma_passada_diverge_linha_trocada"'
}

# eval_3: Nada do comportamento selado mudou
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in check_nao_negativo_monetario fat_especie_fecha_com_a_ancora publica_com_replacewhere; do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py -k "check_nao_negativo_monetario or fat_especie_fecha_com_a_ancora or publica_com_replacewhere"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Cache liberado e um CHECK só"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "A proteção é a mesma"
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

- Do not tirar o CHECK monetário: é o domínio da ADR 0009; instead os mesmos CHECK por coluna, criados no CREATE.
- Do not dropar os seis CHECK de uma tabela existente: desproteger para trocar é janela sem domínio; instead reconhecer os seis como proteção equivalente.
- Do not unpersist antes da reconferência: releria a origem; instead liberar depois de publicado e reconferido.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/pda`
- `src/medalhao/bronze.py`
- `src/medalhao/silver.py`

## Open Questions

(none — this task is fully specified)
