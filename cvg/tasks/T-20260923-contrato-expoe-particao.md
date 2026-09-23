---
id: T-20260923-contrato-expoe-particao
title: "Expor particionamento e limites de expoente no Contrato carregado"
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
source_note: "seamwise/legs/LEG-CONTRATO-EXPOE-PARTICAO.md#T-20260923-contrato-expoe-particao"
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
signed_off_at: 2026-09-23T16:28:24Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:1a405f69d36ffb14135f7d60af287f840edaeb3794ffdfe7a17632096ee8efda
---

# Expor particionamento e limites de expoente no Contrato carregado

> **Why:** Fazer o objeto carregado dizer o que o YAML já declara, sem quebrar a primeira descida.

## Goal

Fazer o objeto carregado dizer o que o YAML já declara, sem quebrar a primeira descida.

## Context

Intent DI-PDA-MEDALHAO; seam SEAM-CONTRATO-EXT; swimlane LANE-CONTRATO-EXT; capability leg LEG-CONTRATO-EXPOE-PARTICAO. Done condition: O contrato real expõe particionamento e politica_decimal.emax/emin; um contrato sem esses blocos carrega com os campos None; e TODA a suíte já existente de tests/test_contrato.py passa sem que um teste dela seja editado.

## Behavior

- **B-1** — GIVEN o contrato real da competência 2026-01, que declara particionamento — chave, caminho, formato, valores medidos, objetos auxiliares ignorados — e politica_decimal com emax 999999 e emin -999999, com aprovador e data WHEN o contrato é carregado THEN o objeto Contrato expõe um campo particionamento com os cinco atributos, a politica_decimal expõe emax e emin, e o Contrato expõe o MAPA DE COLAPSOS APROVADO — os grupos, cada um com a descrição original e a lista dos códigos que ela cobre, e o aprovador e a data da aprovação —, porque a decisão DEC-MAPA-APROVADO-OBRIGATORIO torna o mapa condição de publicação e, sem este campo, ele não teria caminho do YAML até Silver nem depois de aprovado, lidos do MESMO carregamento — uma única leitura do YAML, nunca uma segunda porta para o mesmo oráculo. Os campos novos são OPCIONAIS no carregador: um contrato sem esses blocos carrega com eles None, e None não é zero nem vazio — é ausência declarada, que Bronze, e não o carregador, trata como NAO_MEDIDO. Exigi-los aqui recusaria os contratos-fixture da primeira descida, que não os têm, e quebraria a suíte selada: o requisito é do consumidor, e é ele que o impõe. Já um bloco PRESENTE E INVÁLIDO é RECUSADO no carregamento, como o carregador selado já faz com política contraditória — emax que não é inteiro, emin maior que emax, e — porque ordem entre inteiros é proxy e não garante contexto utilizável — o carregador CONSTRÓI o Context declarado inteiro (precisão, arredondamento, traps=[], emax, emin) e RECUSA quando o construtor recusa ou quando o total e o máximo da âncora não o atravessam intactos, sem Overflow: MEDIDO, emin=-10 com emax=9 leva a âncora, de expoente ajustado 10, a Infinity em silêncio. Conferir o total e o máximo basta pela ADR 0009 — soma monotônica sem negativos, nenhum intermediário excede o total; particionamento sem chave, mapa com grupo de um código só ou código repetido entre grupos, aprovação sem aprovador ou sem data. Entregar o bloco e deixar a camada tropeçar ao construir o Context trocaria uma recusa com motivo por uma exceção longe da causa
- **B-2** — GIVEN a suíte já existente de tests/test_contrato.py, selada na primeira descida WHEN o carregador estendido é testado THEN toda a suíte existente passa SEM que um teste dela seja editado, e o comportamento selado fica intacto — recusa de float nos controles, precisão derivada por suficiência, política contraditória recusada no carregamento, NAO_MEDIDO sem âncora. Estender não é afrouxar: a tarefa só ACRESCENTA atributos, e um teste selado que precisasse mudar denunciaria que o carregador mudou de comportamento, que é o que a Regra 11 existe para impedir sem autorização

## Success Criteria

```bash
# eval_1: Os dois blocos expostos, opcionais, e None não é zero
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in expoe_particionamento expoe_limites_de_expoente campos_novos_sao_opcionais ausencia_vira_none_nao_zero expoe_mapa_de_colapsos limites_que_estouram_a_ancora_recusados; do python3 -m pytest --collect-only -q tests/test_contrato.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_contrato.py -k "expoe_particionamento or expoe_limites_de_expoente or campos_novos_sao_opcionais or ausencia_vira_none_nao_zero or expoe_mapa_de_colapsos or limites_que_estouram_a_ancora_recusados"'
}

# eval_2: A suíte selada passa inteira, e o contrato real expõe os dois
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in suite_selada_continua_passando fixture_sem_campos_novos contrato_real_expoe_os_dois; do python3 -m pytest --collect-only -q tests/test_contrato.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_contrato.py && python3 -m pytest -q tests/test_contrato.py -k "suite_selada_continua_passando or fixture_sem_campos_novos or contrato_real_expoe_os_dois"'
}

# eval_3: Nada do comportamento selado afrouxou
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in nao_relaxa_recusa_de_float nao_muda_precisao_derivada nao_le_o_yaml_duas_vezes bloco_presente_e_invalido_recusado; do python3 -m pytest --collect-only -q tests/test_contrato.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_contrato.py -k "nao_relaxa_recusa_de_float or nao_muda_precisao_derivada or nao_le_o_yaml_duas_vezes or bloco_presente_e_invalido_recusado"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Os dois blocos expostos, opcionais, e None não é zero"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "A suíte selada passa inteira, e o contrato real expõe os dois"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Nada do comportamento selado afrouxou"
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

Reverter src/pda/contrato.py e tests/test_contrato.py ao commit selado.

## Observability Hooks

contratos carregados sem os blocos novos

## Anti-Patterns

- Do not exigir no carregador os campos novos como obrigatórios: os contratos-fixture da primeira descida não os têm, e a suíte selada quebraria; instead expô-los como opcionais e deixar o consumidor exigi-los.
- Do not editar um teste já existente de tests/test_contrato.py para ele passar: teste selado que precisa mudar denuncia mudança de comportamento no carregador; instead só acrescentar testes novos; se um antigo falhar, o carregador é que está errado.
- Do not ler o YAML uma segunda vez para achar os blocos novos: duas leituras do mesmo oráculo podem divergir, e o contrato passa a ter duas verdades; instead extrair os blocos no mesmo carregamento que já existe.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`

## Open Questions

(none — this task is fully specified)
