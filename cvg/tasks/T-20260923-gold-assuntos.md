---
id: T-20260923-gold-assuntos
title: "Publicar fat_especie e kpis_nacionais a partir da Silver"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260923-contrato-expoe-grupos, T-20260923-gold-le-silver]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/gold_assuntos.py, tests/test_gold_assuntos.py]
source_note: "seamwise/legs/LEG-GOLD-ASSUNTOS.md#T-20260923-gold-assuntos"
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
signed_off_at: 2026-09-23T21:44:03Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:d6e673e25e021bb7cb49a4ec78ecf9cd9329d29808aa5fb393f829b9b752fa7f
---

# Publicar fat_especie e kpis_nacionais a partir da Silver

> **Why:** Entregar ao cliente as tabelas por assunto da Fase 1, reconciliadas.

## Goal

Entregar ao cliente as tabelas por assunto da Fase 1, reconciliadas.

## Context

Intent DI-PDA-MEDALHAO-V4; seam SEAM-GOLD-ASSUNTOS; swimlane LANE-GOLD-ASSUNTOS; capability leg LEG-GOLD-ASSUNTOS. Done condition: Sobre uma Silver INTEGRO e uma Gold principal publicada, as duas tabelas são publicadas fechando exato com a âncora; faltando qualquer pré-condição, nada é publicado.

## Behavior

- **B-1** — GIVEN a Silver publicada com estado INTEGRO, a Gold principal da competência publicada, e grupos_especie no Contrato WHEN a Gold por assuntos roda para a competência THEN lê a versão da Silver NOMEADA no commit da Gold principal publicada da competência — nunca a mais recente —, com versionAsOf; num único groupBy por especie_codigo monta fat_especie — grão (especie_codigo, competencia), com descrição, grupo_especie do mapa, qtd_beneficios, vl_total em soma EXATA no DecimalType declarado, vl_minimo, vl_maximo, qtd_vl_zero, vl_medio arredondado meio-para-par com bround, vl_mediano_aprox e vl_p90_aprox — nomes que dizem que são aproximados — com a precisão do percentil declarada, rank_no_grupo e percentuais nacionais —; kpis_nacionais sai de fat_especie, grão competência, uma linha, com colunas ENUMERADAS — total_beneficios e vl_total como somas, vl_medio = bround(vl_total / total_beneficios, 2), NUNCA a média das médias por espécie, vl_minimo o menor dos mínimos, vl_maximo o maior dos máximos, total_especies_ativas, qtd_vl_zero somado —, e só vl_mediano_aprox e vl_p90_aprox nacionais exigem outra passada. Antes de publicar, confere EXATO: soma de qtd_beneficios igual a count_linhas da âncora, soma de vl_total igual a sum_vl_liquido, o menor vl_minimo igual a min_vl_liquido e o maior vl_maximo igual a max_vl_liquido da âncora, linhas_invalidas zero — os CINCO controles —, kpis_nacionais com os mesmos totais, 65 códigos, cada um em um grupo. Grava em preparo e publica com replaceWhere na competência em s3a://gold/pda/assuntos/fat_especie e s3a://gold/pda/assuntos/kpis_nacionais, DecimalType do contrato, ansi.enabled=true, CHECK >= 0 nas colunas monetárias, imposição de schema ligada e evolução só aditiva com mergeSchema — nunca overwriteSchema —, e o userMetadata do commit nomeia a versão da Silver e a da Gold principal lidas.
- **B-2** — GIVEN uma competência sem Gold principal publicada, sem grupos_especie, com código fora do mapa, ou cujas somas não fecham WHEN a Gold por assuntos roda THEN sem Gold principal publicada ou sem grupos_especie devolve NAO_MEDIDO; código fora do mapa ou soma que não fecha devolve DIVERGE nomeando a diferença; em nenhum dos casos publica nada, e nenhuma tolerância é aceita — a igualdade é exata, porque tolerância aqui seria afrouxar o oráculo.

## Success Criteria

```bash
# eval_1: Grão, colunas e fechamento exato
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_especie_fecha_com_a_ancora kpis_somam_fat_especie medio_arredonda_meio_para_par percentis_rotulados_aprox le_silver_por_versao usa_a_silver_nomeada_pela_gold extremos_conferem_com_a_ancora medio_nacional_nao_e_media_das_medias; do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py -k "fat_especie_fecha_com_a_ancora or kpis_somam_fat_especie or medio_arredonda_meio_para_par or percentis_rotulados_aprox or le_silver_por_versao or usa_a_silver_nomeada_pela_gold or extremos_conferem_com_a_ancora or medio_nacional_nao_e_media_das_medias"'
}

# eval_2: Delta com a doutrina
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in publica_com_replacewhere check_nao_negativo_monetario commit_nomeia_versoes_lidas; do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py -k "publica_com_replacewhere or check_nao_negativo_monetario or commit_nomeia_versoes_lidas"'
}

# eval_3: Nada publica sem pré-condição
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sem_gold_principal_nao_medido sem_grupos_nao_medido codigo_fora_do_mapa_diverge soma_que_nao_fecha_diverge; do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py -k "sem_gold_principal_nao_medido or sem_grupos_nao_medido or codigo_fora_do_mapa_diverge or soma_que_nao_fecha_diverge"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Grão, colunas e fechamento exato"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Delta com a doutrina"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Nada publica sem pré-condição"
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

Remover as duas tabelas por assunto; Silver e Gold principal não são tocadas.

## Observability Hooks

competências publicadas na Gold principal sem tabelas por assunto

## Anti-Patterns

- Do not validar com tolerância (< 10 linhas, ~100%): tolerância afrouxa o oráculo e esconde centavo sumido; instead igualdade exata contra a âncora.
- Do not usar overwriteSchema ou round (meio-para-cima): apaga schema em silêncio; arredonda contra o ADR; instead mergeSchema só aditivo; bround meio-para-par.
- Do not comparar especie_codigo com inteiros: '01' não casa com 1 e tudo cai fora do grupo em silêncio; instead usar os códigos texto do grupos_especie.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/medalhao/gold.py`

## Open Questions

(none — this task is fully specified)
