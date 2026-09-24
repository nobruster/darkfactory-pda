---
id: T-20260924-ontologia-postgres
title: "Projeção da ontologia no Postgres, carregada numa transação e reconferida"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-ontologia-versionada]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/projecao_postgres.py, tests/test_projecao_postgres.py]
source_note: "seamwise/legs/LEG-ONTOLOGIA-POSTGRES.md#T-20260924-ontologia-postgres"
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
signed_off_at: 2026-09-24T22:52:45Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-24T23:10:56Z
signed_off_sig: hmac-sha256-v3:85d3c104:bcb837632e7f3633a0e7e5f6b2f69ca706c96b56437592b745bb4700bc0d1e09
accepted_tier: 1
accepted_attempt_id: 8ecc6d1c-56b5-4981-a23d-7878f1612f6b
accepted_authorization_ref: hmac-sha256-v3:85d3c104:bcb837632e7f3633a0e7e5f6b2f69ca706c96b56437592b745bb4700bc0d1e09
acceptance_record_digest: sha256:e785d93d235f12d6533a6db7682f2f750aa5949246809d8a9b5c177d3cc9b165
---

# Projeção da ontologia no Postgres, carregada numa transação e reconferida

> **Why:** Carregar a ontologia no Postgres pda-postgres para consulta fora do Spark, sem que o banco vire fonte da verdade: tudo ou nada, reconferido linha a linha, com a versão da ontologia gravada. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Carregar a ontologia no Postgres pda-postgres para consulta fora do Spark, sem que o banco vire fonte da verdade: tudo ou nada, reconferido linha a linha, com a versão da ontologia gravada. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-ONTOLOGIA; seam SEAM-ONTOLOGIA-POSTGRES; swimlane LANE-ONTOLOGIA-POSTGRES; capability leg LEG-ONTOLOGIA-POSTGRES. Done condition: projetar_ontologia carrega fontes, termos, colunas, grupos e espécies num schema nomeado, numa transação só, reconfere cada tabela contra a ontologia e grava o sha256 da ontologia; falha no meio deixa a carga anterior intacta; os testes de tests/test_projecao_postgres.py passam.

## Behavior

- **B-1** — GIVEN a ontologia carregada e as variáveis PG_HOST, PG_PORT, PG_DB, PG_USER e PG_PASSWORD do ambiente WHEN projetar_ontologia(ontologia, schema) roda THEN num schema OBRIGATÓRIO, sem valor padrão, cujo nome é validado como identificador simples (letras minúsculas, dígitos e _), cria as tabelas fonte, termo, coluna, grupo e especie, com chave primária em cada uma e chave estrangeira de coluna para termo e de especie para grupo, e uma tabela carga com o sha256 da ontologia e o instante da carga; a carga substitui o conteúdo anterior do schema numa ÚNICA transação e, AINDA DENTRO dela, antes do commit, relê cada tabela e confere linha a linha contra a ontologia — 2 fontes, 13 termos, 14 colunas, os grupos do contrato (5 hoje), 65 espécies —; só então faz commit e devolve PROJETADA com as contagens. Aceita um parâmetro apos_tabela, chamado dentro da transação depois de cada tabela carregada, pelo qual os testes injetam falha ou alteração. Credenciais só do ambiente, nunca escritas no código, nunca impressas nem incluídas em mensagem de erro.
- **B-2** — GIVEN uma carga que falha no meio, uma variável de ambiente ausente, ou um nome de schema inválido WHEN projetar_ontologia roda THEN falha no meio desfaz a transação e a carga anterior fica intacta, conferida pelo sha256 na tabela carga; reconferência divergente — uma linha alterada por apos_tabela — desfaz a transação, devolve DIVERGENTE e a carga anterior segue sendo a visível; variável ausente recusa SEM chamar psycopg.connect (o teste o substitui por um que falha se chamado) e nomeia a variável, nunca o valor; um erro de conexão não traz a senha na mensagem; nome de schema fora do padrão, 'public' ou começado por 'pg_' recusa sem executar SQL. Cada teste usa um schema 'teste_' com sufixo aleatório, apagado no finalizer da fixture — mesmo quando o teste falha —, e nunca apaga schema que ele não criou. Nenhum cenário usa skip, xfail ou importorskip: Postgres indisponível FALHA o teste.

## Success Criteria

```bash
# eval_1: A projeção carrega e confere
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in projeta_e_reconfere grava_sha256_da_ontologia chaves_estrangeiras_valem chave_primaria_em_cada_tabela; do python3 -m pytest --collect-only -q tests/test_projecao_postgres.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_projecao_postgres.py -k "projeta_e_reconfere or grava_sha256_da_ontologia or chaves_estrangeiras_valem or chave_primaria_em_cada_tabela"'
}

# eval_2: Tudo ou nada
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in falha_no_meio_preserva_carga_anterior divergencia_desfaz_e_preserva_carga_anterior; do python3 -m pytest --collect-only -q tests/test_projecao_postgres.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_projecao_postgres.py -k "falha_no_meio_preserva_carga_anterior or divergencia_desfaz_e_preserva_carga_anterior"'
}

# eval_3: Sem credencial no código e sem SQL de nome livre
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in variavel_ausente_recusa_sem_conectar erro_de_conexao_nao_vaza_senha schema_invalido_recusa schema_public_recusa schema_de_teste_apagado; do python3 -m pytest --collect-only -q tests/test_projecao_postgres.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_projecao_postgres.py -k "variavel_ausente_recusa_sem_conectar or erro_de_conexao_nao_vaza_senha or schema_invalido_recusa or schema_public_recusa or schema_de_teste_apagado"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A projeção carrega e confere"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Tudo ou nada"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Sem credencial no código e sem SQL de nome livre"
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

Remover os dois arquivos criados e apagar o schema carregado.

## Observability Hooks

projeções divergentes da ontologia versionada

## Anti-Patterns

- Do not escrever credencial, host ou senha padrão no código ou no teste: é o defeito do legado que o BRD nomeou (Regra 6); instead ler PG_* do ambiente e recusar se faltar.
- Do not montar SQL com o nome do schema sem validar: nome livre em SQL é injeção; instead validar o identificador e usar psycopg.sql.Identifier.
- Do not inserir tabela por tabela em transações separadas: uma falha no meio deixa o banco com meia ontologia; instead uma transação para a carga inteira.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/pda`
- `infra`
- `src/ontologia/beneficios-emitidos.yaml`
- `src/medalhao/ontologia.py`

## Open Questions

(none — this task is fully specified)
