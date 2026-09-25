---
id: T-20260924-especie-da-bronze
title: "A especie tira os nomes da Bronze do dicionário"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-silver-glossario]
supersedes: (none)
touches_paths: [src/medalhao/especie.py, tests/test_especie.py]
creates_paths: []
source_note: "seamwise/legs/LEG-ESPECIE-DA-BRONZE.md#T-20260924-especie-da-bronze"
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
signed_off_at: 2026-09-25T01:42:07Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-25T02:37:31Z
signed_off_sig: hmac-sha256-v3:85d3c104:4e07c863718cb6eec0d1004f256ea8e5dd4f2d22711037921ceda3deb5297b14
accepted_tier: 1
accepted_attempt_id: 6e694d80-e539-452c-b2ee-90aeb5591761
accepted_authorization_ref: hmac-sha256-v3:85d3c104:4e07c863718cb6eec0d1004f256ea8e5dd4f2d22711037921ceda3deb5297b14
acceptance_record_digest: sha256:9fa489811b54a8f89364da21f517760f57c4afb30e75795741bb008f64af5dfa
---

# A especie tira os nomes da Bronze do dicionário

> **Why:** Fazer a especie da Silver ler os nomes oficiais da Bronze do dicionário — não do YAML —, com a linhagem das duas camadas anteriores. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Fazer a especie da Silver ler os nomes oficiais da Bronze do dicionário — não do YAML —, com a linhagem das duas camadas anteriores. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-REFERENCIA-MEDALHAO; seam SEAM-ESPECIE-DA-BRONZE; swimlane LANE-ESPECIE-DA-BRONZE; capability leg LEG-ESPECIE-DA-BRONZE. Done condition: src/medalhao/especie.py tem publicar_especie_da_bronze; a publicar_especie existente e seus testes ficam intactos; os testes novos de tests/test_especie.py passam, incluindo o de ponta a ponta com a referência real.

## Behavior

- **B-1** — GIVEN a Bronze do dicionário publicada por bronze_referencia e uma Silver de benefícios WHEN especie.publicar_especie_da_bronze(spark, bronze_dicionario, sha256, sha256_aprovado, silver, destino, competencia, grupos) roda, com grupos vindos de contrato.grupos_especie e sha256_aprovado vindo da fonte aprovada na ontologia versionada THEN se sha256 difere de sha256_aprovado, recusa SEM ler nem gravar, com o motivo DICIONARIO_NAO_APROVADO — um dicionário novo do INSS só entra depois de o dono aprová-lo, como o ADR 0014 já exigia; lê a Bronze do dicionário e a Silver cada uma numa versão fixada no início, SELECIONA sha256_arquivo igual ao pedido antes de conformar (ausente devolve NAO_MEDIDO); conforma os nomes a partir da Bronze — linha com coluna_a numérica vira código de 2 dígitos e coluna_b é o nome oficial COMO VEIO; o cabeçalho e as vazias são descartados E CONTADOS; duas linhas que caem no MESMO código depois de conformadas (ex.: '1' e '01') recusam com CODIGO_COLIDIDO, nunca uma é escolhida —; grava com o MESMO schema e as mesmas regras da especie atual (descricao_fonte como veio, texto_fonte_confere_prefixo, replaceWhere da competência, reconferência do próprio commit); o commit leva a versão da Silver, a versão da Bronze do dicionário, o sha256 do arquivo e os descartes. Nenhuma função existente de especie.py muda de comportamento.
- **B-2** — GIVEN o tests/test_especie.py selado WHEN a tarefa acrescenta os testes THEN todos os test_* existentes ficam como estão e passam; entram só test_especie_da_bronze_nomes_da_bronze, test_especie_da_bronze_linhagem_das_duas_camadas, test_especie_da_bronze_conta_descartes, test_especie_da_bronze_codigo_fora_recusa, test_especie_da_bronze_dicionario_nao_aprovado_recusa, test_especie_da_bronze_codigo_colidido_recusa e test_especie_da_bronze_ponta_a_ponta_real — este grava, em tmp_path, o landing e a Bronze de referência a partir de /dados/_raw pelos módulos das tarefas anteriores e exige, sobre a Silver real de 2026-01, 65 linhas, 65 nomes distintos, 43 com o prefixo conferindo, e cada nome IGUAL ao da ontologia versionada — extraído por OUTRO parser (medalhao.ontologia), a evidência independente de que o parser da Bronze leu a planilha certo. Nenhum cenário usa skip, xfail ou importorskip; os testes GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde o cenário pede, e MinIO indisponível FALHA o teste; a sessão Spark do teste é uma fixture de módulo ou sessão, e nenhuma função a para.

## Success Criteria

```bash
# eval_1: Nomes da Bronze, com linhagem
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in especie_da_bronze_nomes_da_bronze especie_da_bronze_linhagem_das_duas_camadas especie_da_bronze_conta_descartes; do python3 -m pytest --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_especie.py -k "especie_da_bronze_nomes_da_bronze or especie_da_bronze_linhagem_das_duas_camadas or especie_da_bronze_conta_descartes"'
}

# eval_2: Ponta a ponta e recusa
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in especie_da_bronze_ponta_a_ponta_real especie_da_bronze_codigo_fora_recusa especie_da_bronze_dicionario_nao_aprovado_recusa especie_da_bronze_codigo_colidido_recusa; do python3 -m pytest --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_especie.py -k "especie_da_bronze_ponta_a_ponta_real or especie_da_bronze_codigo_fora_recusa or especie_da_bronze_dicionario_nao_aprovado_recusa or especie_da_bronze_codigo_colidido_recusa"'
}

# eval_3: A especie antiga intacta
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grava_nome_oficial_e_texto_da_fonte reconferencia_acusa_linha_alterada outra_competencia_intacta; do python3 -m pytest --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_especie.py -k "grava_nome_oficial_e_texto_da_fonte or reconferencia_acusa_linha_alterada or outra_competencia_intacta"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Nomes da Bronze, com linhagem"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Ponta a ponta e recusa"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A especie antiga intacta"
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

Reverter src/medalhao/especie.py e tests/test_especie.py.

## Observability Hooks

nomes divergentes da Bronze

## Anti-Patterns

- Do not mudar publicar_especie ou um teste existente: acrescentar, não mudar; instead função nova ao lado.
- Do not ler os nomes do YAML ou de _raw: a Silver lê a Bronze; instead a Bronze do dicionário.
- Do not aparar o nome oficial: o nome é o texto da fonte; instead como veio.

## Do-Not-Touch

- `_raw`
- `contracts`
- `cvg/docs/adrs`
- `src/pda`
- `src/ontologia`
- `infra`
- `src/medalhao/ontologia.py`
- `src/medalhao/projecao_postgres.py`
- `src/medalhao/bronze.py`
- `tests/test_bronze.py`
- `src/produtor/landing_referencia.py`
- `src/medalhao/bronze_referencia.py`
- `src/medalhao/glossario.py`

## Open Questions

(none — this task is fully specified)
