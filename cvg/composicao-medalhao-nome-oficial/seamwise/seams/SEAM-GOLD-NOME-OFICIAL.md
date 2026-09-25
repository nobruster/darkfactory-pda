---
schema_version: 1
kind: seam
claim: derived
id: SEAM-GOLD-NOME-OFICIAL
name: Gold com nome oficial
description: Separa o nome oficial do texto truncado na Gold.
evidence:
- E-ANCORA-202601
responsibility: Juntar o nome da Silver especie depois da agregação.
consumes:
- especie na silver
produces: &id001
- gold com nome oficial
owner: medalhao
independent_proof: Controles idênticos com e sem o nome.
decision_ids:
- DEC-NOME-OFICIAL-NA-GOLD
rejected_alternatives:
- alternative: Tabelas novas ao lado das atuais
  reason: o dono escolheu evoluir as tabelas atuais (2026-09-25).
swimlane:
  id: LANE-GOLD-NOME-OFICIAL
  name: Gold com nome oficial lane
  owner: medalhao
  legs:
  - id: LEG-GOLD-NOME-OFICIAL
    observable_state: Gold com nome oficial
    proof: Controles idênticos com e sem o nome.
    requires: []
    produces: *id001
    tasks:
    - id: T-20260925-gold-nome-oficial
      title: A Gold principal ganha o nome oficial, lido da Silver especie
      goal: Pôr o nome oficial da espécie na Gold principal, ligado pelo código, sem mudar nenhum controle
        e sem quebrar os testes selados que montam a Gold sem a especie. Para rodar testes, o ÚNICO comando
        liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest
        <arquivo> -k <cenarios>`.
      done_condition: GOLD_COLUNAS termina em nome_oficial; com o caminho da Silver especie a Gold publica
        o nome, sem ele publica nulo com o motivo no commit; em tests/test_gold.py muda só a tupla literal
        de test_commit_carrega_a_forma; os testes de tests/test_gold_nome_oficial.py e os existentes passam.
      effort: M
      profile: standard
      execution_backend: any
      required_tools:
      - git
      - bash
      - python3
      - pytest
      - docker
      depends_on: []
      touches_paths:
      - src/medalhao/gold.py
      - tests/test_gold.py
      creates_paths:
      - tests/test_gold_nome_oficial.py
      behavior:
      - id: B-1
        given: uma Silver de benefícios e uma Silver especie da mesma competência, em tmp_path
        when: executar_gold_da_silver, executar_gold e agregar rodam com o parâmetro novo especie_destino
          (Optional[str], padrão None) apontando para a Silver especie
        then: 'GOLD_COLUNAS passa a ser (especie_codigo, especie_descricao, vl_liquido_total, competencia,
          nome_oficial) — a coluna nova no FIM, onde a evolução de schema a põe; a Silver especie é lida
          numa versão V fixada UMA vez (versionAsOf), filtrada pela competência, e juntada DEPOIS do groupBy
          por especie_codigo, em left join — a contagem, a soma, o mínimo, o máximo e o total_por_codigo
          saem IDÊNTICOS aos de sem o nome; um código da Gold sem linha na especie devolve DIVERGE com
          a diferença NOME_OFICIAL_AUSENTE e nada é publicado (Regra 9: nunca nulo calado com a especie
          presente); o commit registra silver_especie = {caminho: especie_destino, versao: V} — o CAMINHO
          e a versão, porque o número da versão sozinho não identifica a tabela; _garantir_tabela declara
          nome_oficial como texto ANULÁVEL, sem CHECK; a reconferência, COM especie_destino, compara as
          5 colunas, nome_oficial incluído, como multiconjunto — um nome perdido ou trocado diverge; SÓ
          sem especie_destino _conferir_tabela compara pelas colunas do esperado, para os testes existentes
          que montam o esperado com 4 colunas seguirem valendo. Numa tabela Gold já publicada com 4 colunas,
          a publicação com evolucao_aditiva=True acrescenta nome_oficial e deixa as outras competências
          intactas, com nome nulo.'
      - id: B-2
        given: a Gold chamada SEM especie_destino, como nos testes selados existentes
        when: a Gold é publicada
        then: 'nome_oficial é nulo em toda linha — e a reconferência CONFERE que é nulo em toda linha
          do publicado, mesmo comparando as outras colunas pelo esperado —, e o commit registra nome_oficial:
          ''NAO_MEDIDO'' com o motivo ''SEM_SILVER_ESPECIE'' — nunca uma ausência calada; todos os controles
          saem como antes. Em tests/test_gold.py a ÚNICA mudança é acrescentar "nome_oficial" ao FIM da
          tupla literal de test_commit_carrega_a_forma; nenhum outro test_* muda nem sai. Em tests/test_gold_nome_oficial.py
          entram test_nome_oficial_vem_da_silver_especie, test_controles_iguais_com_e_sem_nome, test_codigo_sem_nome_diverge_e_nao_publica,
          test_sem_especie_nome_nulo_e_registrado, test_commit_nomeia_a_versao_da_especie, test_especie_lida_na_versao_fixada,
          test_reconferencia_acusa_nome_trocado e test_tabela_de_quatro_colunas_evolui_aditiva. Nenhum
          cenário usa skip, xfail ou importorskip; os testes gravam só em tmp_path, nunca no MinIO; a
          Silver especie de fixture é uma tabela Delta em tmp_path com o schema de medalhao.especie.'
      evals:
      - id: eval_1
        description: O nome vem da Silver especie e os controles não mudam
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in nome_oficial_vem_da_silver_especie
          controles_iguais_com_e_sem_nome commit_nomeia_a_versao_da_especie especie_lida_na_versao_fixada;
          do python3 -m pytest --collect-only -q tests/test_gold_nome_oficial.py -k "$c" 2>/dev/null |
          grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_nome_oficial.py
          -k "nome_oficial_vem_da_silver_especie or controles_iguais_com_e_sem_nome or commit_nomeia_a_versao_da_especie
          or especie_lida_na_versao_fixada"'
        verifies:
        - B-1
      - id: eval_2
        description: Ausência não é silêncio, e a tabela evolui
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in codigo_sem_nome_diverge_e_nao_publica
          sem_especie_nome_nulo_e_registrado reconferencia_acusa_nome_trocado tabela_de_quatro_colunas_evolui_aditiva;
          do python3 -m pytest --collect-only -q tests/test_gold_nome_oficial.py -k "$c" 2>/dev/null |
          grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_nome_oficial.py
          -k "codigo_sem_nome_diverge_e_nao_publica or sem_especie_nome_nulo_e_registrado or reconferencia_acusa_nome_trocado
          or tabela_de_quatro_colunas_evolui_aditiva"'
        verifies:
        - B-1
        - B-2
      - id: eval_3
        description: A Gold existente segue igual
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in commit_carrega_a_forma
          reconfere_multiconjunto_das_linhas publica_em_um_unico_commit; do python3 -m pytest --collect-only
          -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
          exit 1; }; done; python3 -m pytest -q tests/test_gold.py -k "commit_carrega_a_forma or reconfere_multiconjunto_das_linhas
          or publica_em_um_unico_commit"'
        verifies:
        - B-2
      anti_patterns:
      - action: juntar a especie ANTES do groupBy
        reason: multiplicaria linhas e mudaria os controles
        instead: left join depois da agregação por código
      - action: tornar especie_destino obrigatório
        reason: quebraria ~25 testes selados que montam a Gold sem ela
        instead: opcional, com o motivo registrado quando ausente
      - action: editar outro teste existente além da tupla de test_commit_carrega_a_forma
        reason: a exceção à regra do teste selado é nomeada
        instead: testes novos no arquivo novo
      do_not_touch:
      - _raw
      - contracts
      - cvg/docs/adrs
      - src/pda
      - src/ontologia
      - infra
      - src/produtor
      - src/medalhao/especie.py
      - src/medalhao/bronze.py
      - src/medalhao/silver.py
      - tests/test_gold_assuntos.py
      - tests/test_performance_gold.py
      - src/medalhao/gold_assuntos.py
      rollback: Reverter src/medalhao/gold.py e tests/test_gold.py; remover tests/test_gold_nome_oficial.py.
      observability: Gold publicada sem nome oficial
---
# Gold com nome oficial

Separa o nome oficial do texto truncado na Gold.

## Responsibility

Juntar o nome da Silver especie depois da agregação.

## Independent proof

Controles idênticos com e sem o nome.

## Rejected alternatives

- **Tabelas novas ao lado das atuais** — o dono escolheu evoluir as tabelas atuais (2026-09-25).

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
