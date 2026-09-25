---
schema_version: 1
kind: seam
claim: derived
id: SEAM-GOLD-REFERENCIA
name: Referência na Gold
description: Separa o que se serve do que se conforma.
evidence:
- E-ANCORA-202601
responsibility: Servir dim_especie e dim_termo lidas da Silver.
consumes:
- especie da bronze
produces: &id001
- referencia na gold
owner: medalhao
independent_proof: Multiconjunto do commit igual à Silver lida.
decision_ids:
- DEC-REFERENCIA-PELO-MEDALHAO
rejected_alternatives:
- alternative: Especie gravada direto na Silver a partir do YAML
  reason: pula landing e Bronze; os bytes da fonte nunca entram no lago.
swimlane:
  id: LANE-GOLD-REFERENCIA
  name: Referência na Gold lane
  owner: medalhao
  legs:
  - id: LEG-GOLD-REFERENCIA
    observable_state: Referência na Gold
    proof: Multiconjunto do commit igual à Silver lida.
    requires:
    - especie da bronze
    produces: *id001
    tasks:
    - id: T-20260924-gold-referencia
      title: A referência na Gold, lida da Silver
      goal: 'Completar o medalhão da referência: a Gold serve a espécie e o termo conformados, lidos da
        Silver — é dela que o consumo (Postgres, BI, agentes) passa a ler. Para rodar testes, o ÚNICO
        comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3
        -m pytest <arquivo> -k <cenarios>`.'
      done_condition: src/medalhao/gold_referencia.py publica dim_especie e dim_termo na Gold a partir
        da Silver, com a linhagem; os testes de tests/test_gold_referencia.py passam.
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
      - T-20260924-especie-da-bronze
      touches_paths: []
      creates_paths:
      - src/medalhao/gold_referencia.py
      - tests/test_gold_referencia.py
      behavior:
      - id: B-1
        given: a Silver especie (publicada da Bronze) e a Silver glossario, em tmp_path
        when: gold_referencia.publicar(spark, silver_especie, silver_glossario, destino, competencia,
          sha256_glossario) roda
        then: 'lê as duas tabelas Silver cada uma numa versão fixada no início e publica em Delta, padrão
          s3a://gold/pda/referencia: dim_especie — codigo, nome_oficial, grupo, descricao_fonte, texto_fonte_confere_prefixo,
          competencia, uma linha por código — com replaceWhere da COMPETÊNCIA, que deixa as outras intactas;
          e dim_termo — termo, descricao, sha256_arquivo — só do sha256_glossario pedido, SELECIONADO
          na Silver antes de publicar, com replaceWhere de sha256_arquivo, que deixa as outras versões
          do glossário intactas; nunca append, nunca overwrite da tabela inteira; cada commit leva as
          versões das tabelas Silver lidas e o id_execucao; relê o próprio commit e confere o multiconjunto
          contra a seleção da Silver lida.'
      - id: B-2
        given: uma Silver especie vazia na competência, ou divergente da releitura
        when: gold_referencia.publicar roda
        then: Silver especie vazia na competência, OU sha256_glossario ausente na Silver glossario lida,
          devolvem NAO_MEDIDO ANTES de qualquer gravação — uma seleção vazia nunca chega ao replaceWhere,
          que apagaria a partição existente; reconferência divergente devolve DIVERGE. As duas dimensões
          são publicações INDEPENDENTES, cada uma com o seu estado no resultado; o consumo só as lê juntas
          se as duas estiverem INTEGRO. O módulo lê só a Silver — um teste confere pelo AST que ele não
          referencia bronze, landing nem _raw. Nenhum cenário usa skip, xfail ou importorskip; os testes
          GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde o cenário
          pede, e MinIO indisponível FALHA o teste; a sessão Spark do teste é uma fixture de módulo ou
          sessão, e nenhuma função a para.
      evals:
      - id: eval_1
        description: A Gold serve o que a Silver conformou
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in dim_especie_da_silver
          dim_termo_da_silver linhagem_das_tabelas_silver; do python3 -m pytest --collect-only -q tests/test_gold_referencia.py
          -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
          -m pytest -q tests/test_gold_referencia.py -k "dim_especie_da_silver or dim_termo_da_silver
          or linhagem_das_tabelas_silver"'
        verifies:
        - B-1
      - id: eval_2
        description: Reconferência e outra competência
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reconfere_o_proprio_commit
          outra_competencia_intacta outra_versao_do_glossario_intacta; do python3 -m pytest --collect-only
          -q tests/test_gold_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
          exit 1; }; done; python3 -m pytest -q tests/test_gold_referencia.py -k "reconfere_o_proprio_commit
          or outra_competencia_intacta or outra_versao_do_glossario_intacta"'
        verifies:
        - B-1
      - id: eval_3
        description: Recusas e só a Silver
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in silver_vazia_nao_medido
          glossario_ausente_nao_apaga_particao dimensoes_independentes modulo_le_so_a_silver; do python3
          -m pytest --collect-only -q tests/test_gold_referencia.py -k "$c" 2>/dev/null | grep -q "::"
          || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_referencia.py
          -k "silver_vazia_nao_medido or glossario_ausente_nao_apaga_particao or dimensoes_independentes
          or modulo_le_so_a_silver"'
        verifies:
        - B-2
      anti_patterns:
      - action: ler a Bronze, o landing, o YAML ou _raw na Gold
        reason: a Gold lê a Silver
        instead: as duas tabelas Silver
      - action: recalcular o nome ou o grupo na Gold
        reason: a Silver conforma, a Gold serve
        instead: servir o que a Silver conformou
      - action: sobrescrever outra competência
        reason: competências são disjuntas (ADR 0011)
        instead: replaceWhere da competência
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
      - src/medalhao/especie.py
      - tests/test_especie.py
      rollback: Remover os dois arquivos criados.
      observability: Gold de referência divergente da Silver
---
# Referência na Gold

Separa o que se serve do que se conforma.

## Responsibility

Servir dim_especie e dim_termo lidas da Silver.

## Independent proof

Multiconjunto do commit igual à Silver lida.

## Rejected alternatives

- **Especie gravada direto na Silver a partir do YAML** — pula landing e Bronze; os bytes da fonte nunca entram no lago.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
