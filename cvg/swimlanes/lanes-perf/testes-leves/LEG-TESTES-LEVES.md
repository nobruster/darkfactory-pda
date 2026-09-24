> Projetado de `LEG-TESTES-LEVES.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `ec85f01dd904e8d7065877821d07742ca5b98a1cc78c30c5066557c05a61524e`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-TESTES-LEVES
seam_id: SEAM-TESTES-LEVES
swimlane_id: LANE-TESTES-LEVES
observable_state: Suíte de assuntos e gold mais rápida com os mesmos testes
proof: Mesmos ids coletados, nenhuma linha dentro de test_* mudou, todos verdes.
requires:
- gold performatica
produces:
- testes leves
tasks:
- id: T-20260924-testes-leves
  title: Cenário de teste montado uma vez por módulo
  goal: Tirar dos testes a montagem da cadeia real a cada teste.
  done_condition: Os mesmos ids de teste de tests/test_gold.py e tests/test_gold_assuntos.py são coletados,
    nenhuma linha dentro de uma função test_* mudou, todos passam, e test_gold_assuntos leva menos da
    metade dos 551s medidos.
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
  - T-20260924-perf-gold
  touches_paths:
  - tests/test_gold.py
  - tests/test_gold_assuntos.py
  creates_paths:
  - tests/test_testes_leves.py
  behavior:
  - id: B-1
    given: os auxiliares _cenario, _cadeia_publicada e _preparar, que montam a cadeia real por teste
    when: os testes rodam
    then: a cadeia do cenário é montada UMA vez por módulo numa fixture e cada teste recebe uma CÓPIA
      do diretório — tabelas Delta locais com caminhos relativos no _delta_log, contrato e lago de teste
      reescritos para a cópia —, isolando os testes entre si como antes; SÓ os auxiliares e as fixtures
      mudam, e nenhuma linha dentro de uma função test_* é alterada.
  - id: B-2
    given: a suíte depois da mudança
    when: é coletada e executada
    then: coleta EXATAMENTE os mesmos ids de teste de antes, todos passam, nenhum é marcado skip ou xfail,
      e o diff de cada função test_* contra o commit anterior é vazio — verificado por um teste que compara
      o corpo das funções pela AST; test_gold_assuntos leva menos da metade dos 551s medidos.
  evals:
  - id: eval_1
    description: Cenário uma vez, cópia por teste
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_especie_fecha_com_a_ancora
      le_silver_por_versao usa_a_silver_nomeada_pela_gold; do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_gold_assuntos.py -k "fat_especie_fecha_com_a_ancora or le_silver_por_versao
      or usa_a_silver_nomeada_pela_gold"'
    verifies:
    - B-1
  - id: eval_2
    description: Nenhuma asserção mudou
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in mesmos_ids_coletados
      corpo_das_funcoes_test_intacto nenhum_skip_ou_xfail; do python3 -m pytest --collect-only -q tests/test_testes_leves.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_testes_leves.py -k "mesmos_ids_coletados or corpo_das_funcoes_test_intacto
      or nenhum_skip_ou_xfail"'
    verifies:
    - B-2
  - id: eval_3
    description: A Gold continua verde
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_le_so_a_silver
      linhagem_ate_pacote_aceito gold_da_silver_fecha_com_a_ancora; do python3 -m pytest --collect-only
      -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit
      1; }; done; python3 -m pytest -q tests/test_gold.py -k "gold_le_so_a_silver or linhagem_ate_pacote_aceito
      or gold_da_silver_fecha_com_a_ancora"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: editar uma linha dentro de uma função test_*
    reason: muda o que o teste prova
    instead: mudar só auxiliares e fixtures
  - action: marcar teste lento como skip ou xfail
    reason: é afrouxar o gate (Regra 3)
    instead: barateá-lo pela fixture
  - action: compartilhar o MESMO diretório entre testes
    reason: um teste que republica contamina o outro
    instead: uma cópia por teste
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src
  rollback: Reverter os arquivos tocados ao commit assentado; remover os criados.
  observability: execuções com memória herdada ou cache não liberado
source_seam_sha256: 03433f7cba7711d00e96e0917140634d2b26c2bbcb8f6eca8cc715a5a8d34d54
---
# Suíte de assuntos e gold mais rápida com os mesmos testes

## Observable proof

Mesmos ids coletados, nenhuma linha dentro de test_* mudou, todos verdes.

## Runnable leaves

- `T-20260924-testes-leves` — Cenário de teste montado uma vez por módulo: Os mesmos ids de teste de tests/test_gold.py e tests/test_gold_assuntos.py são coletados, nenhuma linha dentro de uma função test_* mudou, todos passam, e test_gold_assuntos leva menos da metade dos 551s medidos.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
