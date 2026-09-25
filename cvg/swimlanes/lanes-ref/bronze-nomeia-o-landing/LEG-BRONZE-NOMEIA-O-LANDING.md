> Projetado de `LEG-BRONZE-NOMEIA-O-LANDING.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `cc373ab19aa8ec78b635dc592c7757e13288d1c0e4f1c9cfe15b3d7be0861b9b`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-BRONZE-NOMEIA-O-LANDING
seam_id: SEAM-BRONZE-NOMEIA-O-LANDING
swimlane_id: LANE-BRONZE-NOMEIA-O-LANDING
observable_state: Bronze nomeia o landing
proof: Commit com partição, manifesto e prova conferidos.
requires: []
produces:
- bronze com linhagem do landing
tasks:
- id: T-20260924-bronze-nomeia-o-landing
  title: A Bronze registra qual partição do landing leu
  goal: 'Fechar a linhagem de ponta a ponta: hoje a Silver, a Gold e a especie registram a versão da camada
    anterior, e a Bronze registra só o hash do CSV, não o que leu do landing. Para rodar testes, o ÚNICO
    comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m
    pytest <arquivo> -k <cenarios>`.'
  done_condition: O commit da Bronze traz a partição do landing lida, o manifesto dos objetos e o sha256
    da prova; os testes existentes de tests/test_bronze.py passam sem edição; os novos passam.
  effort: S
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
  - src/medalhao/bronze.py
  - tests/test_bronze.py
  creates_paths: []
  behavior:
  - id: B-1
    given: uma partição do landing com objetos Parquet e _PROCEDENCIA.json, em tmp_path
    when: a Bronze lê, confere e publica a competência
    then: 'os metadados do commit ganham a chave ''landing'' com: ''particao'' (o caminho EXATO da partição
      lida), ''objetos'' (nome, tamanho e sha256 dos bytes de cada objeto de dado lido, em ordem de nome
      — o sha256 porque nome e tamanho não provam que o objeto não foi trocado), ''sha256_manifesto''
      (sha256 do JSON canônico — chaves ordenadas, sem espaços — da lista ''objetos'') e ''sha256_prova''
      (sha256 dos BYTES da _PROCEDENCIA.json da partição). A listagem e os bytes da prova são capturados
      ANTES da leitura dos dados e reconferidos antes do commit — se a partição mudou no meio, a Bronze
      devolve DIVERGE sem publicar. A Bronze LÊ os bytes da prova para o hash nos DOIS caminhos — com
      procedencia= passada pelo chamador (o de produção: ingestao e gold passam) e sem ela —; sem _PROCEDENCIA.json
      na partição, ''sha256_prova'' é null e ''prova_ausente'' é true, nunca um valor inventado. Pode
      acrescentar campo com default em BronzeConferido e guardar os bytes em _ler_prova, tudo em bronze.py.
      Nenhuma chave que já existia muda de nome ou de valor, e os DADOS publicados são os mesmos, linha
      a linha.'
  - id: B-2
    given: o tests/test_bronze.py selado
    when: a tarefa acrescenta os testes
    then: todos os test_* existentes ficam como estão e passam; entram só test_commit_nomeia_a_particao_do_landing,
      test_manifesto_do_commit_confere_com_os_objetos, test_prova_do_commit_e_a_lida — este lê os bytes
      da _PROCEDENCIA.json e compara o sha256 — e test_prova_lida_tambem_com_procedencia_passada e test_particao_mudou_no_meio_diverge;
      os testes novos usam a fixture spark que o arquivo já tem. Nenhum cenário usa skip, xfail ou importorskip;
      os testes GRAVAM só em tmp_path, nunca no MinIO — LER o MinIO ou /dados/_raw é permitido onde o
      cenário pede, e MinIO indisponível FALHA o teste; a sessão Spark do teste é uma fixture de módulo
      ou sessão, e nenhuma função a para.
  evals:
  - id: eval_1
    description: A partição e o manifesto no commit
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in commit_nomeia_a_particao_do_landing
      manifesto_do_commit_confere_com_os_objetos prova_do_commit_e_a_lida prova_lida_tambem_com_procedencia_passada
      particao_mudou_no_meio_diverge; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c"
      2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest
      -q tests/test_bronze.py -k "commit_nomeia_a_particao_do_landing or manifesto_do_commit_confere_com_os_objetos
      or prova_do_commit_e_a_lida or prova_lida_tambem_com_procedencia_passada or particao_mudou_no_meio_diverge"'
    verifies:
    - B-1
  - id: eval_2
    description: O commit dono da competência segue igual
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in metadados_do_commit_dono_da_competencia
      commit_carrega_a_forma replacewhere_nao_toca_outra_competencia; do python3 -m pytest --collect-only
      -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "metadados_do_commit_dono_da_competencia
      or commit_carrega_a_forma or replacewhere_nao_toca_outra_competencia"'
    verifies:
    - B-2
  - id: eval_3
    description: A procedência e o resto da Bronze iguais
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in manifesto_confere_objetos_listados
      procedencia_confere_tira_a_marca classificacao_das_seis; do python3 -m pytest --collect-only -q
      tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit
      1; }; done; python3 -m pytest -q tests/test_bronze.py -k "manifesto_confere_objetos_listados or
      procedencia_confere_tira_a_marca or classificacao_das_seis"'
    verifies:
    - B-2
  anti_patterns:
  - action: trocar ou renomear uma chave existente dos metadados
    reason: Silver, Gold e ingestão leem esses metadados
    instead: só acrescentar a chave 'landing'
  - action: registrar o caminho da raiz do landing em vez da partição
    reason: não diz o que foi lido
    instead: a partição exata
  - action: editar um teste existente
    reason: a tarefa só acrescenta
    instead: testes novos
  do_not_touch:
  - _raw
  - contracts
  - cvg/docs/adrs
  - src/pda
  - src/ontologia
  - infra
  - src/medalhao/ontologia.py
  - src/medalhao/projecao_postgres.py
  - src/medalhao/especie.py
  - tests/test_especie.py
  rollback: Reverter src/medalhao/bronze.py e tests/test_bronze.py.
  observability: commits da Bronze sem a partição lida
source_seam_sha256: d557e754c65ec03ca80b6b91f1ba4f9375a3d3cc4ba84bc5bb2e2de0a911f3c3
---
# Bronze nomeia o landing

## Observable proof

Commit com partição, manifesto e prova conferidos.

## Runnable leaves

- `T-20260924-bronze-nomeia-o-landing` — A Bronze registra qual partição do landing leu: O commit da Bronze traz a partição do landing lida, o manifesto dos objetos e o sha256 da prova; os testes existentes de tests/test_bronze.py passam sem edição; os novos passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
