---
id: T-20260923-ingestao-julgada
title: "Julgar a ingestão com o segundo motor e publicar a Bronze só com ACEITO"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [src/medalhao/bronze.py]
creates_paths: [src/medalhao/ingestao.py, tests/test_ingestao.py]
source_note: "seamwise/legs/LEG-JUIZO-NA-INGESTAO.md#T-20260923-ingestao-julgada"
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
signed_off_at: 2026-09-23T21:44:32Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:1daaa60bc594b0cd2505d92b234ff6a875401df90805a5ff2f13821cd74a0f83
---

# Julgar a ingestão com o segundo motor e publicar a Bronze só com ACEITO

> **Why:** Ler o arquivo bruto uma vez, na ingestão, com os dois motores.

## Goal

Ler o arquivo bruto uma vez, na ingestão, com os dois motores.

## Context

Intent DI-PDA-MEDALHAO-V4; seam SEAM-JUIZO-NA-INGESTAO; swimlane LANE-JUIZO-NA-INGESTAO; capability leg LEG-JUIZO-NA-INGESTAO. Done condition: Sobre uma landing vinculada, conduzir julga a Bronze contra o CSV; só com autorizado_publicar a Bronze publica, e o commit nomeia o pacote; sem autorização, nada é publicado.

## Behavior

- **B-1** — GIVEN a landing vinculada ao CSV, o contrato e o CSV original em _raw/ WHEN a ingestão roda para a competência THEN chama orquestracao.conduzir com um executar_leitura que mede a Bronze no motor Spark SEM gravar e lê o CSV pelo segundo motor, o leitor posicional em Python já selado, montando InsumosExecucao; só com Desfecho.autorizado_publicar a Bronze publica pelo protocolo que já existe — preparo, replaceWhere, reconferência —, e o userMetadata do commit nomeia o caminho_pacote e o sha256 do pacote do juízo. O orquestrador e o juiz selados são reusados, nunca alterados. O que publica é o MESMO resultado medido dentro do executar_leitura — nunca uma segunda leitura da landing —, e a reconferência depois de publicar compara a Bronze publicada com os cinco controles e o total_por_codigo que o pacote JULGOU, não só com o próprio preparo.
- **B-2** — GIVEN um juízo que não autoriza — RECUSADO, ERRO ou ACEITO_SEM_ANCORA WHEN a ingestão termina THEN a Bronze não publica nada, o pacote do juízo fica gravado como evidência com o motivo, e a ingestão devolve o veredito do orquestrador sem traduzi-lo; nenhum teste já existente de tests/test_bronze.py é editado.

## Success Criteria

```bash
# eval_1: O juízo acontece na ingestão, com os dois motores
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in julga_na_ingestao_com_segundo_motor publica_bronze_so_com_aceito commit_da_bronze_nomeia_o_pacote publicado_confere_com_o_julgado; do python3 -m pytest --collect-only -q tests/test_ingestao.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_ingestao.py -k "julga_na_ingestao_com_segundo_motor or publica_bronze_so_com_aceito or commit_da_bronze_nomeia_o_pacote or publicado_confere_com_o_julgado"'
}

# eval_2: Sem autorização, nada publica
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in recusado_nao_publica erro_nao_publica pacote_fica_como_evidencia; do python3 -m pytest --collect-only -q tests/test_ingestao.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_ingestao.py -k "recusado_nao_publica or erro_nao_publica or pacote_fica_como_evidencia"'
}

# eval_3: Orquestrador reusado, não alterado
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reusa_conduzir_selado reusa_leitor_posicional; do python3 -m pytest --collect-only -q tests/test_ingestao.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_ingestao.py -k "reusa_conduzir_selado or reusa_leitor_posicional"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "O juízo acontece na ingestão, com os dois motores"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Sem autorização, nada publica"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Orquestrador reusado, não alterado"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
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

Reverter src/medalhao/bronze.py; remover ingestao.py e seu teste.

## Observability Hooks

competências com Bronze publicada sem pacote no commit

## Anti-Patterns

- Do not reimplementar o juiz ou o orquestrador dentro da ingestão: são selados; uma segunda versão pode divergir em silêncio; instead chamar orquestracao.conduzir.
- Do not ler o CSV pelo Spark no lugar do leitor Python: dois motores iguais não se conferem (ADR 0006); instead usar o leitor posicional já selado.
- Do not publicar a Bronze antes do veredito: publicação sem juízo é o que o portão existe para impedir; instead publicar só com autorizado_publicar.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/pda`

## Open Questions

(none — this task is fully specified)
