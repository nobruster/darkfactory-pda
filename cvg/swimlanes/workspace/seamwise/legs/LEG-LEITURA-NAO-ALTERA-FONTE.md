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
  behavior:
  - id: B-1
    given: o arquivo de uma competência
    when: a leitura termina
    then: o sha256 do arquivo é idêntico ao de antes
  - id: B-2
    given: o arquivo de 2026-03
    when: os registros são contados
    then: a contagem é 41719140
  evals:
  - id: eval_1
    description: A fonte permanece byte-idêntica
    bash: pytest -q tests/test_leitura.py -k sha256
    verifies:
    - B-1
  - id: eval_2
    description: A contagem bate com a âncora
    bash: pytest -q tests/test_leitura.py -k contagem
    verifies:
    - B-2
  - id: eval_3
    description: Registro malformado é preservado, não corrigido
    bash: pytest -q tests/test_leitura.py -k preserva_defeito
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
  observability: contagem de registros lidos por competência
source_seam_sha256: fe4a3d93819553fd0686d836105214b801b26832ce44a7edf188b17bed90128e
---
# A leitura não altera a fonte e conta o esperado

## Observable proof

sha256 do arquivo inalterado após a leitura; contagem de registros igual a 41719140 para 2026-03.

## Runnable leaves

- `T-20260917-leitura-competencia` — Ler a competência sem alterar a fonte: O sha256 do arquivo é idêntico antes e depois, e a contagem de registros bate com a âncora.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
