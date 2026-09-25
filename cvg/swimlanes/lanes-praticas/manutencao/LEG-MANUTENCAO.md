> Projetado de `LEG-MANUTENCAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `35617a8f1bcf51df16d25156acc28d50a0159e480beb61342969f70f2381a205`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-MANUTENCAO
seam_id: SEAM-MANUTENCAO
swimlane_id: LANE-MANUTENCAO
observable_state: Manutenção de retenção e OPTIMIZE
proof: Multiconjunto igual antes e depois do OPTIMIZE.
requires:
- assuntos evoluem
produces:
- lago mantido
tasks:
- id: T-20260925-manutencao-retencao-e-optimize
  title: 'Manutenção: retenção nas tabelas publicadas e OPTIMIZE com prova'
  goal: Dar às tabelas já publicadas a retenção de 5 anos e compactar ao fim de cada carga, provando que
    o dado não muda. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml
    exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.
  done_condition: src/medalhao/manutencao.py tem garantir_retencao e otimizar; scripts/manter_lago.py
    aplica os dois numa lista fechada de tabelas; os testes de tests/test_manutencao.py passam.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  depends_on:
  - T-20260925-assuntos-evoluem-por-padrao
  touches_paths: []
  creates_paths:
  - src/medalhao/manutencao.py
  - tests/test_manutencao.py
  - scripts/manter_lago.py
  behavior:
  - id: B-1
    given: tabelas Delta em tmp_path, com e sem as propriedades de retenção
    when: manutencao.garantir_retencao(spark, caminho) e manutencao.otimizar(spark, caminho) rodam
    then: 'garantir_retencao trata CADA uma das duas propriedades (delta.logRetentionDuration e delta.deletedFileRetentionDuration)
      assim, e nunca encurta: AUSENTE → ''interval 1825 days''; PRESENTE e MENOR que 1825 dias → sobe
      para ''interval 1825 days''; PRESENTE e MAIOR OU IGUAL a 1825 dias → fica como está; valor em formato
      que não se lê como ''interval N days'' → nada é alterado e o resultado é NAO_MEDIDO nomeando a propriedade.
      Sem nada a mudar, devolve JA_TINHA e não cria commit; com mudança, aplica numa ÚNICA ALTER TABLE
      SET TBLPROPERTIES e devolve ALTERADA (estava ausente) ou CORRIGIDA (estava menor), sempre com os
      valores ANTERIORES no resultado. otimizar resolve a versão atual V, roda OPTIMIZE (executeCompaction)
      e lê o histórico depois de V: se não há commit novo, devolve SEM_MUDANCA; se há exatamente UM commit
      novo e a operação dele é OPTIMIZE, esse é W, e prova que o dado não mudou comparando o multiconjunto
      de V e de W nos dois sentidos — o Delta 3.2.1 NÃO grava contagem de linhas no commit do OPTIMIZE
      (medido: só numAddedFiles, numRemovedFiles, bytes e tamanhos), então a prova é o multiconjunto,
      e as métricas de arquivo só são relatadas —; igual → OTIMIZADA; diferente → DIVERGE, sem esconder;
      se entre V e o fim houver commit que não seja o próprio OPTIMIZE, devolve NAO_MEDIDO (escrita concorrente),
      nunca DIVERGE. O módulo NÃO tem VACUUM — só sob pedido do dono (ADR 0017). scripts/manter_lago.py
      aplica os dois a esta LISTA FECHADA, literal no script, das 11 tabelas Delta do lago: s3a://bronze/pda/beneficios-emitidos,
      s3a://bronze/pda/referencia/dicionario_especies, s3a://bronze/pda/referencia/glossario, s3a://silver/pda/beneficios-emitidos,
      s3a://silver/pda/especie, s3a://silver/pda/glossario, s3a://gold/pda/beneficios-emitidos, s3a://gold/pda/assuntos/fat_especie,
      s3a://gold/pda/assuntos/kpis_nacionais, s3a://gold/pda/referencia/dim_especie e s3a://gold/pda/referencia/dim_termo;
      por padrão só MEDE (diz o que faria, sem commit) e só altera com --aplicar, um token por tabela.
      Quem o chama ao fim de cada carga é o procedimento de publicação do dono (regra operacional do ADR
      0017).'
  - id: B-2
    given: uma tabela Delta em tmp_path e o script
    when: os testes rodam
    then: 'entram em tests/test_manutencao.py test_retencao_aplicada_em_tabela_sem, test_retencao_ja_presente_sem_commit,
      test_retencao_divergente_corrigida_e_registrada, test_retencao_parcial_completada, test_retencao_maior_nunca_encurta,
      test_retencao_ilegivel_nao_medido, test_optimize_com_escrita_concorrente_nao_medido, test_optimize_nao_muda_o_dado,
      test_optimize_sem_nada_a_compactar, test_optimize_acusa_dado_mudado (a leitura da versão nova é
      substituída por uma com uma linha a mais), test_modulo_sem_vacuum (AST: nenhuma chamada vacuum)
      e test_script_mede_por_padrao_e_lista_e_fechada (o script sem --aplicar não cria commit; a lista
      é literal). Nenhum cenário usa skip, xfail ou importorskip; os testes gravam só em tmp_path, nunca
      no MinIO; nenhuma função para a sessão Spark da suíte.'
  evals:
  - id: eval_1
    description: Retenção sem commit à toa
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in retencao_aplicada_em_tabela_sem
      retencao_ja_presente_sem_commit retencao_divergente_corrigida_e_registrada retencao_parcial_completada
      retencao_maior_nunca_encurta retencao_ilegivel_nao_medido; do python3 -m pytest --collect-only -q
      tests/test_manutencao.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_manutencao.py -k "retencao_aplicada_em_tabela_sem
      or retencao_ja_presente_sem_commit or retencao_divergente_corrigida_e_registrada or retencao_parcial_completada
      or retencao_maior_nunca_encurta or retencao_ilegivel_nao_medido"'
    verifies:
    - B-1
  - id: eval_2
    description: OPTIMIZE com prova
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in optimize_nao_muda_o_dado
      optimize_sem_nada_a_compactar optimize_acusa_dado_mudado optimize_com_escrita_concorrente_nao_medido;
      do python3 -m pytest --collect-only -q tests/test_manutencao.py -k "$c" 2>/dev/null | grep -q "::"
      || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_manutencao.py
      -k "optimize_nao_muda_o_dado or optimize_sem_nada_a_compactar or optimize_acusa_dado_mudado or optimize_com_escrita_concorrente_nao_medido"'
    verifies:
    - B-1
  - id: eval_3
    description: Sem VACUUM, script que mede por padrão
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in modulo_sem_vacuum script_mede_por_padrao_e_lista_e_fechada;
      do python3 -m pytest --collect-only -q tests/test_manutencao.py -k "$c" 2>/dev/null | grep -q "::"
      || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_manutencao.py
      -k "modulo_sem_vacuum or script_mede_por_padrao_e_lista_e_fechada"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: incluir VACUUM
    reason: só sob pedido do dono (ADR 0017)
    instead: OPTIMIZE e retenção
  - action: chamar OPTIMIZE dentro de publicar
    reason: testes conferem a versão exata depois de publicar
    instead: manutenção separada, pós-carga
  - action: lista de tabelas por varredura do bucket
    reason: tocaria o que ninguém nomeou
    instead: lista fechada
  do_not_touch:
  - _raw
  - contracts
  - cvg/docs/adrs
  - src/pda
  - src/ontologia
  - src/produtor
  - infra
  - tests/test_gold.py
  - tests/test_gold_assuntos.py
  - tests/test_testes_leves.py
  - src/medalhao/bronze.py
  - src/medalhao/silver.py
  - src/medalhao/ingestao.py
  - src/medalhao/gold.py
  - src/medalhao/gold_assuntos.py
  - tests/test_gold_nome_oficial.py
  - tests/test_assuntos_nome_oficial.py
  - tests/test_delta_padroes.py
  - tests/test_delta_padroes_silver.py
  rollback: Reverter os caminhos tocados e remover os criados.
  observability: tabelas sem retenção declarada
source_seam_sha256: 72c3d45641dff2422f57a50ae07891d3f37c1312bf93926e3f06a4882cce1374
---
# Manutenção de retenção e OPTIMIZE

## Observable proof

Multiconjunto igual antes e depois do OPTIMIZE.

## Runnable leaves

- `T-20260925-manutencao-retencao-e-optimize` — Manutenção: retenção nas tabelas publicadas e OPTIMIZE com prova: src/medalhao/manutencao.py tem garantir_retencao e otimizar; scripts/manter_lago.py aplica os dois numa lista fechada de tabelas; os testes de tests/test_manutencao.py passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
