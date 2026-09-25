---
id: T-20260924-vinculador-gramatica
title: "O vinculador de procedência com a mesma gramática do gravador"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-produtor-e-gravador-corrigem]
supersedes: (none)
touches_paths: [src/produtor/vincular_procedencia.py, tests/test_vincular_procedencia.py]
creates_paths: []
source_note: "seamwise/legs/LEG-VINCULADOR-GRAMATICA.md#T-20260924-vinculador-gramatica"
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
signed_off_at: 2026-09-25T00:26:45Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:2e7efe519a52bdd1910c02cc0da5ea991fdb1922a7703fc3f192b3f3e0ede5e7
---

# O vinculador de procedência com a mesma gramática do gravador

> **Why:** Fazer o vinculador medir a partição pela mesma gramática com que o gravador a gravou. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Fazer o vinculador medir a partição pela mesma gramática com que o gravador a gravou. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-CORRIGE-PRODUTOR; seam SEAM-VINCULADOR-GRAMATICA; swimlane LANE-VINCULADOR-GRAMATICA; capability leg LEG-VINCULADOR-GRAMATICA. Done condition: src/produtor/vincular_procedencia.py usa gramatica.valor_decimal; os testes existentes de tests/test_vincular_procedencia.py passam sem edição; os testes novos provam que vinculador e gravador medem igual e que o vinculador prova uma partição gravada pelo gravador corrigido.

## Behavior

- **B-1** — GIVEN um CSV em tmp_path com '1,5', '-5,00' e valores válidos WHEN o main do gravador corrigido grava esse CSV em tmp_path, num processo filho sem S3_*, e vincular_procedencia.vincular confere a partição gravada THEN ler_fonte usa gramatica.valor_decimal — a regex local sai de vincular_procedencia.py —, os cinco controles de ler_fonte e de gravar_lago._ler_fonte sobre o mesmo CSV são iguais, e o vínculo da partição gravada pelo gravador corrigido é GRAVADO; a declaração de ANSI que já existe fica; nenhuma outra função muda de comportamento.
- **B-2** — GIVEN o tests/test_vincular_procedencia.py selado WHEN a tarefa acrescenta os testes novos THEN todos os test_* existentes ficam como estão e passam; entram só test_vinculador_usa_a_gramatica_do_juiz, test_vinculador_e_gravador_medem_igual e test_vinculador_prova_particao_do_gravador_corrigido. Nenhum cenário usa skip, xfail ou importorskip.

## Success Criteria

```bash
# eval_1: A mesma gramática, e a partição gravada provada
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in vinculador_usa_a_gramatica_do_juiz vinculador_e_gravador_medem_igual vinculador_prova_particao_do_gravador_corrigido; do python3 -m pytest --collect-only -q tests/test_vincular_procedencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_vincular_procedencia.py -k "vinculador_usa_a_gramatica_do_juiz or vinculador_e_gravador_medem_igual or vinculador_prova_particao_do_gravador_corrigido"'
}

# eval_2: A prova segue igual
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grava_manifesto_hash_e_controles rele_o_que_gravou valor_em_decimal_nunca_float; do python3 -m pytest --collect-only -q tests/test_vincular_procedencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_vincular_procedencia.py -k "grava_manifesto_hash_e_controles or rele_o_que_gravou or valor_em_decimal_nunca_float"'
}

# eval_3: As recusas seguem iguais
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in zero_linhas_e_nao_medido prova_identica_nao_regrava hash_divergente_nao_grava; do python3 -m pytest --collect-only -q tests/test_vincular_procedencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_vincular_procedencia.py -k "zero_linhas_e_nao_medido or prova_identica_nao_regrava or hash_divergente_nao_grava"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A mesma gramática, e a partição gravada provada"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "A prova segue igual"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "As recusas seguem iguais"
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

Reverter src/produtor/vincular_procedencia.py e tests/test_vincular_procedencia.py ao commit anterior.

## Observability Hooks

vínculo divergente do gravador

## Anti-Patterns

- Do not editar um teste existente: a tarefa só troca a gramática; instead só acrescentar.
- Do not regravar a _PROCEDENCIA.json da 2026-01: a prova anterior nunca é sobrescrita; instead o 2026-01 não muda com a gramática nova.
- Do not copiar a regex de novo: é a duplicação que criou a divergência; instead importar gramatica.

## Do-Not-Touch

- `_raw`
- `contracts`
- `cvg/docs/adrs`
- `src/pda`
- `src/medalhao`
- `src/ontologia`
- `infra`
- `src/produtor/gramatica.py`
- `tests/test_gramatica.py`
- `src/produtor/spark_produtor.py`
- `src/produtor/gravar_lago.py`
- `tests/test_produtor.py`

## Open Questions

(none — this task is fully specified)
