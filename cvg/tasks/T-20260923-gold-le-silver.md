---
id: T-20260923-gold-le-silver
title: "Gold principal a partir da versão da Silver"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260923-ingestao-julgada]
supersedes: (none)
touches_paths: [src/medalhao/gold.py, tests/test_gold.py]
creates_paths: []
source_note: "seamwise/legs/LEG-GOLD-LE-SILVER.md#T-20260923-gold-le-silver"
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
signed_off_at: 2026-09-23T21:44:00Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:3f52074eb672e2a2b46049cee055a0909bac0bbcf34400ac172d10fb83855411
---

# Gold principal a partir da versão da Silver

> **Why:** Tirar da Gold a leitura do arquivo inteiro.

## Goal

Tirar da Gold a leitura do arquivo inteiro.

## Context

Intent DI-PDA-MEDALHAO-V4; seam SEAM-GOLD-LE-SILVER; swimlane LANE-GOLD-LE-SILVER; capability leg LEG-GOLD-LE-SILVER. Done condition: Sobre a Silver INTEGRO cuja Bronze tem pacote ACEITO, a Gold principal publica fechando exato com a âncora sem ler landing nem CSV; sem essa linhagem, nada é publicado.

## Behavior

- **B-1** — GIVEN a Silver publicada INTEGRO e a Bronze que ela leu, com pacote ACEITO no commit WHEN a Gold principal roda pela entrada nova THEN resolve UMA vez a versão da Silver, lê com versionAsOf, segue a versão da Bronze nos metadados da Silver e confere que o commit dessa Bronze nomeia um pacote ACEITO da mesma competência e do mesmo sha256 do CSV; agrega por código reusando agregar, confere exato contra os controles persistidos da Silver e a âncora, e publica pelo protocolo que já existe, com o userMetadata nomeando a versão da Silver e o pacote. NÃO abre a landing nem o CSV. Antes de confiar no pacote, recalcula o sha256 dos BYTES do arquivo em caminho_pacote e compara com o sha256 que o commit da Bronze registrou; bytes diferentes são DIVERGE.
- **B-2** — GIVEN uma Silver sem linhagem até um pacote ACEITO, ou com estado diferente de INTEGRO WHEN a Gold principal roda pela entrada nova THEN devolve NAO_MEDIDO sem pacote ACEITO na linhagem e DIVERGE quando a soma não fecha, sem publicar nada; a entrada antiga continua existindo para os testes selados, e nenhum teste já existente de tests/test_gold.py é editado.

## Success Criteria

```bash
# eval_1: Lê só a Silver e segue a linhagem
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_le_so_a_silver nao_abre_landing_nem_csv linhagem_ate_pacote_aceito sha256_do_pacote_conferido; do python3 -m pytest --collect-only -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold.py -k "gold_le_so_a_silver or nao_abre_landing_nem_csv or linhagem_ate_pacote_aceito or sha256_do_pacote_conferido"'
}

# eval_2: Fecha exato e nomeia as versões
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_da_silver_fecha_com_a_ancora commit_nomeia_silver_e_pacote; do python3 -m pytest --collect-only -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold.py -k "gold_da_silver_fecha_com_a_ancora or commit_nomeia_silver_e_pacote"'
}

# eval_3: Sem linhagem, nada publica
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sem_pacote_aceito_nao_medido silver_nao_integra_nao_publica gold_soma_que_nao_fecha_diverge; do python3 -m pytest --collect-only -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold.py -k "sem_pacote_aceito_nao_medido or silver_nao_integra_nao_publica or gold_soma_que_nao_fecha_diverge"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Lê só a Silver e segue a linhagem"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Fecha exato e nomeia as versões"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Sem linhagem, nada publica"
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

Reverter src/medalhao/gold.py e tests/test_gold.py ao commit assentado.

## Observability Hooks

publicações da Gold sem versão da Silver no commit

## Anti-Patterns

- Do not chamar leitura.ler_competencia na Gold: é a leitura do arquivo inteiro que a decisão tirou daqui; instead confiar no pacote ACEITO da ingestão, pela linhagem.
- Do not recalcular Bronze e Silver da landing: ignora a Silver publicada e perde a linhagem; instead ler a Silver por versionAsOf.
- Do not editar um teste já existente de tests/test_gold.py: teste selado que precisa mudar denuncia mudança de comportamento; instead acrescentar a entrada nova e testes novos.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/pda`

## Open Questions

(none — this task is fully specified)
