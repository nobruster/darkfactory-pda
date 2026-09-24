---
id: T-20260924-testes-leves
title: "Cenário de teste montado uma vez por módulo"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-perf-gold]
supersedes: (none)
touches_paths: [tests/test_gold.py, tests/test_gold_assuntos.py]
creates_paths: [tests/test_testes_leves.py]
source_note: "seamwise/legs/LEG-TESTES-LEVES.md#T-20260924-testes-leves"
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
signed_off_at: 2026-09-24T16:52:07Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-24T18:02:02Z
signed_off_sig: hmac-sha256-v3:85d3c104:c9ea2a0ec86df6add8036d6dd8139fa318214be192ea67815caa2cbe1b0b38ec
accepted_tier: 1
accepted_attempt_id: 0b266bbc-260a-417f-8022-98520337f685
accepted_authorization_ref: hmac-sha256-v3:85d3c104:c9ea2a0ec86df6add8036d6dd8139fa318214be192ea67815caa2cbe1b0b38ec
acceptance_record_digest: sha256:a412d593a68f759a5eda766bd602bed41c6758f67a4eaad1a252c354f0992e3a
---

# Cenário de teste montado uma vez por módulo

> **Why:** Tirar dos testes a montagem da cadeia real a cada teste. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>` — outras formas são recusadas pela permissão.

## Goal

Tirar dos testes a montagem da cadeia real a cada teste. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>` — outras formas são recusadas pela permissão.

## Context

Intent DI-PDA-PERFORMANCE; seam SEAM-TESTES-LEVES; swimlane LANE-TESTES-LEVES; capability leg LEG-TESTES-LEVES. Done condition: Os mesmos ids de teste de tests/test_gold.py e tests/test_gold_assuntos.py são coletados, nenhuma linha dentro de uma função test_* mudou, todos passam, e test_gold_assuntos leva menos da metade dos 551s medidos.

## Behavior

- **B-1** — GIVEN os auxiliares _cenario, _cadeia_publicada e _preparar, que montam a cadeia real por teste WHEN os testes rodam THEN a cadeia do cenário é montada UMA vez por módulo numa fixture e cada teste recebe uma CÓPIA do diretório — tabelas Delta locais com caminhos relativos no _delta_log, contrato e lago de teste reescritos para a cópia —, isolando os testes entre si como antes — provado por um cenário que republica numa cópia e confere que o cenário-base e outra cópia ficam intactos; SÓ os auxiliares e as fixtures mudam, e nenhuma linha dentro de uma função test_* é alterada.
- **B-2** — GIVEN a suíte depois da mudança WHEN é coletada e executada THEN coleta EXATAMENTE os mesmos ids de teste de antes, todos passam, nenhum é marcado skip ou xfail, e o diff de cada função test_* contra o commit anterior é vazio — verificado por um teste que compara o corpo das funções pela AST; test_gold_assuntos leva menos da metade dos 551s medidos.

## Success Criteria

```bash
# eval_1: Cenário uma vez, cópia por teste
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_especie_fecha_com_a_ancora le_silver_por_versao usa_a_silver_nomeada_pela_gold; do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py -k "fat_especie_fecha_com_a_ancora or le_silver_por_versao or usa_a_silver_nomeada_pela_gold"'
}

# eval_2: Nenhuma asserção mudou
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in mesmos_ids_coletados corpo_das_funcoes_test_intacto nenhum_skip_ou_xfail copia_isolada_do_cenario_base; do python3 -m pytest --collect-only -q tests/test_testes_leves.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_testes_leves.py -k "mesmos_ids_coletados or corpo_das_funcoes_test_intacto or nenhum_skip_ou_xfail or copia_isolada_do_cenario_base"'
}

# eval_3: A Gold continua verde
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_le_so_a_silver linhagem_ate_pacote_aceito gold_da_silver_fecha_com_a_ancora; do python3 -m pytest --collect-only -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold.py -k "gold_le_so_a_silver or linhagem_ate_pacote_aceito or gold_da_silver_fecha_com_a_ancora"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Cenário uma vez, cópia por teste"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Nenhuma asserção mudou"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A Gold continua verde"
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

- Do not editar uma linha dentro de uma função test_*: muda o que o teste prova; instead mudar só auxiliares e fixtures.
- Do not marcar teste lento como skip ou xfail: é afrouxar o gate (Regra 3); instead barateá-lo pela fixture.
- Do not compartilhar o MESMO diretório entre testes: um teste que republica contamina o outro; instead uma cópia por teste.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src`

## Open Questions

(none — this task is fully specified)
