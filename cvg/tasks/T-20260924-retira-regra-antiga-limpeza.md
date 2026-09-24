---
id: T-20260924-retira-regra-antiga-limpeza
title: "Retirar o teste selado que codifica a regra antiga da limpeza"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [tests/test_limpeza.py]
creates_paths: []
source_note: "seamwise/legs/LEG-RETIRA-REGRA-ANTIGA.md#T-20260924-retira-regra-antiga-limpeza"
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
signed_off_at: 2026-09-24T20:18:14Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-24T20:48:45Z
signed_off_sig: hmac-sha256-v3:85d3c104:de10ab58482f80d91373bd1c1d37e6d264c0932b92ea581af5b69d842ac35fca
accepted_tier: 1
accepted_attempt_id: 3774a4c0-6371-4f78-8049-0bb863a51bb1
accepted_authorization_ref: hmac-sha256-v3:85d3c104:de10ab58482f80d91373bd1c1d37e6d264c0932b92ea581af5b69d842ac35fca
acceptance_record_digest: sha256:22c73a4ad97aad0ddec231649892dd203400cc41fc25ce037ef2810091826065
---

# Retirar o teste selado que codifica a regra antiga da limpeza

> **Why:** Deixar a suíte coerente com a regra aprovada: execução substituída e conferida tem o preparo apagado. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Deixar a suíte coerente com a regra aprovada: execução substituída e conferida tem o preparo apagado. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-TESTE-LIMPEZA; seam SEAM-RETIRA-REGRA-ANTIGA; swimlane LANE-RETIRA-REGRA-ANTIGA; capability leg LEG-RETIRA-REGRA-ANTIGA. Done condition: test_commit_seguido_de_outro_preserva não existe mais; os demais testes de tests/test_limpeza.py são exatamente os de antes e passam; um teste-guarda confere a lista de testes do módulo; o módulo inteiro passa.

## Behavior

- **B-1** — GIVEN o teste selado test_commit_seguido_de_outro_preserva, cujo cenário é idêntico ao de test_substituida_conferida_apaga com a expectativa oposta WHEN a regra aprovada — substituída e conferida apaga — vale THEN test_commit_seguido_de_outro_preserva é RETIRADO do módulo, sem ser reescrito, porque reescrito seria uma duplicata de test_substituida_conferida_apaga, que já cobre o mesmo cenário com a expectativa nova; nenhuma outra função test_* do módulo muda; src/medalhao/limpeza.py fica FORA do escopo de escrita — o comportamento entregue governa, e o path_policy recusa qualquer escrita nele.
- **B-2** — GIVEN o módulo depois da retirada WHEN é coletado e executado inteiro THEN um teste-guarda, test_lista_de_testes_da_limpeza, confere que o módulo tem EXATAMENTE os testes test_apaga_preparo_de_execucao_publicada, test_publicada_intacta_depois, test_id_vazio_recusado, test_caminho_fora_do_preparo_recusado, test_execucao_nao_publicada_preserva, test_commit_revertido_preserva, test_outra_execucao_intacta, test_substituida_conferida_apaga, test_publicada_intacta_apos_limpar_substituida, test_revertida_preserva, test_sem_commit_preserva, test_execucao_ativa_preserva, test_prefixo_montado_de_partes_validadas e ele mesmo — nem um a mais, nem um a menos; os casos que a regra antiga ainda governa seguem preservando: revertida, sem commit, execução ativa; todos passam.

## Success Criteria

```bash
# eval_1: A regra nova governa o cenário
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in substituida_conferida_apaga publicada_intacta_apos_limpar_substituida; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "substituida_conferida_apaga or publicada_intacta_apos_limpar_substituida"'
}

# eval_2: A lista de testes é exatamente a esperada
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in lista_de_testes_da_limpeza revertida_preserva sem_commit_preserva execucao_ativa_preserva; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "lista_de_testes_da_limpeza or revertida_preserva or sem_commit_preserva or execucao_ativa_preserva"'
}

# eval_3: O resto do módulo segue verde
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in apaga_preparo_de_execucao_publicada commit_revertido_preserva caminho_fora_do_preparo_recusado publicada_intacta_depois id_vazio_recusado execucao_nao_publicada_preserva outra_execucao_intacta prefixo_montado_de_partes_validadas; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "apaga_preparo_de_execucao_publicada or commit_revertido_preserva or caminho_fora_do_preparo_recusado or publicada_intacta_depois or id_vazio_recusado or execucao_nao_publicada_preserva or outra_execucao_intacta or prefixo_montado_de_partes_validadas"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A regra nova governa o cenário"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "A lista de testes é exatamente a esperada"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "O resto do módulo segue verde"
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

Restaurar tests/test_limpeza.py do commit assentado.

## Observability Hooks

testes selados que contradizem uma regra aprovada

## Anti-Patterns

- Do not reescrever test_commit_seguido_de_outro_preserva para esperar APAGADO: vira duplicata de um teste que já existe; instead retirar e manter a guarda da lista.
- Do not mudar src/medalhao/limpeza.py para o teste antigo voltar a passar: desfaz a regra aprovada pelo dono; instead o comportamento entregue governa.
- Do not retirar ou editar qualquer outro teste: a exceção é para exatamente um teste; instead a guarda confere a lista inteira.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/pda`

## Open Questions

(none — this task is fully specified)
