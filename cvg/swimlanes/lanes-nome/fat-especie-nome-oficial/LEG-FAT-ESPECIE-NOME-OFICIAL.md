> Projetado de `LEG-FAT-ESPECIE-NOME-OFICIAL.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `4ca1595dbc10fb8ac6a8dba007bf1d8bcab2051197791380a51f5cc4da464ae9`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-FAT-ESPECIE-NOME-OFICIAL
seam_id: SEAM-FAT-ESPECIE-NOME-OFICIAL
swimlane_id: LANE-FAT-ESPECIE-NOME-OFICIAL
observable_state: Fat especie com nome oficial
proof: Mesma versão da especie nas duas tabelas.
requires:
- gold com nome oficial
produces:
- fat com nome oficial
tasks:
- id: T-20260925-fat-especie-nome-oficial
  title: A fat_especie ganha o nome oficial, da mesma especie que a Gold principal usou
  goal: Pôr o nome oficial na fat_especie lendo a Silver especie na MESMA versão que a Gold principal
    registrou — sem a Gold ler a Gold. Para rodar testes, o ÚNICO comando liberado ao agente é `docker
    compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.
  done_condition: FAT_COLUNAS termina em nome_oficial, lido da especie na versão registrada pela Gold
    principal; os testes de tests/test_assuntos_nome_oficial.py e os existentes de tests/test_gold_assuntos.py
    passam.
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
  - T-20260925-gold-nome-oficial
  touches_paths:
  - src/medalhao/gold_assuntos.py
  creates_paths:
  - tests/test_assuntos_nome_oficial.py
  behavior:
  - id: B-1
    given: uma Gold principal publicada COM especie_destino (commit com a chave silver_especie {caminho,
      versao})
    when: executar_gold_assuntos roda
    then: 'lê silver_especie {caminho, versao} do commit da Gold principal que ele já consulta, lê a Silver
      especie NESSE caminho e NESSA versão (versionAsOf) — nunca um caminho padrão —, filtrada pela competência,
      registra o mesmo {caminho, versao} no commit da fat, e junta nome_oficial por especie_codigo depois
      de montar a fat — montar_fat_especie ganha um parâmetro opcional nomes (DataFrame, padrão None)
      —; FAT_COLUNAS passa a terminar em nome_oficial, no FIM; os controles da fat e dos kpis saem idênticos
      aos de sem o nome; um código sem nome devolve DIVERGE sem publicar; a presença ou ausência da especie
      é decidida SÓ pela chave silver_especie do commit da Gold principal; a reconferência do próprio
      commit da fat compara o multiconjunto COM nome_oficial — um nome trocado diverge —; a tabela da
      fat declara nome_oficial anulável e evolui só de forma aditiva: partindo de uma fat JÁ publicada
      com o schema antigo e outra competência, a publicação acrescenta a coluna e deixa a outra competência
      intacta.'
  - id: B-2
    given: uma Gold principal publicada SEM especie (commit SEM a chave silver_especie)
    when: executar_gold_assuntos roda
    then: 'nome_oficial é nulo e o commit registra nome_oficial: ''NAO_MEDIDO'' com o motivo; nenhum teste
      de tests/test_gold_assuntos.py muda. Em tests/test_assuntos_nome_oficial.py entram test_fat_nome_da_mesma_especie_da_gold,
      test_fat_controles_iguais_com_e_sem_nome, test_fat_codigo_sem_nome_diverge, test_fat_sem_especie_nome_nulo_e_registrado,
      test_fat_nome_oficial_no_fim_das_colunas, test_fat_commit_nomeia_a_especie_lida, test_fat_reconferencia_acusa_nome_trocado
      e test_fat_existente_evolui_e_outra_competencia_intacta. Nenhum cenário usa skip, xfail ou importorskip;
      os testes gravam só em tmp_path, nunca no MinIO; a Silver especie de fixture é uma tabela Delta
      em tmp_path com o schema de medalhao.especie.'
  evals:
  - id: eval_1
    description: O nome da mesma especie
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_nome_da_mesma_especie_da_gold
      fat_controles_iguais_com_e_sem_nome fat_nome_oficial_no_fim_das_colunas fat_commit_nomeia_a_especie_lida;
      do python3 -m pytest --collect-only -q tests/test_assuntos_nome_oficial.py -k "$c" 2>/dev/null |
      grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_assuntos_nome_oficial.py
      -k "fat_nome_da_mesma_especie_da_gold or fat_controles_iguais_com_e_sem_nome or fat_nome_oficial_no_fim_das_colunas
      or fat_commit_nomeia_a_especie_lida"'
    verifies:
    - B-1
  - id: eval_2
    description: Ausência não é silêncio
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_codigo_sem_nome_diverge
      fat_sem_especie_nome_nulo_e_registrado fat_reconferencia_acusa_nome_trocado fat_existente_evolui_e_outra_competencia_intacta;
      do python3 -m pytest --collect-only -q tests/test_assuntos_nome_oficial.py -k "$c" 2>/dev/null |
      grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_assuntos_nome_oficial.py
      -k "fat_codigo_sem_nome_diverge or fat_sem_especie_nome_nulo_e_registrado or fat_reconferencia_acusa_nome_trocado
      or fat_existente_evolui_e_outra_competencia_intacta"'
    verifies:
    - B-1
    - B-2
  - id: eval_3
    description: Os assuntos existentes seguem iguais
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_especie_fecha_com_a_ancora
      commit_nomeia_versoes_lidas publica_com_replacewhere; do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_gold_assuntos.py -k "fat_especie_fecha_com_a_ancora or commit_nomeia_versoes_lidas
      or publica_com_replacewhere"'
    verifies:
    - B-2
  anti_patterns:
  - action: ler o nome da Gold principal
    reason: a Gold lê da Silver
    instead: a Silver especie na versão que a Gold principal registrou
  - action: ler a especie na versão atual
    reason: a fat e a Gold principal poderiam divergir no nome
    instead: a versão registrada no commit da Gold principal
  - action: editar um teste de tests/test_gold_assuntos.py
    reason: acrescentar, não mudar
    instead: arquivo de teste novo
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
  - src/medalhao/gold.py
  - tests/test_gold.py
  rollback: Reverter src/medalhao/gold_assuntos.py; remover tests/test_assuntos_nome_oficial.py.
  observability: fat_especie sem nome oficial
source_seam_sha256: 404af2431105633c842f26b8a78f4874bd279f20dfb31ca6cf3d6f695111733a
---
# Fat especie com nome oficial

## Observable proof

Mesma versão da especie nas duas tabelas.

## Runnable leaves

- `T-20260925-fat-especie-nome-oficial` — A fat_especie ganha o nome oficial, da mesma especie que a Gold principal usou: FAT_COLUNAS termina em nome_oficial, lido da especie na versão registrada pela Gold principal; os testes de tests/test_assuntos_nome_oficial.py e os existentes de tests/test_gold_assuntos.py passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
