> Projetado de `LEG-LEITURA-NAO-ALTERA-FONTE.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `32d957c7f92101151e8a746bb1aa5cc5de95e467e3f44dceb69b983327aebd8d`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-LEITURA-NAO-ALTERA-FONTE
seam_id: SEAM-LEITURA
swimlane_id: LANE-LEITURA
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
  done_condition: O sha256 do arquivo é idêntico antes e depois, e a contagem de registros bate com a
    âncora.
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
  - tests/fixtures/competencia-min.csv
  behavior:
  - id: B-1
    given: o arquivo de uma competência e o layout declarado no contrato (posições, formato monetário,
      chave do registro)
    when: a leitura termina
    then: o sha256 do arquivo é idêntico ao de antes, e cada campo lido vem da POSIÇÃO declarada — cabeçalho
      repetido não decide nada
  - id: B-2
    given: o arquivo de 2026-03, com um registro cujo campo monetário é ilegível
    when: os registros são contados e a leitura termina
    then: a contagem bate com a do contrato para aquele arquivo — 41719140 na fonte real de 2026-03, o
      valor do fixture nos testes —, o registro ilegível entra em linhas_invalidas e NÃO entra em sum/min/max,
      e o defeito sai com identidade, valor original e posição
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
    do início da leitura ao veredito (o limite de R-6, sem o qual tudo passa mesmo levando horas — objeção
    C7)
source_seam_sha256: 5156a0eb0352db7ac3f204e7646ca51d91691a4dd2cd5258699b3b52c8e64ed9
---
# A leitura não altera a fonte e conta o esperado

## Observable proof

sha256 do arquivo inalterado após a leitura; contagem de registros igual a 41719140 para 2026-03.

## Runnable leaves

- `T-20260917-leitura-competencia` — Ler a competência sem alterar a fonte: O sha256 do arquivo é idêntico antes e depois, e a contagem de registros bate com a âncora.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
