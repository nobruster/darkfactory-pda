---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-ESPECIE-DA-BRONZE
seam_id: SEAM-ESPECIE-DA-BRONZE
swimlane_id: LANE-ESPECIE-DA-BRONZE
observable_state: Especie da Bronze
proof: 'Ponta a ponta sobre a referência real: 65/65/43.'
requires:
- glossario na silver
produces:
- especie da bronze
tasks:
- id: T-20260924-especie-da-bronze
  title: A especie tira os nomes da Bronze do dicionário
  goal: Fazer a especie da Silver ler os nomes oficiais da Bronze do dicionário — não do YAML —, com a
    linhagem das duas camadas anteriores. Para rodar testes, o ÚNICO comando liberado ao agente é `docker
    compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.
  done_condition: src/medalhao/especie.py tem publicar_especie_da_bronze; a publicar_especie existente
    e seus testes ficam intactos; os testes novos de tests/test_especie.py passam, incluindo o de ponta
    a ponta com a referência real.
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
  - T-20260924-silver-glossario
  touches_paths:
  - src/medalhao/especie.py
  - tests/test_especie.py
  creates_paths: []
  behavior:
  - id: B-1
    given: a Bronze do dicionário publicada por bronze_referencia e uma Silver de benefícios
    when: especie.publicar_especie_da_bronze(spark, bronze_dicionario, sha256, sha256_aprovado, silver,
      destino, competencia, grupos) roda, com grupos vindos de contrato.grupos_especie e sha256_aprovado
      vindo da fonte aprovada na ontologia versionada
    then: 'se sha256 difere de sha256_aprovado, recusa SEM ler nem gravar, com o motivo DICIONARIO_NAO_APROVADO
      — um dicionário novo do INSS só entra depois de o dono aprová-lo, como o ADR 0014 já exigia; lê
      a Bronze do dicionário e a Silver cada uma numa versão fixada no início, SELECIONA sha256_arquivo
      igual ao pedido antes de conformar (ausente devolve NAO_MEDIDO); conforma os nomes a partir da Bronze
      — linha com coluna_a numérica vira código de 2 dígitos e coluna_b é o nome oficial COMO VEIO; o
      cabeçalho e as vazias são descartados E CONTADOS; duas linhas que caem no MESMO código depois de
      conformadas (ex.: ''1'' e ''01'') recusam com CODIGO_COLIDIDO, nunca uma é escolhida —; grava com
      o MESMO schema e as mesmas regras da especie atual (descricao_fonte como veio, texto_fonte_confere_prefixo,
      replaceWhere da competência, reconferência do próprio commit); o commit leva a versão da Silver,
      a versão da Bronze do dicionário, o sha256 do arquivo e os descartes. Nenhuma função existente de
      especie.py muda de comportamento.'
  - id: B-2
    given: o tests/test_especie.py selado
    when: a tarefa acrescenta os testes
    then: todos os test_* existentes ficam como estão e passam; entram só test_especie_da_bronze_nomes_da_bronze,
      test_especie_da_bronze_linhagem_das_duas_camadas, test_especie_da_bronze_conta_descartes, test_especie_da_bronze_codigo_fora_recusa,
      test_especie_da_bronze_dicionario_nao_aprovado_recusa, test_especie_da_bronze_codigo_colidido_recusa
      e test_especie_da_bronze_ponta_a_ponta_real — este grava, em tmp_path, o landing e a Bronze de referência
      a partir de /dados/_raw pelos módulos das tarefas anteriores e exige, sobre a Silver real de 2026-01,
      65 linhas, 65 nomes distintos, 43 com o prefixo conferindo, e cada nome IGUAL ao da ontologia versionada
      — extraído por OUTRO parser (medalhao.ontologia), a evidência independente de que o parser da Bronze
      leu a planilha certo. Nenhum cenário usa skip, xfail ou importorskip; os testes GRAVAM só em tmp_path,
      nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde o cenário pede, e MinIO indisponível
      FALHA o teste; a sessão Spark do teste é uma fixture de módulo ou sessão, e nenhuma função a para.
  evals:
  - id: eval_1
    description: Nomes da Bronze, com linhagem
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in especie_da_bronze_nomes_da_bronze
      especie_da_bronze_linhagem_das_duas_camadas especie_da_bronze_conta_descartes; do python3 -m pytest
      --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_especie.py -k "especie_da_bronze_nomes_da_bronze
      or especie_da_bronze_linhagem_das_duas_camadas or especie_da_bronze_conta_descartes"'
    verifies:
    - B-1
  - id: eval_2
    description: Ponta a ponta e recusa
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in especie_da_bronze_ponta_a_ponta_real
      especie_da_bronze_codigo_fora_recusa especie_da_bronze_dicionario_nao_aprovado_recusa especie_da_bronze_codigo_colidido_recusa;
      do python3 -m pytest --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::"
      || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_especie.py
      -k "especie_da_bronze_ponta_a_ponta_real or especie_da_bronze_codigo_fora_recusa or especie_da_bronze_dicionario_nao_aprovado_recusa
      or especie_da_bronze_codigo_colidido_recusa"'
    verifies:
    - B-1
    - B-2
  - id: eval_3
    description: A especie antiga intacta
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grava_nome_oficial_e_texto_da_fonte
      reconferencia_acusa_linha_alterada outra_competencia_intacta; do python3 -m pytest --collect-only
      -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_especie.py -k "grava_nome_oficial_e_texto_da_fonte
      or reconferencia_acusa_linha_alterada or outra_competencia_intacta"'
    verifies:
    - B-2
  anti_patterns:
  - action: mudar publicar_especie ou um teste existente
    reason: acrescentar, não mudar
    instead: função nova ao lado
  - action: ler os nomes do YAML ou de _raw
    reason: a Silver lê a Bronze
    instead: a Bronze do dicionário
  - action: aparar o nome oficial
    reason: o nome é o texto da fonte
    instead: como veio
  do_not_touch:
  - _raw
  - contracts
  - cvg/docs/adrs
  - src/pda
  - src/ontologia
  - infra
  - src/medalhao/ontologia.py
  - src/medalhao/projecao_postgres.py
  - src/medalhao/bronze.py
  - tests/test_bronze.py
  - src/produtor/landing_referencia.py
  - src/medalhao/bronze_referencia.py
  - src/medalhao/glossario.py
  rollback: Reverter src/medalhao/especie.py e tests/test_especie.py.
  observability: nomes divergentes da Bronze
source_seam_sha256: 6859b0449c65bdc48ce0a881acfbf2182384fd803c978f25066090912eec00d7
---
# Especie da Bronze

## Observable proof

Ponta a ponta sobre a referência real: 65/65/43.

## Runnable leaves

- `T-20260924-especie-da-bronze` — A especie tira os nomes da Bronze do dicionário: src/medalhao/especie.py tem publicar_especie_da_bronze; a publicar_especie existente e seus testes ficam intactos; os testes novos de tests/test_especie.py passam, incluindo o de ponta a ponta com a referência real.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
