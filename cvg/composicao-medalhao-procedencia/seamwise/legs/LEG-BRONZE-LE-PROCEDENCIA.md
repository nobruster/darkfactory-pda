---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-BRONZE-LE-PROCEDENCIA
seam_id: SEAM-BRONZE-LE-PROCEDENCIA
swimlane_id: LANE-BRONZE-LE-PROCEDENCIA
observable_state: A Bronze sai sem a marca quando a procedência confere
proof: A marca só sai com hash, manifesto e controles conferidos.
requires:
- procedencia vinculada
produces:
- bronze com procedencia
tasks:
- id: T-20260923-bronze-le-procedencia
  title: Bronze confere _PROCEDENCIA.json da partição
  goal: Tirar a marca PROCEDENCIA_NAO_VINCULADA só com prova.
  done_condition: Com _PROCEDENCIA.json válido a Bronze sai sem a marca e com o hash; sem ele, a marca
    continua; com manifesto divergente, DIVERGE; e toda a suíte já existente de tests/test_bronze.py continua
    passando.
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
  - T-20260923-vincula-procedencia
  touches_paths:
  - src/medalhao/bronze.py
  - tests/test_bronze.py
  creates_paths: []
  behavior:
  - id: B-1
    given: a partição com _PROCEDENCIA.json gravado pelo vinculador
    when: a Bronze lê a competência
    then: 'lê o arquivo do prefixo da partição, confere o sha256 do CSV contra o contrato, a COMPETÊNCIA
      do arquivo contra a solicitada e a do contrato, o MANIFESTO contra os objetos de dado que ela mesma
      lista — nome, tamanho e sha256 do conteúdo, com a mesma definição de objeto de dado do vinculador:
      objeto de dado é todo objeto sob o prefixo da partição EXCETO os auxiliares que o contrato nomeia
      em objetos_auxiliares_ignorados e o próprio _PROCEDENCIA.json — isenções nomeadas uma a uma, nunca
      exclusão por prefixo, para um _extra.parquet contar como objeto a mais — e os controles do arquivo
      contra os que ela mede; conferindo tudo, sai sem a marca PROCEDENCIA_NAO_VINCULADA e com hash_procedencia
      preenchido, e o estado INTEGRO segue as regras que já existem.'
  - id: B-2
    given: uma partição sem _PROCEDENCIA.json, com um JSON inválido, ou com manifesto que não bate com
      os objetos
    when: a Bronze lê a competência
    then: sem o arquivo, a marca continua como hoje; JSON inválido é ERRO_LEITURA; manifesto, hash ou
      controles divergentes são DIVERGE com a diferença nomeada, e nada é gravado — objeto a mais, a menos
      ou alterado depois da vinculação é exatamente o que a procedência existe para acusar. Nenhum teste
      já existente de tests/test_bronze.py é editado.
  evals:
  - id: eval_1
    description: A marca sai só com prova conferida
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in procedencia_confere_tira_a_marca
      manifesto_confere_objetos_listados controles_da_procedencia_conferidos competencia_da_prova_conferida;
      do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" ||
      { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k
      "procedencia_confere_tira_a_marca or manifesto_confere_objetos_listados or controles_da_procedencia_conferidos
      or competencia_da_prova_conferida"'
    verifies:
    - B-1
  - id: eval_2
    description: Ausente, inválida ou divergente
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sem_procedencia_mantem_a_marca
      procedencia_json_invalido_e_erro objeto_a_mais_diverge hash_da_procedencia_diverge objeto_com_underscore_a_mais_diverge;
      do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" ||
      { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k
      "sem_procedencia_mantem_a_marca or procedencia_json_invalido_e_erro or objeto_a_mais_diverge or
      hash_da_procedencia_diverge or objeto_com_underscore_a_mais_diverge"'
    verifies:
    - B-2
  - id: eval_3
    description: A suíte já existente continua passando
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in cinco_controles particao_ausente
      centavo_a_mais; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null
      | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py
      -k "cinco_controles or particao_ausente or centavo_a_mais"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: aceitar o hash do arquivo sem conferir o manifesto
    reason: hash certo sem vínculo com os objetos lidos não prova nada
    instead: conferir nome, tamanho e sha256 de cada objeto listado
  - action: ignorar objetos pelo prefixo _ em vez de nomeá-los
    reason: um _extra.parquet ficaria fora do manifesto sem acusar
    instead: isentar só os auxiliares do contrato e o _PROCEDENCIA.json, um a um
  - action: editar um teste já existente de tests/test_bronze.py
    reason: teste selado que precisa mudar denuncia mudança de comportamento
    instead: só acrescentar testes novos
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  rollback: Reverter src/medalhao/bronze.py e tests/test_bronze.py ao commit assentado.
  observability: leituras com a marca PROCEDENCIA_NAO_VINCULADA
source_seam_sha256: f270284063cd4d649abcdfdae50fb41ae05d4e7552a3b8072ef13baa8c4c9478
---
# A Bronze sai sem a marca quando a procedência confere

## Observable proof

A marca só sai com hash, manifesto e controles conferidos.

## Runnable leaves

- `T-20260923-bronze-le-procedencia` — Bronze confere _PROCEDENCIA.json da partição: Com _PROCEDENCIA.json válido a Bronze sai sem a marca e com o hash; sem ele, a marca continua; com manifesto divergente, DIVERGE; e toda a suíte já existente de tests/test_bronze.py continua passando.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
