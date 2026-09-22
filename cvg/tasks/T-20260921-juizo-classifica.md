---
id: T-20260921-juizo-classifica
title: "Comparar os cinco controles e classificar a diferença"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260921-envelope-fronteira]
supersedes: (none)
touches_paths: []
creates_paths: [src/pda/juizo.py, tests/test_juizo.py]
source_note: "seamwise/legs/LEG-JUIZO-ACUSA.md#T-20260921-juizo-classifica"
created: "2026-09-21T00:00:00Z"
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
signed_off_at: 2026-09-22T02:47:14Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:0a85d3bd124cab5dc67704986205d329d646931ed81303ad51cb05b5b3de4f1a
---

# Comparar os cinco controles e classificar a diferença

> **Why:** Fazer o juiz acusar, não apenas aprovar.

## Goal

Fazer o juiz acusar, não apenas aprovar.

## Context

Intent DI-PDA-BENEFICIOS; seam SEAM-JUIZO; swimlane LANE-JUIZO; capability leg LEG-JUIZO-ACUSA. Done condition: Os cinco controles comparados individualmente; divergência recusa mesmo classificada; defeito sem classificação bloqueia.

## Behavior

- **B-1** — GIVEN um agregado com uma linha a menos, e outro que redistribui valores mantendo soma e contagem WHEN o juízo compara contra a âncora THEN os cinco controles são comparados individualmente e qualquer divergência recusa — soma e contagem iguais não bastam
- **B-2** — GIVEN uma diferença de cada uma das seis classificações, uma sem classificação nenhuma, uma marcada com DUAS ao mesmo tempo, e os 11 colapsos que a competência realmente tem WHEN o veredito é calculado THEN a classificação vem do CONTRATO, não do juízo — os defeitos conhecidos da fonte entram pré-classificados e aprovados junto da âncora, com os 11 colapsos como CONFIRMED_SOURCE_DEFECT, e defeito FORA dessa lista bloqueia em vez de o juízo inventar uma; inventar seria tomar decisão de negócio sem autoridade, e bloquear com os cinco controles corretos seria travar a fábrica no dado certo. Cada diferença carrega exatamente uma classificação — zero bloqueia e duas também, porque duas permitem escolher a mais branda na hora de ler; divergência em qualquer controle RECUSA mesmo classificada; fora dos controles, MODERN_DEFECT, CONTRACT_AMBIGUITY e UNRESOLVED bloqueiam e as três CONFIRMED/APPROVED apenas registram

## Success Criteria

```bash
# eval_1: Linha a menos recusa; extremos alterados com soma igual também
eval_1() {
  pytest -q tests/test_juizo.py -k "linha_a_menos or cinco_controles"
}

# eval_2: Precedência — controle divergente recusa mesmo classificado
eval_2() {
  pytest -q tests/test_juizo.py -k precedencia
}

# eval_3: Sem classificação bloqueia; DUAS classificações também
eval_3() {
  pytest -q tests/test_juizo.py -k "defeito_sem_classe or classificacao_unica"
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Linha a menos recusa; extremos alterados com soma igual também"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Precedência — controle divergente recusa mesmo classificado"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Sem classificação bloqueia; DUAS classificações também"
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

Remover o juízo e seus testes.

## Observability Hooks

vereditos por classificação

## Anti-Patterns

- Do not introduzir parâmetro de tolerância: um centavo inexplicado viraria um centavo aceito; instead classificar a diferença ou consertar o pipeline.
- Do not editar a âncora para o veredito passar: falsifica a prova em vez de investigar; instead investigar; âncora revista exige nova aprovação.
- Do not deixar a classificação autorizar publicação: CONFIRMED explica a diferença, não a aprova; instead divergência em controle recusa, classificada ou não.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`

## Open Questions

(none — this task is fully specified)
