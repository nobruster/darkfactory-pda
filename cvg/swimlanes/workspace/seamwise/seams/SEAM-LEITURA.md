---
schema_version: 1
kind: seam
claim: derived
id: SEAM-LEITURA
name: Leitura da competência
description: Separa a extração dos bytes da interpretação monetária.
evidence:
- E-ANCORA-202603
responsibility: Ler os registros da competência preservando os bytes originais.
consumes:
- arquivo da competência
produces:
- registros lidos
- defeitos observados
owner: leitura
independent_proof: O hash do arquivo antes e depois da leitura é idêntico, e a contagem de registros lidos
  bate com a contagem da âncora.
decision_ids:
- ADR-0002-ANCORA-2026-03
rejected_alternatives:
- alternative: Normalizar valores durante a leitura
  reason: Normalizar apaga o defeito da origem antes que alguém possa classificá-lo.
swimlane:
  id: LANE-LEITURA
  name: Leitura lane
  owner: leitura
  legs:
  - id: LEG-LEITURA-NAO-ALTERA-FONTE
    observable_state: A leitura não altera a fonte e conta o esperado
    proof: sha256 do arquivo inalterado após a leitura; contagem de registros igual a 41719140 para 2026-03.
    requires:
    - contrato validado
    produces:
    - registros lidos
    - defeitos observados
    tasks:
    - id: T-20260917-leitura-competencia
      title: Ler a competência sem alterar a fonte
      goal: Extrair registros preservando os bytes originais.
      done_condition: O sha256 do arquivo é idêntico antes e depois, e a contagem de registros bate com
        a âncora.
      effort: M
      profile: standard
      execution_backend: any
      required_tools:
      - git
      - bash
      - python3
      - pytest
      depends_on:
      - T-20260917-contrato-ancora
      touches_paths: []
      creates_paths:
      - src/fabrica/leitura.py
      - tests/test_leitura.py
      behavior:
      - id: B-1
        given: o arquivo de uma competência e o layout declarado no contrato (posições, formato monetário,
          chave do registro)
        when: a leitura termina
        then: o sha256 do arquivo é idêntico ao de antes, e cada campo lido vem da POSIÇÃO declarada —
          cabeçalho repetido não decide nada
      - id: B-2
        given: o arquivo de 2026-03, com um registro malformado
        when: os registros são contados e a leitura termina
        then: a contagem é 41719140 E o defeito sai com identidade do registro, valor original e posição
          — preservar no arquivo não basta se a informação some na interface
      evals:
      - id: eval_1
        description: Fonte byte-idêntica; leitura posicional com cabeçalho repetido
        bash: pytest -q tests/test_leitura.py -k "sha256 or posicional"
        verifies:
        - B-1
      - id: eval_2
        description: Contagem bate com a âncora e o defeito sai com identidade
        bash: pytest -q tests/test_leitura.py -k "contagem or defeito_identificado"
        verifies:
        - B-2
      - id: eval_3
        description: A leitura reporta seus segundos para a orquestração medir o total
        bash: pytest -q tests/test_leitura.py -k reporta_duracao
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: escrever no arquivo de origem
        reason: destrói a prova de que a origem publicou aquilo
        instead: tratar a origem como somente leitura
      - action: corrigir valor malformado durante a leitura
        reason: apaga o defeito antes da classificação
        instead: preservar e deixar o juízo classificar
      - action: ler colunas por nome de cabeçalho
        reason: cabeçalho com nome repetido faz perder a coluna em silêncio
        instead: ler por posição declarada no contrato
      do_not_touch:
      - _raw
      rollback: Remover o leitor e seus testes.
      observability: contagem de registros lidos por competência, defeitos observados por tipo, e segundos
        do início da leitura ao veredito (o limite de R-6, sem o qual tudo passa mesmo levando horas —
        objeção C7)
---
# Leitura da competência

Separa a extração dos bytes da interpretação monetária.

## Responsibility

Ler os registros da competência preservando os bytes originais.

## Independent proof

O hash do arquivo antes e depois da leitura é idêntico, e a contagem de registros lidos bate com a contagem da âncora.

## Rejected alternatives

- **Normalizar valores durante a leitura** — Normalizar apaga o defeito da origem antes que alguém possa classificá-lo.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
