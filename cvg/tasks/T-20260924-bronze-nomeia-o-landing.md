---
id: T-20260924-bronze-nomeia-o-landing
title: "A Bronze registra qual partição do landing leu"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [src/medalhao/bronze.py, tests/test_bronze.py]
creates_paths: []
source_note: "seamwise/legs/LEG-BRONZE-NOMEIA-O-LANDING.md#T-20260924-bronze-nomeia-o-landing"
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
signed_off_at: 2026-09-25T01:41:34Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-25T01:59:31Z
signed_off_sig: hmac-sha256-v3:85d3c104:8bbe8f4591093c9e3fc91bd57213746e7caa82d6415bee9be1fd4962deea021f
accepted_tier: 1
accepted_attempt_id: 7e292395-8b57-4f20-b940-ca3bdc7116c4
accepted_authorization_ref: hmac-sha256-v3:85d3c104:8bbe8f4591093c9e3fc91bd57213746e7caa82d6415bee9be1fd4962deea021f
acceptance_record_digest: sha256:d866edc6bbf09d5420f5477fd94b059e496b3bb8ba5ddd3dbe264b2c421b0a23
---

# A Bronze registra qual partição do landing leu

> **Why:** Fechar a linhagem de ponta a ponta: hoje a Silver, a Gold e a especie registram a versão da camada anterior, e a Bronze registra só o hash do CSV, não o que leu do landing. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Fechar a linhagem de ponta a ponta: hoje a Silver, a Gold e a especie registram a versão da camada anterior, e a Bronze registra só o hash do CSV, não o que leu do landing. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-REFERENCIA-MEDALHAO; seam SEAM-BRONZE-NOMEIA-O-LANDING; swimlane LANE-BRONZE-NOMEIA-O-LANDING; capability leg LEG-BRONZE-NOMEIA-O-LANDING. Done condition: O commit da Bronze traz a partição do landing lida, o manifesto dos objetos e o sha256 da prova; os testes existentes de tests/test_bronze.py passam sem edição; os novos passam.

## Behavior

- **B-1** — GIVEN uma partição do landing com objetos Parquet e _PROCEDENCIA.json, em tmp_path WHEN a Bronze lê, confere e publica a competência THEN os metadados do commit ganham a chave 'landing' com: 'particao' (o caminho EXATO da partição lida), 'objetos' (nome, tamanho e sha256 dos bytes de cada objeto de dado lido, em ordem de nome — o sha256 porque nome e tamanho não provam que o objeto não foi trocado), 'sha256_manifesto' (sha256 do JSON canônico — chaves ordenadas, sem espaços — da lista 'objetos') e 'sha256_prova' (sha256 dos BYTES da _PROCEDENCIA.json da partição). A listagem e os bytes da prova são capturados ANTES da leitura dos dados e reconferidos antes do commit — se a partição mudou no meio, a Bronze devolve DIVERGE sem publicar. A Bronze LÊ os bytes da prova para o hash nos DOIS caminhos — com procedencia= passada pelo chamador (o de produção: ingestao e gold passam) e sem ela —; sem _PROCEDENCIA.json na partição, 'sha256_prova' é null e 'prova_ausente' é true, nunca um valor inventado. Pode acrescentar campo com default em BronzeConferido e guardar os bytes em _ler_prova, tudo em bronze.py. Nenhuma chave que já existia muda de nome ou de valor, e os DADOS publicados são os mesmos, linha a linha.
- **B-2** — GIVEN o tests/test_bronze.py selado WHEN a tarefa acrescenta os testes THEN todos os test_* existentes ficam como estão e passam; entram só test_commit_nomeia_a_particao_do_landing, test_manifesto_do_commit_confere_com_os_objetos, test_prova_do_commit_e_a_lida — este lê os bytes da _PROCEDENCIA.json e compara o sha256 — e test_prova_lida_tambem_com_procedencia_passada e test_particao_mudou_no_meio_diverge; os testes novos usam a fixture spark que o arquivo já tem. Nenhum cenário usa skip, xfail ou importorskip; os testes GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde o cenário pede, e MinIO indisponível FALHA o teste; a sessão Spark do teste é uma fixture de módulo ou sessão, e nenhuma função a para.

## Success Criteria

```bash
# eval_1: A partição e o manifesto no commit
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in commit_nomeia_a_particao_do_landing manifesto_do_commit_confere_com_os_objetos prova_do_commit_e_a_lida prova_lida_tambem_com_procedencia_passada particao_mudou_no_meio_diverge; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "commit_nomeia_a_particao_do_landing or manifesto_do_commit_confere_com_os_objetos or prova_do_commit_e_a_lida or prova_lida_tambem_com_procedencia_passada or particao_mudou_no_meio_diverge"'
}

# eval_2: O commit dono da competência segue igual
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in metadados_do_commit_dono_da_competencia commit_carrega_a_forma replacewhere_nao_toca_outra_competencia; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "metadados_do_commit_dono_da_competencia or commit_carrega_a_forma or replacewhere_nao_toca_outra_competencia"'
}

# eval_3: A procedência e o resto da Bronze iguais
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in manifesto_confere_objetos_listados procedencia_confere_tira_a_marca classificacao_das_seis; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "manifesto_confere_objetos_listados or procedencia_confere_tira_a_marca or classificacao_das_seis"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A partição e o manifesto no commit"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "O commit dono da competência segue igual"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A procedência e o resto da Bronze iguais"
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

Reverter src/medalhao/bronze.py e tests/test_bronze.py.

## Observability Hooks

commits da Bronze sem a partição lida

## Anti-Patterns

- Do not trocar ou renomear uma chave existente dos metadados: Silver, Gold e ingestão leem esses metadados; instead só acrescentar a chave 'landing'.
- Do not registrar o caminho da raiz do landing em vez da partição: não diz o que foi lido; instead a partição exata.
- Do not editar um teste existente: a tarefa só acrescenta; instead testes novos.

## Do-Not-Touch

- `_raw`
- `contracts`
- `cvg/docs/adrs`
- `src/pda`
- `src/ontologia`
- `infra`
- `src/medalhao/ontologia.py`
- `src/medalhao/projecao_postgres.py`
- `src/medalhao/especie.py`
- `tests/test_especie.py`

## Open Questions

(none — this task is fully specified)
