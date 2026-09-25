---
id: T-20260924-gold-referencia
title: "A referência na Gold, lida da Silver"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-especie-da-bronze]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/gold_referencia.py, tests/test_gold_referencia.py]
source_note: "seamwise/legs/LEG-GOLD-REFERENCIA.md#T-20260924-gold-referencia"
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
signed_off_at: 2026-09-25T01:42:08Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:a09351c06d471be25f550c124dc448d484e9ee08805233d9f1ce9ad984a140d6
---

# A referência na Gold, lida da Silver

> **Why:** Completar o medalhão da referência: a Gold serve a espécie e o termo conformados, lidos da Silver — é dela que o consumo (Postgres, BI, agentes) passa a ler. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Completar o medalhão da referência: a Gold serve a espécie e o termo conformados, lidos da Silver — é dela que o consumo (Postgres, BI, agentes) passa a ler. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-REFERENCIA-MEDALHAO; seam SEAM-GOLD-REFERENCIA; swimlane LANE-GOLD-REFERENCIA; capability leg LEG-GOLD-REFERENCIA. Done condition: src/medalhao/gold_referencia.py publica dim_especie e dim_termo na Gold a partir da Silver, com a linhagem; os testes de tests/test_gold_referencia.py passam.

## Behavior

- **B-1** — GIVEN a Silver especie (publicada da Bronze) e a Silver glossario, em tmp_path WHEN gold_referencia.publicar(spark, silver_especie, silver_glossario, destino, competencia, sha256_glossario) roda THEN lê as duas tabelas Silver cada uma numa versão fixada no início e publica em Delta, padrão s3a://gold/pda/referencia: dim_especie — codigo, nome_oficial, grupo, descricao_fonte, texto_fonte_confere_prefixo, competencia, uma linha por código — com replaceWhere da COMPETÊNCIA, que deixa as outras intactas; e dim_termo — termo, descricao, sha256_arquivo — só do sha256_glossario pedido, SELECIONADO na Silver antes de publicar, com replaceWhere de sha256_arquivo, que deixa as outras versões do glossário intactas; nunca append, nunca overwrite da tabela inteira; cada commit leva as versões das tabelas Silver lidas e o id_execucao; relê o próprio commit e confere o multiconjunto contra a seleção da Silver lida.
- **B-2** — GIVEN uma Silver especie vazia na competência, ou divergente da releitura WHEN gold_referencia.publicar roda THEN Silver especie vazia na competência, OU sha256_glossario ausente na Silver glossario lida, devolvem NAO_MEDIDO ANTES de qualquer gravação — uma seleção vazia nunca chega ao replaceWhere, que apagaria a partição existente; reconferência divergente devolve DIVERGE. As duas dimensões são publicações INDEPENDENTES, cada uma com o seu estado no resultado; o consumo só as lê juntas se as duas estiverem INTEGRO. O módulo lê só a Silver — um teste confere pelo AST que ele não referencia bronze, landing nem _raw. Nenhum cenário usa skip, xfail ou importorskip; os testes GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde o cenário pede, e MinIO indisponível FALHA o teste; a sessão Spark do teste é uma fixture de módulo ou sessão, e nenhuma função a para.

## Success Criteria

```bash
# eval_1: A Gold serve o que a Silver conformou
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in dim_especie_da_silver dim_termo_da_silver linhagem_das_tabelas_silver; do python3 -m pytest --collect-only -q tests/test_gold_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_referencia.py -k "dim_especie_da_silver or dim_termo_da_silver or linhagem_das_tabelas_silver"'
}

# eval_2: Reconferência e outra competência
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reconfere_o_proprio_commit outra_competencia_intacta outra_versao_do_glossario_intacta; do python3 -m pytest --collect-only -q tests/test_gold_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_referencia.py -k "reconfere_o_proprio_commit or outra_competencia_intacta or outra_versao_do_glossario_intacta"'
}

# eval_3: Recusas e só a Silver
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in silver_vazia_nao_medido glossario_ausente_nao_apaga_particao dimensoes_independentes modulo_le_so_a_silver; do python3 -m pytest --collect-only -q tests/test_gold_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_referencia.py -k "silver_vazia_nao_medido or glossario_ausente_nao_apaga_particao or dimensoes_independentes or modulo_le_so_a_silver"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A Gold serve o que a Silver conformou"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Reconferência e outra competência"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Recusas e só a Silver"
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

Gold de referência divergente da Silver

## Anti-Patterns

- Do not ler a Bronze, o landing, o YAML ou _raw na Gold: a Gold lê a Silver; instead as duas tabelas Silver.
- Do not recalcular o nome ou o grupo na Gold: a Silver conforma, a Gold serve; instead servir o que a Silver conformou.
- Do not sobrescrever outra competência: competências são disjuntas (ADR 0011); instead replaceWhere da competência.

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
- `src/medalhao/especie.py`
- `tests/test_especie.py`

## Open Questions

(none — this task is fully specified)
