---
id: T-20260924-bronze-referencia
title: "A Bronze do dicionário e do glossário, lida do landing"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-landing-referencia]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/bronze_referencia.py, tests/test_bronze_referencia.py]
source_note: "seamwise/legs/LEG-BRONZE-REFERENCIA.md#T-20260924-bronze-referencia"
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
signed_off_at: 2026-09-25T01:41:36Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-25T02:13:46Z
signed_off_sig: hmac-sha256-v3:85d3c104:494ce4f04857cfa7740ee2954ebb38ec5a365fdbd1c21bca304dafce6d2db56d
accepted_tier: 1
accepted_attempt_id: 2ec8474f-20de-4803-8274-9d8fc533102b
accepted_authorization_ref: hmac-sha256-v3:85d3c104:494ce4f04857cfa7740ee2954ebb38ec5a365fdbd1c21bca304dafce6d2db56d
acceptance_record_digest: sha256:6efd8c9d323eb1197919447e215594aad0034c5ce5c32084049abd42ea0ce730
---

# A Bronze do dicionário e do glossário, lida do landing

> **Why:** Pôr em Delta as linhas dos dois arquivos de referência como vieram, lidas do landing. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Pôr em Delta as linhas dos dois arquivos de referência como vieram, lidas do landing. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-REFERENCIA-MEDALHAO; seam SEAM-BRONZE-REFERENCIA; swimlane LANE-BRONZE-REFERENCIA; capability leg LEG-BRONZE-REFERENCIA. Done condition: src/medalhao/bronze_referencia.py lê do landing — nunca de _raw —, confere a prova e publica as duas tabelas Bronze com as linhas como vieram e a linhagem no commit; os testes de tests/test_bronze_referencia.py passam.

## Behavior

- **B-1** — GIVEN o landing de referência gravado por landing_referencia em tmp_path WHEN bronze_referencia.publicar(spark, landing, destino, arquivo, sha256) roda THEN lê os bytes da partição sha256=<sha256> DO LANDING, confere que o sha256 dos bytes lidos é o da _PROCEDENCIA.json e o do nome da partição, e lê a planilha com um parser PRÓPRIO deste módulo, só com a biblioteca padrão (zipfile sobre io.BytesIO e xml) — NÃO medalhao.ontologia.ler_xlsx, que descarta linhas sem valor e não devolve o número da linha (medido: o dicionário tem 69 elementos <row>, 2 sem valor; o glossário 24, 10 sem valor). O arquivo tem de ter EXATAMENTE uma planilha, senão recusa. Grava em Delta, por replaceWhere de sha256_arquivo, um registro por elemento <row> COMO VEIO: linha = o número do atributo r do <row> (nunca uma contagem), coluna_a e coluna_b em texto sem trim (célula ausente é nula), arquivo e sha256_arquivo — o cabeçalho e os <row> sem valor entram também, porque a Bronze não filtra; uma linha que o XML não traz não é inventada; o dicionário vai para <destino>/dicionario_especies e o glossário para <destino>/glossario, padrão s3a://bronze/pda/referencia; o commit leva em userMetadata a partição do landing lida, o sha256 da prova, o id_execucao e o número de linhas; depois relê a versão do PRÓPRIO commit e confere o multiconjunto nos dois sentidos.
- **B-2** — GIVEN uma prova divergente, uma planilha sem linhas, ou um pedido que leria _raw WHEN bronze_referencia.publicar roda THEN sha256 dos bytes diferente da prova ou do nome da partição recusa SEM gravar; planilha sem nenhuma linha devolve NAO_MEDIDO; o módulo não tem caminho para /dados/_raw — um teste confere pelo AST do módulo que ele não referencia _raw. Nenhum cenário usa skip, xfail ou importorskip; os testes GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde o cenário pede, e MinIO indisponível FALHA o teste; a sessão Spark do teste é uma fixture de módulo ou sessão, e nenhuma função a para.

## Success Criteria

```bash
# eval_1: Linhas como vieram, lidas do landing
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in linhas_como_vieram cabecalho_e_vazias_entram numero_da_linha_e_o_do_xml linhagem_do_landing_no_commit; do python3 -m pytest --collect-only -q tests/test_bronze_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze_referencia.py -k "linhas_como_vieram or cabecalho_e_vazias_entram or numero_da_linha_e_o_do_xml or linhagem_do_landing_no_commit"'
}

# eval_2: Reconferência e idempotência
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reconfere_o_proprio_commit republicar_mesmo_sha_substitui_so_a_particao; do python3 -m pytest --collect-only -q tests/test_bronze_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze_referencia.py -k "reconfere_o_proprio_commit or republicar_mesmo_sha_substitui_so_a_particao"'
}

# eval_3: Recusas e nada de _raw
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in prova_divergente_nao_grava planilha_vazia_nao_medido mais_de_uma_planilha_recusa modulo_nao_le_raw; do python3 -m pytest --collect-only -q tests/test_bronze_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze_referencia.py -k "prova_divergente_nao_grava or planilha_vazia_nao_medido or mais_de_uma_planilha_recusa or modulo_nao_le_raw"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Linhas como vieram, lidas do landing"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Reconferência e idempotência"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Recusas e nada de _raw"
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

Remover os dois arquivos criados.

## Observability Hooks

referências recusadas pela prova

## Anti-Patterns

- Do not ler o .xlsx de _raw: a Bronze lê o landing; instead os bytes da partição.
- Do not filtrar o cabeçalho ou as linhas vazias na Bronze: a Bronze guarda como veio; instead a Silver conforma.
- Do not aparar ou converter texto: a Bronze guarda como veio; instead a Silver conforma.

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
- `src/medalhao/especie.py`
- `tests/test_especie.py`
- `src/produtor/landing_referencia.py`

## Open Questions

(none — this task is fully specified)
