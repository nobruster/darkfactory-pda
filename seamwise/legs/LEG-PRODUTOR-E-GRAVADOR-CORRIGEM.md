---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-PRODUTOR-E-GRAVADOR-CORRIGEM
seam_id: SEAM-PRODUTOR-E-GRAVADOR-CORRIGEM
swimlane_id: LANE-PRODUTOR-E-GRAVADOR-CORRIGEM
observable_state: Produtor e gravador corrigidos
proof: Produtor sobre o CSV real de 2026-01 dá a âncora; segunda carga recusada; rejeitos conferem.
requires:
- gramatica do juiz em spark
produces:
- produtor e gravador corrigidos
tasks:
- id: T-20260924-produtor-e-gravador-corrigem
  title: Produtor e gravador com a gramática do juiz, carga única e rejeitos com o texto bruto
  goal: Corrigir no produtor e no gravador, NUMA tarefa só, os defeitos latentes que a adoção fixou em
    teste — juntos porque dividem as fixtures de tests/test_produtor.py. Para rodar testes, o ÚNICO comando
    liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo>
    -k <cenarios>`.
  done_condition: src/produtor/spark_produtor.py e src/produtor/gravar_lago.py usam a gramática do juiz,
    declaram ANSI, recusam espécie fora do padrão e valor fora da precisão; o gravador recusa partição
    ou rejeitos já ocupados e grava os rejeitos com o texto bruto fora da tabela; só o que B-2 nomeia
    muda em tests/test_produtor.py; todos passam.
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
  - T-20260924-gramatica-do-juiz
  touches_paths:
  - src/produtor/spark_produtor.py
  - src/produtor/gravar_lago.py
  - tests/test_produtor.py
  creates_paths: []
  behavior:
  - id: B-1
    given: o CSV de fixture, e um destino e um diretório de rejeitos em tmp_path
    when: produzir e o main do gravador rodam, cada um num processo filho sem S3_*
    then: 'os dois convertem o valor por gramatica.valor_decimal e validam a espécie por gramatica.especie_valida
      — as regexes locais saem dos dois arquivos —, e as duas sessões declaram spark.sql.ansi.enabled=true;
      ''1,5'' entra como 1.50 e ''-5,00'' conta em linhas_invalidas; QUALQUER linha de espécie inválida
      recusa o arquivo — produzir levanta ProdutorRecusado(''ESPECIE_FORA_DO_PADRAO'', contagem) e o main
      do produtor imprime PRODUTOR=RECUSADO sem escrever envelope; o gravador imprime LAGO=RECUSADO sem
      gravar nada; valor que casa com a gramática mas não cabe na precisão do contrato recusa o arquivo
      nos dois com o motivo VALOR_FORA_DA_PRECISAO. O gravador, ANTES de gravar, recusa com LAGO=RECUSADO
      se a partição competencia=<c> do destino OU a do diretório de rejeitos já tem QUALQUER objeto —
      motivos PARTICAO_JA_CARREGADA e REJEITOS_JA_OCUPADOS; nada é sobrescrito nem apagado, e a retomada
      depois de uma tentativa que falhou é decisão do dono. Premissa declarada: um escritor por competência;
      se outra carga entrar entre a conferência e a escrita, a releitura acusa LAGO=DIVERGE. A TABELA
      continua como hoje: TODAS as linhas do CSV, a de valor inválido com vl_liquido NULL — os rejeitos
      são uma CÓPIA a mais, não uma segregação, para o vinculador e a Bronze seguirem vendo a contagem
      inteira. Grava primeiro os rejeitos — as linhas de valor inválido, em Parquet, com as colunas brutas
      do CSV COMO VIERAM e o motivo VALOR_FORA_DA_GRAMATICA — e depois a tabela; relê os dois, e a contagem
      de rejeitos relida tem de ser igual a linhas_invalidas, senão LAGO=DIVERGE; sem linha inválida,
      nenhum rejeito é criado. --rejeitos tem padrão s3a://landing/pda/beneficios-emitidos-rejeitos, FORA
      do diretório da tabela, para a Bronze não o ler.'
  - id: B-2
    given: o tests/test_produtor.py selado pela adoção, que fixava o comportamento antigo
    when: a tarefa atualiza os testes
    then: 'EXATAMENTE estas mudanças nas funções test_*, e nenhuma outra: SAEM test_gramatica_atual_fixada,
      test_codigo_vazio_fora_do_total_fixado e test_primeira_grava_segunda_diverge_sem_apagar; ENTRAM
      test_gramatica_do_juiz, test_especie_fora_do_padrao_recusa, test_especie_fora_do_padrao_nao_grava,
      test_sessao_do_produtor_ansi, test_valor_fora_da_precisao_recusa, test_segunda_carga_recusada_sem_gravar
      (a primeira dá LAGO=GRAVADO, a segunda LAGO=RECUSADO, e os objetos da primeira ficam os mesmos em
      nome e quantidade), test_residuo_de_rejeitos_recusa, test_rejeitos_guardam_o_texto_bruto, test_rejeitos_fora_da_tabela
      e test_contagem_de_rejeitos_reconferida; MUDAM só os valores esperados de test_produtor_totais_literais_da_fixture,
      test_codigos_com_mesma_descricao_somam_separados e test_cada_controle_divergente_acusa, recalculados
      à mão pela gramática nova — neste último pode mudar também QUAL linha cada mutação altera, para
      uma linha VÁLIDA pela gramática nova, mantendo a asserção de que só o controle alterado diverge
      (a linha ''-5,00'' agora é inválida, e alterá-la mudaria três controles de uma vez). As funções
      que não são test_* — LINHAS, ESPERADO, ESPERADO_POR_CODIGO, a âncora da fixture contratos, _rodar_main
      (que passa a mandar --rejeitos em tmp_path) e _Leitor (que passa a substituir só a releitura da
      tabela, não a dos rejeitos) — mudam só para isso; a linha de espécie vazia sai da fixture principal
      para uma fixture própria. Os demais test_* ficam como estão e passam. Nenhum cenário usa skip, xfail
      ou importorskip.'
  evals:
  - id: eval_1
    description: A gramática do juiz nos dois
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gramatica_do_juiz produtor_totais_literais_da_fixture
      codigos_com_mesma_descricao_somam_separados especie_fora_do_padrao_recusa sessao_do_produtor_ansi
      valor_fora_da_precisao_recusa; do python3 -m pytest --collect-only -q tests/test_produtor.py -k
      "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m
      pytest -q tests/test_produtor.py -k "gramatica_do_juiz or produtor_totais_literais_da_fixture or
      codigos_com_mesma_descricao_somam_separados or especie_fora_do_padrao_recusa or sessao_do_produtor_ansi
      or valor_fora_da_precisao_recusa"'
    verifies:
    - B-1
    - B-2
  - id: eval_2
    description: Carga única e rejeitos
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in segunda_carga_recusada_sem_gravar
      residuo_de_rejeitos_recusa rejeitos_guardam_o_texto_bruto rejeitos_fora_da_tabela contagem_de_rejeitos_reconferida
      especie_fora_do_padrao_nao_grava; do python3 -m pytest --collect-only -q tests/test_produtor.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_produtor.py -k "segunda_carga_recusada_sem_gravar or residuo_de_rejeitos_recusa
      or rejeitos_guardam_o_texto_bruto or rejeitos_fora_da_tabela or contagem_de_rejeitos_reconferida
      or especie_fora_do_padrao_nao_grava"'
    verifies:
    - B-1
    - B-2
  - id: eval_3
    description: O resto igual, os dois medindo igual
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gravador_mede_igual_ao_produtor
      cada_controle_divergente_acusa destino_padrao_e_o_landing_de_hoje filho_sem_credencial_s3 produzir_e_main_so_em_processo_filho
      envelope_sem_float; do python3 -m pytest --collect-only -q tests/test_produtor.py -k "$c" 2>/dev/null
      | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_produtor.py
      -k "gravador_mede_igual_ao_produtor or cada_controle_divergente_acusa or destino_padrao_e_o_landing_de_hoje
      or filho_sem_credencial_s3 or produzir_e_main_so_em_processo_filho or envelope_sem_float"'
    verifies:
    - B-2
  anti_patterns:
  - action: apagar ou sobrescrever a partição ou os rejeitos já existentes para gravar de novo
    reason: destrói a carga anterior, que é evidência
    instead: recusar sem gravar
  - action: gravar os rejeitos dentro do diretório da tabela
    reason: a Bronze leria os rejeitos como dado
    instead: o prefixo -rejeitos, irmão da tabela
  - action: editar um test_* fora da lista nomeada em B-2
    reason: a exceção à regra do teste selado é nomeada
    instead: só o que B-2 lista
  do_not_touch:
  - _raw
  - contracts
  - cvg/docs/adrs
  - src/pda
  - src/medalhao
  - src/ontologia
  - infra
  - src/produtor/gramatica.py
  - tests/test_gramatica.py
  - src/produtor/vincular_procedencia.py
  - tests/test_vincular_procedencia.py
  rollback: Reverter src/produtor/spark_produtor.py, src/produtor/gravar_lago.py e tests/test_produtor.py
    ao commit anterior.
  observability: arquivos recusados por espécie, precisão ou partição ocupada
source_seam_sha256: c511062ad5e1f8f7382013b23c1de66b8a09eca0c806dff5b4e3b217df927d2d
---
# Produtor e gravador corrigidos

## Observable proof

Produtor sobre o CSV real de 2026-01 dá a âncora; segunda carga recusada; rejeitos conferem.

## Runnable leaves

- `T-20260924-produtor-e-gravador-corrigem` — Produtor e gravador com a gramática do juiz, carga única e rejeitos com o texto bruto: src/produtor/spark_produtor.py e src/produtor/gravar_lago.py usam a gramática do juiz, declaram ANSI, recusam espécie fora do padrão e valor fora da precisão; o gravador recusa partição ou rejeitos já ocupados e grava os rejeitos com o texto bruto fora da tabela; só o que B-2 nomeia muda em tests/test_produtor.py; todos passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
