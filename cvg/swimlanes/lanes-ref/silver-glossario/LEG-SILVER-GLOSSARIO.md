> Projetado de `LEG-SILVER-GLOSSARIO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `a0cb1738d5975cf22b40787126adf528b53e02ba286b4bdd905a9fe59a31b4a7`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-SILVER-GLOSSARIO
seam_id: SEAM-SILVER-GLOSSARIO
swimlane_id: LANE-SILVER-GLOSSARIO
observable_state: Glossário na Silver
proof: 13 termos, descartes contados, linhagem.
requires:
- referencia na bronze
produces:
- glossario na silver
tasks:
- id: T-20260924-silver-glossario
  title: O glossário conformado na Silver, a partir da Bronze
  goal: Conformar o glossário do INSS na Silver, lendo da Bronze de referência. Para rodar testes, o ÚNICO
    comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m
    pytest <arquivo> -k <cenarios>`.
  done_condition: src/medalhao/glossario.py publica silver/pda/glossario a partir da Bronze, com a linhagem;
    os testes de tests/test_glossario.py passam.
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
  - T-20260924-bronze-referencia
  touches_paths: []
  creates_paths:
  - src/medalhao/glossario.py
  - tests/test_glossario.py
  behavior:
  - id: B-1
    given: a Bronze do glossário publicada por bronze_referencia em tmp_path
    when: glossario.publicar(spark, bronze, destino, sha256, sha256_aprovado) roda
    then: 'se sha256 difere de sha256_aprovado (o da fonte aprovada na ontologia), recusa SEM ler nem
      gravar, com o motivo GLOSSARIO_NAO_APROVADO — a mesma proteção da especie (ADR 0015); lê a Bronze
      numa versão fixada no início e SELECIONA sha256_arquivo igual ao pedido ANTES de conformar — sha256
      pedido ausente na versão lida devolve NAO_MEDIDO —; conforma NESTA ORDEM: primeiro apara as pontas
      de termo e descrição, depois descarta como vazia só a linha com as DUAS células vazias, depois recusa
      termo vazio com descrição preenchida e termo repetido (já aparado); descarta a linha de cabeçalho
      (coluna_a ''Nome'') e as vazias, CONTANDO os descartes, tira espaços das pontas de termo e descrição,
      e grava em Delta, padrão s3a://silver/pda/glossario, uma linha por termo — termo, descricao, sha256_arquivo
      —, por replaceWhere de sha256_arquivo; o commit leva a versão da Bronze lida, o sha256 e os descartes;
      relê o próprio commit e confere. Sobre a referência real, são 13 termos.'
  - id: B-2
    given: uma Bronze com termo repetido, termo vazio com descrição, ou nenhum termo
    when: glossario.publicar roda
    then: recusa SEM gravar termo repetido e termo vazio; nenhum termo devolve NAO_MEDIDO. Nenhum cenário
      usa skip, xfail ou importorskip; os testes GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou
      /dados/_raw é permitido onde o cenário pede, e MinIO indisponível FALHA o teste; a sessão Spark
      do teste é uma fixture de módulo ou sessão, e nenhuma função a para.
  evals:
  - id: eval_1
    description: Conformado com linhagem
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in conforma_e_conta_descartes
      linhagem_da_bronze_no_commit treze_termos_na_referencia_real; do python3 -m pytest --collect-only
      -q tests/test_glossario.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_glossario.py -k "conforma_e_conta_descartes or
      linhagem_da_bronze_no_commit or treze_termos_na_referencia_real"'
    verifies:
    - B-1
  - id: eval_2
    description: Reconferência e versão fixada
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reconfere_o_proprio_commit
      le_a_bronze_na_versao_fixada; do python3 -m pytest --collect-only -q tests/test_glossario.py -k
      "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m
      pytest -q tests/test_glossario.py -k "reconfere_o_proprio_commit or le_a_bronze_na_versao_fixada"'
    verifies:
    - B-1
  - id: eval_3
    description: Recusas
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in termo_repetido_recusa
      termo_repetido_so_depois_de_aparar_recusa termo_vazio_recusa sem_termos_nao_medido glossario_nao_aprovado_recusa;
      do python3 -m pytest --collect-only -q tests/test_glossario.py -k "$c" 2>/dev/null | grep -q "::"
      || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_glossario.py
      -k "termo_repetido_recusa or termo_repetido_so_depois_de_aparar_recusa or termo_vazio_recusa or
      sem_termos_nao_medido or glossario_nao_aprovado_recusa"'
    verifies:
    - B-2
  anti_patterns:
  - action: ler o glossário de _raw ou do YAML
    reason: a Silver lê a Bronze
    instead: a Bronze
  - action: descartar linha sem contar
    reason: Regra 9
    instead: contar e registrar no commit
  - action: reescrever a descrição do INSS
    reason: é o texto da fonte
    instead: só aparar as pontas
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
  - src/medalhao/especie.py
  - tests/test_especie.py
  - src/produtor/landing_referencia.py
  - src/medalhao/bronze_referencia.py
  rollback: Remover os dois arquivos criados.
  observability: glossário recusado
source_seam_sha256: 166f68c576dfacd6ba523596a5443a856423123d9bc0e8ab72049768365183d6
---
# Glossário na Silver

## Observable proof

13 termos, descartes contados, linhagem.

## Runnable leaves

- `T-20260924-silver-glossario` — O glossário conformado na Silver, a partir da Bronze: src/medalhao/glossario.py publica silver/pda/glossario a partir da Bronze, com a linhagem; os testes de tests/test_glossario.py passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
