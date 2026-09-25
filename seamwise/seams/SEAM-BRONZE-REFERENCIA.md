---
schema_version: 1
kind: seam
claim: derived
id: SEAM-BRONZE-REFERENCIA
name: Bronze de referência
description: Separa as linhas como vieram da conformação.
evidence:
- E-ANCORA-202601
responsibility: Pôr as linhas das planilhas em Delta, lidas do landing.
consumes:
- referencia no landing
produces: &id001
- referencia na bronze
owner: medalhao
independent_proof: Multiconjunto do próprio commit igual ao lido.
decision_ids:
- DEC-REFERENCIA-PELO-MEDALHAO
rejected_alternatives:
- alternative: Especie gravada direto na Silver a partir do YAML
  reason: pula landing e Bronze; os bytes da fonte nunca entram no lago.
swimlane:
  id: LANE-BRONZE-REFERENCIA
  name: Bronze de referência lane
  owner: medalhao
  legs:
  - id: LEG-BRONZE-REFERENCIA
    observable_state: Bronze de referência
    proof: Multiconjunto do próprio commit igual ao lido.
    requires:
    - referencia no landing
    produces: *id001
    tasks:
    - id: T-20260924-bronze-referencia
      title: A Bronze do dicionário e do glossário, lida do landing
      goal: Pôr em Delta as linhas dos dois arquivos de referência como vieram, lidas do landing. Para
        rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml
        exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.
      done_condition: src/medalhao/bronze_referencia.py lê do landing — nunca de _raw —, confere a prova
        e publica as duas tabelas Bronze com as linhas como vieram e a linhagem no commit; os testes de
        tests/test_bronze_referencia.py passam.
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
      - T-20260924-landing-referencia
      touches_paths: []
      creates_paths:
      - src/medalhao/bronze_referencia.py
      - tests/test_bronze_referencia.py
      behavior:
      - id: B-1
        given: o landing de referência gravado por landing_referencia em tmp_path
        when: bronze_referencia.publicar(spark, landing, destino, arquivo, sha256) roda
        then: 'lê os bytes da partição sha256=<sha256> DO LANDING, confere que o sha256 dos bytes lidos
          é o da _PROCEDENCIA.json e o do nome da partição, e lê a planilha com um parser PRÓPRIO deste
          módulo, só com a biblioteca padrão (zipfile sobre io.BytesIO e xml) — NÃO medalhao.ontologia.ler_xlsx,
          que descarta linhas sem valor e não devolve o número da linha (medido: o dicionário tem 69 elementos
          <row>, 2 sem valor; o glossário 24, 10 sem valor). O arquivo tem de ter EXATAMENTE uma planilha,
          senão recusa. Grava em Delta, por replaceWhere de sha256_arquivo, um registro por elemento <row>
          COMO VEIO: linha = o número do atributo r do <row> (nunca uma contagem), coluna_a e coluna_b
          em texto sem trim (célula ausente é nula), arquivo e sha256_arquivo — o cabeçalho e os <row>
          sem valor entram também, porque a Bronze não filtra; uma linha que o XML não traz não é inventada;
          o dicionário vai para <destino>/dicionario_especies e o glossário para <destino>/glossario,
          padrão s3a://bronze/pda/referencia; o commit leva em userMetadata a partição do landing lida,
          o sha256 da prova, o id_execucao e o número de linhas; depois relê a versão do PRÓPRIO commit
          e confere o multiconjunto nos dois sentidos.'
      - id: B-2
        given: uma prova divergente, uma planilha sem linhas, ou um pedido que leria _raw
        when: bronze_referencia.publicar roda
        then: sha256 dos bytes diferente da prova ou do nome da partição recusa SEM gravar; planilha sem
          nenhuma linha devolve NAO_MEDIDO; o módulo não tem caminho para /dados/_raw — um teste confere
          pelo AST do módulo que ele não referencia _raw. Nenhum cenário usa skip, xfail ou importorskip;
          os testes GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde
          o cenário pede, e MinIO indisponível FALHA o teste; a sessão Spark do teste é uma fixture de
          módulo ou sessão, e nenhuma função a para.
      evals:
      - id: eval_1
        description: Linhas como vieram, lidas do landing
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in linhas_como_vieram
          cabecalho_e_vazias_entram numero_da_linha_e_o_do_xml linhagem_do_landing_no_commit; do python3
          -m pytest --collect-only -q tests/test_bronze_referencia.py -k "$c" 2>/dev/null | grep -q "::"
          || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze_referencia.py
          -k "linhas_como_vieram or cabecalho_e_vazias_entram or numero_da_linha_e_o_do_xml or linhagem_do_landing_no_commit"'
        verifies:
        - B-1
      - id: eval_2
        description: Reconferência e idempotência
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reconfere_o_proprio_commit
          republicar_mesmo_sha_substitui_so_a_particao; do python3 -m pytest --collect-only -q tests/test_bronze_referencia.py
          -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
          -m pytest -q tests/test_bronze_referencia.py -k "reconfere_o_proprio_commit or republicar_mesmo_sha_substitui_so_a_particao"'
        verifies:
        - B-1
      - id: eval_3
        description: Recusas e nada de _raw
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in prova_divergente_nao_grava
          planilha_vazia_nao_medido mais_de_uma_planilha_recusa modulo_nao_le_raw; do python3 -m pytest
          --collect-only -q tests/test_bronze_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo
          "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze_referencia.py
          -k "prova_divergente_nao_grava or planilha_vazia_nao_medido or mais_de_uma_planilha_recusa or
          modulo_nao_le_raw"'
        verifies:
        - B-2
      anti_patterns:
      - action: ler o .xlsx de _raw
        reason: a Bronze lê o landing
        instead: os bytes da partição
      - action: filtrar o cabeçalho ou as linhas vazias na Bronze
        reason: a Bronze guarda como veio
        instead: a Silver conforma
      - action: aparar ou converter texto
        reason: a Bronze guarda como veio
        instead: a Silver conforma
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
      rollback: Remover os dois arquivos criados.
      observability: referências recusadas pela prova
---
# Bronze de referência

Separa as linhas como vieram da conformação.

## Responsibility

Pôr as linhas das planilhas em Delta, lidas do landing.

## Independent proof

Multiconjunto do próprio commit igual ao lido.

## Rejected alternatives

- **Especie gravada direto na Silver a partir do YAML** — pula landing e Bronze; os bytes da fonte nunca entram no lago.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
