---
id: T-20260923-bronze-le-procedencia
title: "Bronze confere _PROCEDENCIA.json da partição"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260923-vincula-procedencia]
supersedes: (none)
touches_paths: [src/medalhao/bronze.py, tests/test_bronze.py]
creates_paths: []
source_note: "seamwise/legs/LEG-BRONZE-LE-PROCEDENCIA.md#T-20260923-bronze-le-procedencia"
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
signed_off_at: 2026-09-23T19:34:51Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:00d2647046c583d7596be872cd2396e1fabac065f6fde396a6675780e180e346
---

# Bronze confere _PROCEDENCIA.json da partição

> **Why:** Tirar a marca PROCEDENCIA_NAO_VINCULADA só com prova.

## Goal

Tirar a marca PROCEDENCIA_NAO_VINCULADA só com prova.

## Context

Intent DI-PDA-PROCEDENCIA; seam SEAM-BRONZE-LE-PROCEDENCIA; swimlane LANE-BRONZE-LE-PROCEDENCIA; capability leg LEG-BRONZE-LE-PROCEDENCIA. Done condition: Com _PROCEDENCIA.json válido a Bronze sai sem a marca e com o hash; sem ele, a marca continua; com manifesto divergente, DIVERGE; e toda a suíte já existente de tests/test_bronze.py continua passando.

## Behavior

- **B-1** — GIVEN a partição com _PROCEDENCIA.json gravado pelo vinculador WHEN a Bronze lê a competência THEN lê o arquivo do prefixo da partição, confere o sha256 do CSV contra o contrato, a COMPETÊNCIA do arquivo contra a solicitada e a do contrato, o MANIFESTO contra os objetos de dado que ela mesma lista — nome, tamanho e sha256 do conteúdo, com a mesma definição de objeto de dado do vinculador: objeto de dado é todo objeto sob o prefixo da partição EXCETO os auxiliares que o contrato nomeia em objetos_auxiliares_ignorados e o próprio _PROCEDENCIA.json — isenções nomeadas uma a uma, nunca exclusão por prefixo, para um _extra.parquet contar como objeto a mais — e os controles do arquivo contra os que ela mede; conferindo tudo, sai sem a marca PROCEDENCIA_NAO_VINCULADA e com hash_procedencia preenchido, e o estado INTEGRO segue as regras que já existem.
- **B-2** — GIVEN uma partição sem _PROCEDENCIA.json, com um JSON inválido, ou com manifesto que não bate com os objetos WHEN a Bronze lê a competência THEN sem o arquivo, a marca continua como hoje; JSON inválido é ERRO_LEITURA; manifesto, hash ou controles divergentes são DIVERGE com a diferença nomeada, e nada é gravado — objeto a mais, a menos ou alterado depois da vinculação é exatamente o que a procedência existe para acusar. Nenhum teste já existente de tests/test_bronze.py é editado.

## Success Criteria

```bash
# eval_1: A marca sai só com prova conferida
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in procedencia_confere_tira_a_marca manifesto_confere_objetos_listados controles_da_procedencia_conferidos competencia_da_prova_conferida; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "procedencia_confere_tira_a_marca or manifesto_confere_objetos_listados or controles_da_procedencia_conferidos or competencia_da_prova_conferida"'
}

# eval_2: Ausente, inválida ou divergente
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sem_procedencia_mantem_a_marca procedencia_json_invalido_e_erro objeto_a_mais_diverge hash_da_procedencia_diverge objeto_com_underscore_a_mais_diverge; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "sem_procedencia_mantem_a_marca or procedencia_json_invalido_e_erro or objeto_a_mais_diverge or hash_da_procedencia_diverge or objeto_com_underscore_a_mais_diverge"'
}

# eval_3: A suíte já existente continua passando
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in cinco_controles particao_ausente centavo_a_mais; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "cinco_controles or particao_ausente or centavo_a_mais"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A marca sai só com prova conferida"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Ausente, inválida ou divergente"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A suíte já existente continua passando"
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

Reverter src/medalhao/bronze.py e tests/test_bronze.py ao commit assentado.

## Observability Hooks

leituras com a marca PROCEDENCIA_NAO_VINCULADA

## Anti-Patterns

- Do not aceitar o hash do arquivo sem conferir o manifesto: hash certo sem vínculo com os objetos lidos não prova nada; instead conferir nome, tamanho e sha256 de cada objeto listado.
- Do not ignorar objetos pelo prefixo _ em vez de nomeá-los: um _extra.parquet ficaria fora do manifesto sem acusar; instead isentar só os auxiliares do contrato e o _PROCEDENCIA.json, um a um.
- Do not editar um teste já existente de tests/test_bronze.py: teste selado que precisa mudar denuncia mudança de comportamento; instead só acrescentar testes novos.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`

## Open Questions

(none — this task is fully specified)
