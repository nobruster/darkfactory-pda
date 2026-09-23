---
schema_version: 1
kind: seam
claim: derived
id: SEAM-JUIZO-NA-INGESTAO
name: Ingestão julgada — o bruto lido uma vez, pelos dois motores
description: Separa ler o arquivo bruto de consumir as camadas que dele derivam.
evidence:
- E-ANCORA-202601
responsibility: Julgar a Bronze contra o CSV pelo segundo motor na ingestão e só publicá-la com o pacote
  ACEITO, registrando esse pacote no commit.
consumes:
- procedencia vinculada
produces:
- bronze julgada
owner: medalhao
independent_proof: Sobre o dado real, conduzir devolve ACEITO na ingestão e o commit da Bronze nomeia
  o caminho e o sha256 do pacote.
decision_ids:
- DEC-JUIZO-NA-INGESTAO
rejected_alternatives:
- alternative: Manter o juízo no portão da Gold
  reason: Obriga a Gold a ler o arquivo inteiro, contra o medalhão.
swimlane:
  id: LANE-JUIZO-NA-INGESTAO
  name: Ingestão julgada lane
  owner: medalhao
  legs:
  - id: LEG-JUIZO-NA-INGESTAO
    observable_state: A Bronze publicada carrega o pacote ACEITO da ingestão
    proof: Sem ACEITO, a Bronze não publica; com ACEITO, o commit nomeia o pacote.
    requires: []
    produces:
    - bronze julgada
    tasks:
    - id: T-20260923-ingestao-julgada
      title: Julgar a ingestão com o segundo motor e publicar a Bronze só com ACEITO
      goal: Ler o arquivo bruto uma vez, na ingestão, com os dois motores.
      done_condition: Sobre uma landing vinculada, conduzir julga a Bronze contra o CSV; só com autorizado_publicar
        a Bronze publica, e o commit nomeia o pacote; sem autorização, nada é publicado.
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
      - src/medalhao/bronze.py
      creates_paths:
      - src/medalhao/ingestao.py
      - tests/test_ingestao.py
      behavior:
      - id: B-1
        given: a landing vinculada ao CSV, o contrato e o CSV original em _raw/
        when: a ingestão roda para a competência
        then: chama orquestracao.conduzir com um executar_leitura que mede a Bronze no motor Spark SEM
          gravar e lê o CSV pelo segundo motor, o leitor posicional em Python já selado, montando InsumosExecucao;
          só com Desfecho.autorizado_publicar a Bronze publica pelo protocolo que já existe — preparo,
          replaceWhere, reconferência —, e o userMetadata do commit nomeia o caminho_pacote e o sha256
          do pacote do juízo. O orquestrador e o juiz selados são reusados, nunca alterados. O que publica
          é o MESMO resultado medido dentro do executar_leitura — nunca uma segunda leitura da landing
          —, e a reconferência depois de publicar compara a Bronze publicada com os cinco controles e
          o total_por_codigo que o pacote JULGOU, não só com o próprio preparo.
      - id: B-2
        given: um juízo que não autoriza — RECUSADO, ERRO ou ACEITO_SEM_ANCORA
        when: a ingestão termina
        then: a Bronze não publica nada, o pacote do juízo fica gravado como evidência com o motivo, e
          a ingestão devolve o veredito do orquestrador sem traduzi-lo; nenhum teste já existente de tests/test_bronze.py
          é editado.
      evals:
      - id: eval_1
        description: O juízo acontece na ingestão, com os dois motores
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in julga_na_ingestao_com_segundo_motor
          publica_bronze_so_com_aceito commit_da_bronze_nomeia_o_pacote publicado_confere_com_o_julgado;
          do python3 -m pytest --collect-only -q tests/test_ingestao.py -k "$c" 2>/dev/null | grep -q
          "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_ingestao.py
          -k "julga_na_ingestao_com_segundo_motor or publica_bronze_so_com_aceito or commit_da_bronze_nomeia_o_pacote
          or publicado_confere_com_o_julgado"'
        verifies:
        - B-1
      - id: eval_2
        description: Sem autorização, nada publica
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in recusado_nao_publica
          erro_nao_publica pacote_fica_como_evidencia; do python3 -m pytest --collect-only -q tests/test_ingestao.py
          -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
          -m pytest -q tests/test_ingestao.py -k "recusado_nao_publica or erro_nao_publica or pacote_fica_como_evidencia"'
        verifies:
        - B-2
      - id: eval_3
        description: Orquestrador reusado, não alterado
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reusa_conduzir_selado
          reusa_leitor_posicional; do python3 -m pytest --collect-only -q tests/test_ingestao.py -k "$c"
          2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m
          pytest -q tests/test_ingestao.py -k "reusa_conduzir_selado or reusa_leitor_posicional"'
        verifies:
        - B-1
      anti_patterns:
      - action: reimplementar o juiz ou o orquestrador dentro da ingestão
        reason: são selados; uma segunda versão pode divergir em silêncio
        instead: chamar orquestracao.conduzir
      - action: ler o CSV pelo Spark no lugar do leitor Python
        reason: dois motores iguais não se conferem (ADR 0006)
        instead: usar o leitor posicional já selado
      - action: publicar a Bronze antes do veredito
        reason: publicação sem juízo é o que o portão existe para impedir
        instead: publicar só com autorizado_publicar
      do_not_touch:
      - _raw
      - cvg/docs/adrs
      - contracts
      - src/pda
      rollback: Reverter src/medalhao/bronze.py; remover ingestao.py e seu teste.
      observability: competências com Bronze publicada sem pacote no commit
---
# Ingestão julgada — o bruto lido uma vez, pelos dois motores

Separa ler o arquivo bruto de consumir as camadas que dele derivam.

## Responsibility

Julgar a Bronze contra o CSV pelo segundo motor na ingestão e só publicá-la com o pacote ACEITO, registrando esse pacote no commit.

## Independent proof

Sobre o dado real, conduzir devolve ACEITO na ingestão e o commit da Bronze nomeia o caminho e o sha256 do pacote.

## Rejected alternatives

- **Manter o juízo no portão da Gold** — Obriga a Gold a ler o arquivo inteiro, contra o medalhão.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
