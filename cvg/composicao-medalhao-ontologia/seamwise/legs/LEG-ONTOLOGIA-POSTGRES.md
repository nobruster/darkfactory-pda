---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-ONTOLOGIA-POSTGRES
seam_id: SEAM-ONTOLOGIA-POSTGRES
swimlane_id: LANE-ONTOLOGIA-POSTGRES
observable_state: Ontologia projetada e reconferida
proof: Contagens 2/13/14/5/65 relidas do banco iguais à ontologia; sha256 na tabela carga.
requires:
- ontologia carregada
produces:
- ontologia no postgres
tasks:
- id: T-20260924-ontologia-postgres
  title: Projeção da ontologia no Postgres, carregada numa transação e reconferida
  goal: 'Carregar a ontologia no Postgres pda-postgres para consulta fora do Spark, sem que o banco vire
    fonte da verdade: tudo ou nada, reconferido linha a linha, com a versão da ontologia gravada. Para
    rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec
    -T spark python3 -m pytest <arquivo> -k <cenarios>`.'
  done_condition: projetar_ontologia carrega fontes, termos, colunas, grupos e espécies num schema nomeado,
    numa transação só, reconfere cada tabela contra a ontologia e grava o sha256 da ontologia; falha no
    meio deixa a carga anterior intacta; os testes de tests/test_projecao_postgres.py passam.
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
  - T-20260924-ontologia-versionada
  touches_paths: []
  creates_paths:
  - src/medalhao/projecao_postgres.py
  - tests/test_projecao_postgres.py
  behavior:
  - id: B-1
    given: a ontologia carregada e as variáveis PG_HOST, PG_PORT, PG_DB, PG_USER e PG_PASSWORD do ambiente
    when: projetar_ontologia(ontologia, schema) roda
    then: num schema OBRIGATÓRIO, sem valor padrão, cujo nome é validado como identificador simples (letras
      minúsculas, dígitos e _), cria as tabelas fonte, termo, coluna, grupo e especie, com chave primária
      em cada uma e chave estrangeira de coluna para termo e de especie para grupo, e uma tabela carga
      com o sha256 da ontologia e o instante da carga; a carga substitui o conteúdo anterior do schema
      numa ÚNICA transação e, AINDA DENTRO dela, antes do commit, relê cada tabela e confere linha a linha
      contra a ontologia — 2 fontes, 13 termos, 14 colunas, os grupos do contrato (5 hoje), 65 espécies
      —; só então faz commit e devolve PROJETADA com as contagens. Aceita um parâmetro apos_tabela, chamado
      dentro da transação depois de cada tabela carregada, pelo qual os testes injetam falha ou alteração.
      Credenciais só do ambiente, nunca escritas no código, nunca impressas nem incluídas em mensagem
      de erro.
  - id: B-2
    given: uma carga que falha no meio, uma variável de ambiente ausente, ou um nome de schema inválido
    when: projetar_ontologia roda
    then: 'falha no meio desfaz a transação e a carga anterior fica intacta, conferida pelo sha256 na
      tabela carga; reconferência divergente — uma linha alterada por apos_tabela — desfaz a transação,
      devolve DIVERGENTE e a carga anterior segue sendo a visível; variável ausente recusa SEM chamar
      psycopg.connect (o teste o substitui por um que falha se chamado) e nomeia a variável, nunca o valor;
      um erro de conexão não traz a senha na mensagem; nome de schema fora do padrão, ''public'' ou começado
      por ''pg_'' recusa sem executar SQL. Cada teste usa um schema ''teste_'' com sufixo aleatório, apagado
      no finalizer da fixture — mesmo quando o teste falha —, e nunca apaga schema que ele não criou.
      Nenhum cenário usa skip, xfail ou importorskip: Postgres indisponível FALHA o teste.'
  evals:
  - id: eval_1
    description: A projeção carrega e confere
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in projeta_e_reconfere
      grava_sha256_da_ontologia chaves_estrangeiras_valem chave_primaria_em_cada_tabela; do python3 -m
      pytest --collect-only -q tests/test_projecao_postgres.py -k "$c" 2>/dev/null | grep -q "::" || {
      echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_projecao_postgres.py
      -k "projeta_e_reconfere or grava_sha256_da_ontologia or chaves_estrangeiras_valem or chave_primaria_em_cada_tabela"'
    verifies:
    - B-1
  - id: eval_2
    description: Tudo ou nada
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in falha_no_meio_preserva_carga_anterior
      divergencia_desfaz_e_preserva_carga_anterior; do python3 -m pytest --collect-only -q tests/test_projecao_postgres.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_projecao_postgres.py -k "falha_no_meio_preserva_carga_anterior or divergencia_desfaz_e_preserva_carga_anterior"'
    verifies:
    - B-2
  - id: eval_3
    description: Sem credencial no código e sem SQL de nome livre
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in variavel_ausente_recusa_sem_conectar
      erro_de_conexao_nao_vaza_senha schema_invalido_recusa schema_public_recusa schema_de_teste_apagado;
      do python3 -m pytest --collect-only -q tests/test_projecao_postgres.py -k "$c" 2>/dev/null | grep
      -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_projecao_postgres.py
      -k "variavel_ausente_recusa_sem_conectar or erro_de_conexao_nao_vaza_senha or schema_invalido_recusa
      or schema_public_recusa or schema_de_teste_apagado"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: escrever credencial, host ou senha padrão no código ou no teste
    reason: é o defeito do legado que o BRD nomeou (Regra 6)
    instead: ler PG_* do ambiente e recusar se faltar
  - action: montar SQL com o nome do schema sem validar
    reason: nome livre em SQL é injeção
    instead: validar o identificador e usar psycopg.sql.Identifier
  - action: inserir tabela por tabela em transações separadas
    reason: uma falha no meio deixa o banco com meia ontologia
    instead: uma transação para a carga inteira
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src/pda
  - infra
  - src/ontologia/beneficios-emitidos.yaml
  - src/medalhao/ontologia.py
  rollback: Remover os dois arquivos criados e apagar o schema carregado.
  observability: projeções divergentes da ontologia versionada
source_seam_sha256: d000271ccc150ae31bdc39c4a8229467b6a8166342f533393847879c96fc2b8e
---
# Ontologia projetada e reconferida

## Observable proof

Contagens 2/13/14/5/65 relidas do banco iguais à ontologia; sha256 na tabela carga.

## Runnable leaves

- `T-20260924-ontologia-postgres` — Projeção da ontologia no Postgres, carregada numa transação e reconferida: projetar_ontologia carrega fontes, termos, colunas, grupos e espécies num schema nomeado, numa transação só, reconfere cada tabela contra a ontologia e grava o sha256 da ontologia; falha no meio deixa a carga anterior intacta; os testes de tests/test_projecao_postgres.py passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
