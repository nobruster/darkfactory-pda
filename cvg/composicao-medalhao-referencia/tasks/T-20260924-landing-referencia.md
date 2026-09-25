---
id: T-20260924-landing-referencia
title: "O dicionário e o glossário do INSS no landing, como vieram"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-bronze-nomeia-o-landing]
supersedes: (none)
touches_paths: []
creates_paths: [src/produtor/landing_referencia.py, tests/test_landing_referencia.py]
source_note: "seamwise/legs/LEG-LANDING-REFERENCIA.md#T-20260924-landing-referencia"
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
signed_off_at: 2026-09-25T01:42:10Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-25T02:02:36Z
signed_off_sig: hmac-sha256-v3:85d3c104:f6c2c20742ad825dbf6abdb431a6d096682f0ec28163fcef22ec4e0318f47da4
accepted_tier: 1
accepted_attempt_id: 1c735cd1-1c4a-47d7-8f4e-36ec0dd0bcb3
accepted_authorization_ref: hmac-sha256-v3:85d3c104:f6c2c20742ad825dbf6abdb431a6d096682f0ec28163fcef22ec4e0318f47da4
acceptance_record_digest: sha256:308eeef8f4423d7f66c2b4dd9c23a21b39715cf37009aaed04cfabf1c39a76e9
---

# O dicionário e o glossário do INSS no landing, como vieram

> **Why:** Pôr no landing os bytes dos dois arquivos de referência do INSS, com prova de procedência — o primeiro passo do medalhão, que a especie v1 pulou. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Pôr no landing os bytes dos dois arquivos de referência do INSS, com prova de procedência — o primeiro passo do medalhão, que a especie v1 pulou. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-REFERENCIA-MEDALHAO; seam SEAM-LANDING-REFERENCIA; swimlane LANE-LANDING-REFERENCIA; capability leg LEG-LANDING-REFERENCIA. Done condition: src/produtor/landing_referencia.py copia os bytes dos dois .xlsx para o landing, prova, relê e confere; é idempotente; nunca sobrescreve; os testes de tests/test_landing_referencia.py passam.

## Behavior

- **B-1** — GIVEN os arquivos dicionario-especies-beneficio.xlsx e glossario-beneficios-emitidos.xlsx num diretório de origem com CHECKSUMS.txt, e um destino WHEN landing_referencia.gravar(spark, origem, destino, arquivos) roda THEN para cada arquivo: confere o sha256 dos bytes contra a linha do CHECKSUMS.txt (formato '<sha256>  _raw/<arquivo>', casada pelo NOME), e só então copia os bytes, SEM alterar nenhum, para <destino>/<nome sem extensão>/sha256=<sha256>/<arquivo> pelo FileSystem do Hadoop, grava ao lado a _PROCEDENCIA.json com arquivo, sha256, tamanho, origem e instante, relê os bytes gravados e confere o sha256; devolve GRAVADO por arquivo. O padrão do destino é s3a://landing/pda/referencia e o da origem é /dados/_raw. Uma segunda execução devolve INTEGRO sem regravar nada SÓ se os bytes E a _PROCEDENCIA.json existem e conferem entre si (sha256 e tamanho).
- **B-2** — GIVEN uma origem ou um destino que não conferem WHEN landing_referencia.gravar roda THEN sha256 divergente do CHECKSUMS.txt ou arquivo ausente devolvem NAO_MEDIDO sem gravar nada; no destino, objeto com bytes diferentes, bytes sem _PROCEDENCIA.json (tentativa interrompida) ou prova com sha256 ou tamanho divergente, ou prova existente SEM o arquivo, devolvem DIVERGE e NADA é sobrescrito nem apagado — nem a prova é recriada — a retomada é decisão do dono; os arquivos aceitos são só os dois nomeados — outro nome recusa. Cada arquivo é INDEPENDENTE e tem o seu resultado: um ausente ou recusado não desfaz nem impede o outro, e o resultado da chamada lista os dois. Nenhum cenário usa skip, xfail ou importorskip; os testes GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde o cenário pede, e MinIO indisponível FALHA o teste; a sessão Spark do teste é uma fixture de módulo ou sessão, e nenhuma função a para.

## Success Criteria

```bash
# eval_1: Bytes como vieram, com prova
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grava_os_bytes_como_vieram prova_ao_lado_do_arquivo rele_e_confere_o_sha256; do python3 -m pytest --collect-only -q tests/test_landing_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_landing_referencia.py -k "grava_os_bytes_como_vieram or prova_ao_lado_do_arquivo or rele_e_confere_o_sha256"'
}

# eval_2: Idempotente e sem sobrescrever
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in segunda_execucao_integro_sem_regravar objeto_divergente_nao_sobrescreve bytes_sem_prova_diverge prova_sem_arquivo_diverge; do python3 -m pytest --collect-only -q tests/test_landing_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_landing_referencia.py -k "segunda_execucao_integro_sem_regravar or objeto_divergente_nao_sobrescreve or bytes_sem_prova_diverge or prova_sem_arquivo_diverge"'
}

# eval_3: Recusas
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sha256_divergente_nao_grava arquivo_ausente_nao_medido arquivo_fora_da_lista_recusa resultado_por_arquivo; do python3 -m pytest --collect-only -q tests/test_landing_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_landing_referencia.py -k "sha256_divergente_nao_grava or arquivo_ausente_nao_medido or arquivo_fora_da_lista_recusa or resultado_por_arquivo"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Bytes como vieram, com prova"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Idempotente e sem sobrescrever"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
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

referências recusadas por sha256

## Anti-Patterns

- Do not converter o .xlsx para CSV ou Parquet no landing: o landing guarda a fonte como veio; instead os bytes, iguais.
- Do not sobrescrever um objeto existente: destrói a evidência; instead DIVERGE.
- Do not ler de _raw em qualquer camada seguinte: o medalhão lê a camada anterior; instead só este módulo lê _raw.

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

## Open Questions

(none — this task is fully specified)
