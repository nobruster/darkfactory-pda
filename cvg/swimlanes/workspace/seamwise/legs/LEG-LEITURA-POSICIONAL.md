---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-LEITURA-POSICIONAL
seam_id: SEAM-LEITURA
swimlane_id: LANE-LEITURA
observable_state: A leitura é posicional e não altera a fonte
proof: sha256 inalterado; a coluna 12 traz código numérico e a 13 descrição de até 20 caracteres.
requires:
- contrato validado
produces:
- registros lidos
- defeitos observados
- sha256 computado na leitura
- totais por código da leitura
tasks:
- id: T-20260921-leitura-posicional
  title: Ler a competência por posição, sem alterar a fonte
  goal: Extrair registros preservando os bytes e o defeito de origem.
  done_condition: sha256 idêntico antes e depois; código e descrição saem de posições distintas; registro
    ilegível entra em linhas_invalidas.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on:
  - T-20260921-contrato-ancora
  touches_paths: []
  creates_paths:
  - src/pda/leitura.py
  - tests/test_leitura.py
  - tests/fixtures/competencia-min.csv
  behavior:
  - id: B-1
    given: um arquivo com Espécie repetida e o layout declarado, e outro em que as DUAS colunas de cabeçalho
      idêntico Espécie — índices 12 e 13 — tiveram os valores trocados entre si, deixando o cabeçalho
      byte a byte igual
    when: a leitura começa
    then: no primeiro o sha256 fica idêntico e código e descrição vêm dos índices 12 e 13; no segundo
      a leitura BLOQUEIA, e o gate NÃO pode ser conferência de cabeçalho — cabeçalho idêntico não distingue
      as duas — e sim o formato de cada posição, o índice 12 com código de 2 dígitos à direita e o 13
      com descrição textual; o teste falha se for satisfeito trocando colunas de nomes diferentes, porque
      é esta troca, de nomes iguais, que motivou o ADR 0002 e que os cinco controles preservam
  - id: B-2
    given: um registro cujo campo monetário é ilegível, e os quatro exemplos do ADR 0004 — entre eles
      'Pensão por Morte de ' com 20 caracteres brutos e 19 após strip
    when: os registros são contados
    then: o primeiro entra em linhas_invalidas com identidade, valor original e posição; os quatro emitem
      defeito de truncamento sem serem inválidos, porque o critério é o campo BRUTO ocupar os 20 caracteres
      do layout — medir após strip deixaria o exemplo principal do ADR de fora
  evals:
  - id: eval_1
    description: Leitura posicional; Espécie 12 e 13 trocadas entre si bloqueiam
    bash: pytest -q tests/test_leitura.py -k "sha256 or posicional or especie_12_13_trocadas"
    verifies:
    - B-1
  - id: eval_2
    description: Ilegível vira inválida; descrição truncada emite defeito
    bash: pytest -q tests/test_leitura.py -k "invalida or truncamento_emitido"
    verifies:
    - B-2
  - id: eval_3
    description: A leitura reporta sua duração para a orquestração medir o total
    bash: pytest -q tests/test_leitura.py -k duracao
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: escrever no arquivo de origem
    reason: destrói a prova de que a origem publicou aquilo
    instead: tratar _raw/ como somente leitura
  - action: ler colunas por nome de cabeçalho
    reason: Espécie repetida faz perder uma das duas em silêncio
    instead: ler por posição declarada no contrato
  - action: corrigir valor malformado durante a leitura
    reason: apaga o defeito antes da classificação
    instead: preservar e contar como linha inválida
  do_not_touch:
  - _raw
  rollback: Remover o leitor e seus testes.
  observability: registros lidos e defeitos por tipo
source_seam_sha256: 8bddbdbb4a706ca85794bbea3c15a1db8f22ac63f990008089329ebb718111d4
---
# A leitura é posicional e não altera a fonte

## Observable proof

sha256 inalterado; a coluna 12 traz código numérico e a 13 descrição de até 20 caracteres.

## Runnable leaves

- `T-20260921-leitura-posicional` — Ler a competência por posição, sem alterar a fonte: sha256 idêntico antes e depois; código e descrição saem de posições distintas; registro ilegível entra em linhas_invalidas.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
