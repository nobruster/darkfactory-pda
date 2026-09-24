---
id: T-20260923-contrato-expoe-grupos
title: "Expor grupos_especie no Contrato carregado"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [src/pda/contrato.py, tests/test_contrato.py]
creates_paths: []
source_note: "seamwise/legs/LEG-CONTRATO-EXPOE-GRUPOS.md#T-20260923-contrato-expoe-grupos"
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
signed_off_at: 2026-09-23T21:44:02Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-23T22:30:29Z
signed_off_sig: hmac-sha256-v3:85d3c104:c2e9353ee0a482e255ca08ba369c7000a8f143545268ff06026cde3bdb18e8e1
accepted_tier: 1
accepted_attempt_id: db692ee9-452f-49f1-ac7a-88994ab96b33
accepted_authorization_ref: hmac-sha256-v3:85d3c104:c2e9353ee0a482e255ca08ba369c7000a8f143545268ff06026cde3bdb18e8e1
acceptance_record_digest: sha256:96613f808cf96e43801f54712d9d529bad4d76c409672918fd9b5619a94c6088
---

# Expor grupos_especie no Contrato carregado

> **Why:** Fazer o objeto carregado dizer o mapa de grupos que o YAML aprova.

## Goal

Fazer o objeto carregado dizer o mapa de grupos que o YAML aprova.

## Context

Intent DI-PDA-MEDALHAO-V4; seam SEAM-CONTRATO-GRUPOS; swimlane LANE-CONTRATO-GRUPOS; capability leg LEG-CONTRATO-EXPOE-GRUPOS. Done condition: O contrato real expõe grupos_especie com 5 grupos e 65 códigos; um contrato sem o bloco carrega com None; bloco inválido é recusado; e toda a suíte já existente de tests/test_contrato.py passa sem edição.

## Behavior

- **B-1** — GIVEN o contrato real da competência 2026-01, com grupos_especie aprovado WHEN o contrato é carregado THEN o Contrato expõe grupos_especie com aprovador, data, regra e a lista de grupos, cada um com seu nome e os códigos como TEXTO, lidos do MESMO carregamento; um contrato sem o bloco carrega com None, e é o consumidor que o exige.
- **B-2** — GIVEN um bloco grupos_especie presente e inválido WHEN o contrato é carregado THEN é RECUSADO no carregamento: código repetido entre grupos, código que não é texto, grupo sem códigos, aprovação sem aprovador ou data, ou total de códigos distintos diferente de cardinalidade.codigos_distintos. Nenhum teste já existente de tests/test_contrato.py é editado.

## Success Criteria

```bash
# eval_1: Os grupos expostos, opcionais, em texto
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in expoe_grupos_especie grupos_ausentes_viram_none codigos_de_grupo_sao_texto; do python3 -m pytest --collect-only -q tests/test_contrato.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_contrato.py -k "expoe_grupos_especie or grupos_ausentes_viram_none or codigos_de_grupo_sao_texto"'
}

# eval_2: Bloco inválido recusado no carregamento
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grupo_codigo_repetido_recusado grupos_cobertura_diferente_recusada grupos_sem_aprovacao_recusado; do python3 -m pytest --collect-only -q tests/test_contrato.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_contrato.py -k "grupo_codigo_repetido_recusado or grupos_cobertura_diferente_recusada or grupos_sem_aprovacao_recusado"'
}

# eval_3: O comportamento selado segue intacto
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in expoe_mapa_de_colapsos expoe_particionamento nao_relaxa_recusa_de_float; do python3 -m pytest --collect-only -q tests/test_contrato.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_contrato.py -k "expoe_mapa_de_colapsos or expoe_particionamento or nao_relaxa_recusa_de_float"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Os grupos expostos, opcionais, em texto"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Bloco inválido recusado no carregamento"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "O comportamento selado segue intacto"
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

Reverter src/pda/contrato.py e tests/test_contrato.py ao commit assentado.

## Observability Hooks

contratos carregados sem grupos_especie

## Anti-Patterns

- Do not exigir grupos_especie no carregador: contratos-fixture antigos não o têm; instead expor como opcional e deixar a Gold exigir.
- Do not converter códigos para inteiro: '01' vira 1 e não casa com o dado; instead manter e exigir texto.
- Do not editar um teste já existente de tests/test_contrato.py: teste selado que precisa mudar denuncia mudança de comportamento; instead só acrescentar testes novos.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`

## Open Questions

(none — this task is fully specified)
