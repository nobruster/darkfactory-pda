> Projetado de `LEG-GOLD-ASSUNTOS.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `fb269990da7b9931c7f7e9249e797263d35a70b4ac3333d8999e0d136b7024fb`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-GOLD-ASSUNTOS
seam_id: SEAM-GOLD-ASSUNTOS
swimlane_id: LANE-GOLD-ASSUNTOS
observable_state: fat_especie e kpis_nacionais publicadas e reconciliadas
proof: Cada tabela fecha exato com a âncora antes do commit que a publica.
requires:
- contrato com grupos
- gold principal publicada
produces:
- gold por assuntos
tasks:
- id: T-20260923-gold-assuntos
  title: Publicar fat_especie e kpis_nacionais a partir da Silver
  goal: Entregar ao cliente as tabelas por assunto da Fase 1, reconciliadas.
  done_condition: Sobre uma Silver INTEGRO e uma Gold principal publicada, as duas tabelas são publicadas
    fechando exato com a âncora; faltando qualquer pré-condição, nada é publicado.
  effort: S
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  depends_on:
  - T-20260923-contrato-expoe-grupos
  - T-20260923-gold-le-silver
  touches_paths: []
  creates_paths:
  - src/medalhao/gold_assuntos.py
  - tests/test_gold_assuntos.py
  behavior:
  - id: B-1
    given: a Silver publicada com estado INTEGRO, a Gold principal da competência publicada, e grupos_especie
      no Contrato
    when: a Gold por assuntos roda para a competência
    then: 'lê a versão da Silver NOMEADA no commit da Gold principal publicada da competência — nunca
      a mais recente —, com versionAsOf; num único groupBy por especie_codigo monta fat_especie — grão
      (especie_codigo, competencia), com descrição, grupo_especie do mapa, qtd_beneficios, vl_total em
      soma EXATA no DecimalType declarado, vl_minimo, vl_maximo, qtd_vl_zero, vl_medio arredondado meio-para-par
      com bround, vl_mediano_aprox e vl_p90_aprox — nomes que dizem que são aproximados — com a precisão
      do percentil declarada, rank_no_grupo e percentuais nacionais —; kpis_nacionais sai de fat_especie,
      grão competência, uma linha, com colunas ENUMERADAS — total_beneficios e vl_total como somas, vl_medio
      = bround(vl_total / total_beneficios, 2), NUNCA a média das médias por espécie, vl_minimo o menor
      dos mínimos, vl_maximo o maior dos máximos, total_especies_ativas, qtd_vl_zero somado —, e só vl_mediano_aprox
      e vl_p90_aprox nacionais exigem outra passada. Antes de publicar, confere EXATO: soma de qtd_beneficios
      igual a count_linhas da âncora, soma de vl_total igual a sum_vl_liquido, o menor vl_minimo igual
      a min_vl_liquido e o maior vl_maximo igual a max_vl_liquido da âncora, linhas_invalidas zero — os
      CINCO controles —, kpis_nacionais com os mesmos totais, 65 códigos, cada um em um grupo. Grava em
      preparo e publica com replaceWhere na competência em s3a://gold/pda/assuntos/fat_especie e s3a://gold/pda/assuntos/kpis_nacionais,
      DecimalType do contrato, ansi.enabled=true, CHECK >= 0 nas colunas monetárias, imposição de schema
      ligada e evolução só aditiva com mergeSchema — nunca overwriteSchema —, e o userMetadata do commit
      nomeia a versão da Silver e a da Gold principal lidas.'
  - id: B-2
    given: uma competência sem Gold principal publicada, sem grupos_especie, com código fora do mapa,
      ou cujas somas não fecham
    when: a Gold por assuntos roda
    then: sem Gold principal publicada ou sem grupos_especie devolve NAO_MEDIDO; código fora do mapa ou
      soma que não fecha devolve DIVERGE nomeando a diferença; em nenhum dos casos publica nada, e nenhuma
      tolerância é aceita — a igualdade é exata, porque tolerância aqui seria afrouxar o oráculo.
  evals:
  - id: eval_1
    description: Grão, colunas e fechamento exato
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_especie_fecha_com_a_ancora
      kpis_somam_fat_especie medio_arredonda_meio_para_par percentis_rotulados_aprox le_silver_por_versao
      usa_a_silver_nomeada_pela_gold extremos_conferem_com_a_ancora medio_nacional_nao_e_media_das_medias;
      do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q
      "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py
      -k "fat_especie_fecha_com_a_ancora or kpis_somam_fat_especie or medio_arredonda_meio_para_par or
      percentis_rotulados_aprox or le_silver_por_versao or usa_a_silver_nomeada_pela_gold or extremos_conferem_com_a_ancora
      or medio_nacional_nao_e_media_das_medias"'
    verifies:
    - B-1
  - id: eval_2
    description: Delta com a doutrina
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in publica_com_replacewhere
      check_nao_negativo_monetario commit_nomeia_versoes_lidas; do python3 -m pytest --collect-only -q
      tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py -k "publica_com_replacewhere or
      check_nao_negativo_monetario or commit_nomeia_versoes_lidas"'
    verifies:
    - B-1
  - id: eval_3
    description: Nada publica sem pré-condição
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sem_gold_principal_nao_medido
      sem_grupos_nao_medido codigo_fora_do_mapa_diverge soma_que_nao_fecha_diverge; do python3 -m pytest
      --collect-only -q tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py -k "sem_gold_principal_nao_medido
      or sem_grupos_nao_medido or codigo_fora_do_mapa_diverge or soma_que_nao_fecha_diverge"'
    verifies:
    - B-2
  anti_patterns:
  - action: validar com tolerância (< 10 linhas, ~100%)
    reason: tolerância afrouxa o oráculo e esconde centavo sumido
    instead: igualdade exata contra a âncora
  - action: usar overwriteSchema ou round (meio-para-cima)
    reason: apaga schema em silêncio; arredonda contra o ADR
    instead: mergeSchema só aditivo; bround meio-para-par
  - action: comparar especie_codigo com inteiros
    reason: '''01'' não casa com 1 e tudo cai fora do grupo em silêncio'
    instead: usar os códigos texto do grupos_especie
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src/medalhao/gold.py
  rollback: Remover as duas tabelas por assunto; Silver e Gold principal não são tocadas.
  observability: competências publicadas na Gold principal sem tabelas por assunto
source_seam_sha256: 4a0ad0529836162b83790ac7824107b02c788898b59800f244e467aa5f2bbecf
---
# fat_especie e kpis_nacionais publicadas e reconciliadas

## Observable proof

Cada tabela fecha exato com a âncora antes do commit que a publica.

## Runnable leaves

- `T-20260923-gold-assuntos` — Publicar fat_especie e kpis_nacionais a partir da Silver: Sobre uma Silver INTEGRO e uma Gold principal publicada, as duas tabelas são publicadas fechando exato com a âncora; faltando qualquer pré-condição, nada é publicado.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
