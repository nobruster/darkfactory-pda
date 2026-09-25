---
id: T-20260924-silver-glossario
title: "O glossário conformado na Silver, a partir da Bronze"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-bronze-referencia]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/glossario.py, tests/test_glossario.py]
source_note: "seamwise/legs/LEG-SILVER-GLOSSARIO.md#T-20260924-silver-glossario"
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
signed_off_at: 2026-09-25T01:41:37Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:f00921af3d79b0cf96c38a425bd4c09298e36fec35320ba73a1b1684b57a4940
---

# O glossário conformado na Silver, a partir da Bronze

> **Why:** Conformar o glossário do INSS na Silver, lendo da Bronze de referência. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Conformar o glossário do INSS na Silver, lendo da Bronze de referência. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-REFERENCIA-MEDALHAO; seam SEAM-SILVER-GLOSSARIO; swimlane LANE-SILVER-GLOSSARIO; capability leg LEG-SILVER-GLOSSARIO. Done condition: src/medalhao/glossario.py publica silver/pda/glossario a partir da Bronze, com a linhagem; os testes de tests/test_glossario.py passam.

## Behavior

- **B-1** — GIVEN a Bronze do glossário publicada por bronze_referencia em tmp_path WHEN glossario.publicar(spark, bronze, destino, sha256, sha256_aprovado) roda THEN se sha256 difere de sha256_aprovado (o da fonte aprovada na ontologia), recusa SEM ler nem gravar, com o motivo GLOSSARIO_NAO_APROVADO — a mesma proteção da especie (ADR 0015); lê a Bronze numa versão fixada no início e SELECIONA sha256_arquivo igual ao pedido ANTES de conformar — sha256 pedido ausente na versão lida devolve NAO_MEDIDO —; conforma NESTA ORDEM: primeiro apara as pontas de termo e descrição, depois descarta como vazia só a linha com as DUAS células vazias, depois recusa termo vazio com descrição preenchida e termo repetido (já aparado); descarta a linha de cabeçalho (coluna_a 'Nome') e as vazias, CONTANDO os descartes, tira espaços das pontas de termo e descrição, e grava em Delta, padrão s3a://silver/pda/glossario, uma linha por termo — termo, descricao, sha256_arquivo —, por replaceWhere de sha256_arquivo; o commit leva a versão da Bronze lida, o sha256 e os descartes; relê o próprio commit e confere. Sobre a referência real, são 13 termos.
- **B-2** — GIVEN uma Bronze com termo repetido, termo vazio com descrição, ou nenhum termo WHEN glossario.publicar roda THEN recusa SEM gravar termo repetido e termo vazio; nenhum termo devolve NAO_MEDIDO. Nenhum cenário usa skip, xfail ou importorskip; os testes GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde o cenário pede, e MinIO indisponível FALHA o teste; a sessão Spark do teste é uma fixture de módulo ou sessão, e nenhuma função a para.

## Success Criteria

```bash
# eval_1: Conformado com linhagem
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in conforma_e_conta_descartes linhagem_da_bronze_no_commit treze_termos_na_referencia_real; do python3 -m pytest --collect-only -q tests/test_glossario.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_glossario.py -k "conforma_e_conta_descartes or linhagem_da_bronze_no_commit or treze_termos_na_referencia_real"'
}

# eval_2: Reconferência e versão fixada
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reconfere_o_proprio_commit le_a_bronze_na_versao_fixada; do python3 -m pytest --collect-only -q tests/test_glossario.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_glossario.py -k "reconfere_o_proprio_commit or le_a_bronze_na_versao_fixada"'
}

# eval_3: Recusas
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in termo_repetido_recusa termo_repetido_so_depois_de_aparar_recusa termo_vazio_recusa sem_termos_nao_medido glossario_nao_aprovado_recusa; do python3 -m pytest --collect-only -q tests/test_glossario.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_glossario.py -k "termo_repetido_recusa or termo_repetido_so_depois_de_aparar_recusa or termo_vazio_recusa or sem_termos_nao_medido or glossario_nao_aprovado_recusa"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Conformado com linhagem"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Reconferência e versão fixada"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Recusas"
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

glossário recusado

## Anti-Patterns

- Do not ler o glossário de _raw ou do YAML: a Silver lê a Bronze; instead a Bronze.
- Do not descartar linha sem contar: Regra 9; instead contar e registrar no commit.
- Do not reescrever a descrição do INSS: é o texto da fonte; instead só aparar as pontas.

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
- `src/medalhao/bronze_referencia.py`

## Open Questions

(none — this task is fully specified)
