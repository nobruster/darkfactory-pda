---
id: T-20260925-guarda-registra-nome-oficial
title: "A guarda dos testes selados registra a mudança autorizada na Gold"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [tests/test_testes_leves.py]
creates_paths: []
source_note: "seamwise/legs/LEG-GUARDA-NOME-OFICIAL.md#T-20260925-guarda-registra-nome-oficial"
created: "2026-09-25T00:00:00Z"
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
signed_off_at: 2026-09-25T16:52:10Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:77e5693b869145c9cb580406cebe10a272c21d20643d259a05071f919939e2e8
---

# A guarda dos testes selados registra a mudança autorizada na Gold

> **Why:** Registrar na guarda test_testes_leves.py a impressão nova de test_commit_carrega_a_forma, a única mudança autorizada pelo dono num teste selado da Gold. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Registrar na guarda test_testes_leves.py a impressão nova de test_commit_carrega_a_forma, a única mudança autorizada pelo dono num teste selado da Gold. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-GUARDA-NOME-OFICIAL; seam SEAM-GUARDA-NOME-OFICIAL; swimlane LANE-GUARDA-NOME-OFICIAL; capability leg LEG-GUARDA-NOME-OFICIAL. Done condition: Em tests/test_testes_leves.py muda EXATAMENTE o token 'commit_carrega_a_forma a48ab419462c1eba 1' para 'commit_carrega_a_forma 942ea6bcdf6c9ad3 1', mais um comentário que nomeia a exceção; os testes da guarda passam.

## Behavior

- **B-1** — GIVEN a guarda, que acusa test_gold.py::test_commit_carrega_a_forma porque a sua tupla literal ganhou 'nome_oficial' por exceção nomeada (receita D) WHEN a tarefa atualiza a guarda THEN dentro de _ANTES_GOLD, o token 'commit_carrega_a_forma a48ab419462c1eba 1' passa a 'commit_carrega_a_forma 942ea6bcdf6c9ad3 1' — a impressão medida no contêiner, com o mesmo método da guarda (16 hex do sha256 do ast.dump, Python 3.10.12) —, e uma linha de comentário acima de _ANTES_GOLD registra a exceção: 'commit_carrega_a_forma: nome_oficial na tupla — DEC-NOME-OFICIAL-NA-GOLD, 2026-09-25'. As outras 47 impressões, _ANTES_ASSUNTOS, MODULOS, as funções de apoio e os quatro test_* da guarda ficam EXATAMENTE como estão.
- **B-2** — GIVEN a guarda atualizada WHEN a guarda roda THEN test_corpo_das_funcoes_test_intacto passa, e continua acusando qualquer OUTRA mudança em test_gold.py ou test_gold_assuntos.py; test_mesmos_ids_coletados, test_nenhum_skip_ou_xfail e test_copia_isolada_do_cenario_base passam sem edição. Nenhum cenário usa skip, xfail ou importorskip.

## Success Criteria

```bash
# eval_1: A guarda aceita a mudança registrada
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in corpo_das_funcoes_test_intacto mesmos_ids_coletados; do python3 -m pytest --collect-only -q tests/test_testes_leves.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_testes_leves.py -k "corpo_das_funcoes_test_intacto or mesmos_ids_coletados"'
}

# eval_2: O resto da guarda igual
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in nenhum_skip_ou_xfail copia_isolada_do_cenario_base; do python3 -m pytest --collect-only -q tests/test_testes_leves.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_testes_leves.py -k "nenhum_skip_ou_xfail or copia_isolada_do_cenario_base"'
}

# eval_3: Tudo da guarda
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in corpo_das_funcoes_test_intacto nenhum_skip_ou_xfail; do python3 -m pytest --collect-only -q tests/test_testes_leves.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_testes_leves.py -k "corpo_das_funcoes_test_intacto or nenhum_skip_ou_xfail"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A guarda aceita a mudança registrada"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "O resto da guarda igual"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Tudo da guarda"
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

Reverter tests/test_testes_leves.py.

## Observability Hooks

mudanças em teste selado registradas na guarda

## Anti-Patterns

- Do not recalcular ou reescrever todas as impressões: apagaria a proteção sobre as outras 47; instead trocar só o token nomeado.
- Do not afrouxar a comparação da guarda: Regra 3: nunca ajustar o verificador para passar; instead registrar a mudança autorizada, e só ela.
- Do not tirar test_gold.py de MODULOS: a guarda deixaria de proteger a Gold; instead manter MODULOS.

## Do-Not-Touch

- `_raw`
- `contracts`
- `cvg/docs/adrs`
- `src`
- `infra`
- `tests/test_gold.py`
- `tests/test_gold_assuntos.py`

## Open Questions

(none — this task is fully specified)
