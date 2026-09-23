---
id: T-20260923-vincula-procedencia
title: "Vincular a partição da landing ao CSV de origem"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: []
creates_paths: [src/produtor/vincular_procedencia.py, tests/test_vincular_procedencia.py]
source_note: "seamwise/legs/LEG-VINCULA-PROCEDENCIA.md#T-20260923-vincula-procedencia"
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
signed_off_at: 2026-09-23T19:35:13Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:e40c0f1e1a0d0f71bbbb37927dc16708713346a099bfbbf7cf4235f8bd14c804
---

# Vincular a partição da landing ao CSV de origem

> **Why:** Gravar ao lado da partição a prova de que ela veio do CSV declarado.

## Goal

Gravar ao lado da partição a prova de que ela veio do CSV declarado.

## Context

Intent DI-PDA-PROCEDENCIA; seam SEAM-VINCULA-PROCEDENCIA; swimlane LANE-VINCULA-PROCEDENCIA; capability leg LEG-VINCULA-PROCEDENCIA. Done condition: Com o CSV cujo sha256 é o do contrato e a partição cujo conteúdo é a transformação dele, _PROCEDENCIA.json é gravado e relido; em qualquer divergência nada é gravado.

## Behavior

- **B-1** — GIVEN o CSV em _raw/, o contrato com procedencia.hash_csv_sha256 e o layout posicional, e a partição competencia=<c> sob particionamento.caminho do contrato WHEN o vinculador roda para a competência THEN lista os objetos de dado — objeto de dado é todo objeto sob o prefixo da partição EXCETO os auxiliares que o contrato nomeia em objetos_auxiliares_ignorados e o próprio _PROCEDENCIA.json — isenções nomeadas uma a uma, nunca exclusão por prefixo, para um _extra.parquet contar como objeto a mais — e calcula o MANIFESTO (nome, tamanho e sha256 do conteúdo) ANTES de comparar; calcula o sha256 dos bytes do CSV em fluxo e, se diferir do contrato, devolve DIVERGE sem gravar nada; lê o CSV no motor pelas posições do layout, com o DecimalType da politica_decimal e ansi.enabled=true, nunca float; e compara com a partição o MULTICONJUNTO de (especie_codigo, especie_descricao, vl_liquido) — um exceptAll e a igualdade das contagens, que juntos provam a igualdade. Antes de gravar, RECALCULA o manifesto: se mudou desde a comparação, é DIVERGE e nada é gravado. Conferindo, grava _PROCEDENCIA.json no prefixo da partição com competência, nome e sha256 do CSV, o MANIFESTO de todo objeto de dado da partição — nome, tamanho e sha256 do conteúdo —, os cinco controles como texto e o id da execução; relê o arquivo gravado e confere. Nunca toca nos objetos de dado. Zero linhas lidas de qualquer lado é NAO_MEDIDO.
- **B-2** — GIVEN uma partição que já tem _PROCEDENCIA.json WHEN o vinculador roda de novo THEN prova idêntica é a de mesma competência, hash do CSV, manifesto e controles — id da execução e instante NÃO entram na comparação —; se a prova nova é idêntica à gravada, devolve INTEGRO sem regravar; se diverge — objeto acrescentado, removido ou alterado —, devolve DIVERGE nomeando a diferença e NUNCA sobrescreve em silêncio a prova anterior.

## Success Criteria

```bash
# eval_1: Hash e conteúdo provados antes de gravar
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in hash_divergente_nao_grava conteudo_divergente_nao_grava grava_manifesto_hash_e_controles rele_o_que_gravou manifesto_mudou_antes_de_gravar_diverge; do python3 -m pytest --collect-only -q tests/test_vincular_procedencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_vincular_procedencia.py -k "hash_divergente_nao_grava or conteudo_divergente_nao_grava or grava_manifesto_hash_e_controles or rele_o_que_gravou or manifesto_mudou_antes_de_gravar_diverge"'
}

# eval_2: Nunca float, nunca vazio
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in valor_em_decimal_nunca_float zero_linhas_e_nao_medido; do python3 -m pytest --collect-only -q tests/test_vincular_procedencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_vincular_procedencia.py -k "valor_em_decimal_nunca_float or zero_linhas_e_nao_medido"'
}

# eval_3: Rodar de novo não apaga a prova
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in prova_identica_nao_regrava prova_divergente_nao_sobrescreve reexecucao_com_outro_id_e_identica; do python3 -m pytest --collect-only -q tests/test_vincular_procedencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_vincular_procedencia.py -k "prova_identica_nao_regrava or prova_divergente_nao_sobrescreve or reexecucao_com_outro_id_e_identica"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Hash e conteúdo provados antes de gravar"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Nunca float, nunca vazio"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Rodar de novo não apaga a prova"
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

Remover o _PROCEDENCIA.json; os objetos de dado nunca foram tocados.

## Observability Hooks

competências sem _PROCEDENCIA.json

## Anti-Patterns

- Do not regravar a partição ou chamar o produtor: o produtor grava com append e a competência duplicaria; instead provar sobre os objetos que já estão lá.
- Do not calcular o hash e gravar sem comparar o conteúdo: hash certo sem vínculo com a partição não prova nada; instead comparar o multiconjunto antes de gravar.
- Do not importar _ler_fonte de gravar_lago.py: é código sem Task-Spec (Regra 11); instead ler o CSV pelo layout do contrato neste módulo.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/produtor/gravar_lago.py`

## Open Questions

(none — this task is fully specified)
