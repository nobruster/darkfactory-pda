---
id: T-20260917-leitura-competencia
title: "Ler a competência sem alterar a fonte"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260917-contrato-ancora]
supersedes: (none)
touches_paths: []
creates_paths: [src/fabrica/leitura.py, tests/test_leitura.py, tests/fixtures/competencia-min.csv]
source_note: "seamwise/legs/LEG-LEITURA-NAO-ALTERA-FONTE.md#T-20260917-leitura-competencia"
created: "2026-09-17T00:00:00Z"
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
signed_off: false
signed_off_by: (none)
signed_off_at: (none)
accepted: false
accepted_by: (none)
accepted_at: (none)
---

# Ler a competência sem alterar a fonte

> **Why:** Extrair registros preservando os bytes originais.

## Goal

Extrair registros preservando os bytes originais.

## Context

Intent DI-FABRICA-COMPETENCIA; seam SEAM-LEITURA; swimlane LANE-LEITURA; capability leg LEG-LEITURA-NAO-ALTERA-FONTE. Done condition: O sha256 do arquivo é idêntico antes e depois, e a contagem de registros bate com a âncora.

## Behavior

- **B-1** — GIVEN o arquivo de uma competência e o layout declarado no contrato (posições, formato monetário, chave do registro) WHEN a leitura termina THEN o sha256 do arquivo é idêntico ao de antes, e cada campo lido vem da POSIÇÃO declarada — cabeçalho repetido não decide nada
- **B-2** — GIVEN o arquivo de 2026-03, com um registro cujo campo monetário é ilegível WHEN os registros são contados e a leitura termina THEN a contagem bate com a do contrato para aquele arquivo — 41719140 na fonte real de 2026-03, o valor do fixture nos testes —, o registro ilegível entra em linhas_invalidas e NÃO entra em sum/min/max, e o defeito sai com identidade, valor original e posição

## Success Criteria

```bash
# eval_1: Fonte byte-idêntica; leitura posicional com cabeçalho repetido
eval_1() {
  pytest -q tests/test_leitura.py -k "sha256 or posicional"
}

# eval_2: Contagem bate com a âncora e o defeito sai com identidade
eval_2() {
  pytest -q tests/test_leitura.py -k "contagem or defeito_identificado"
}

# eval_3: A leitura reporta seus segundos para a orquestração medir o total
eval_3() {
  pytest -q tests/test_leitura.py -k reporta_duracao
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Fonte byte-idêntica; leitura posicional com cabeçalho repetido"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Contagem bate com a âncora e o defeito sai com identidade"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A leitura reporta seus segundos para a orquestração medir o total"
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
  required_tools: [git, bash, python3, pytest]
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

Remover o leitor e seus testes.

## Observability Hooks

contagem de registros lidos por competência, defeitos observados por tipo, e segundos do início da leitura ao veredito (o limite de R-6, sem o qual tudo passa mesmo levando horas — objeção C7)

## Anti-Patterns

- Do not escrever no arquivo de origem: destrói a prova de que a origem publicou aquilo; instead tratar a origem como somente leitura.
- Do not corrigir valor malformado durante a leitura: apaga o defeito antes da classificação; instead preservar e deixar o juízo classificar.
- Do not ler colunas por nome de cabeçalho: cabeçalho com nome repetido faz perder a coluna em silêncio; instead ler por posição declarada no contrato.

## Do-Not-Touch

- `_raw`

## Open Questions

(none — this task is fully specified)
