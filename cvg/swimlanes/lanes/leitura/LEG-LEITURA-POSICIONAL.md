> Projetado de `LEG-LEITURA-POSICIONAL.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `6ebb397912453a29466591a93da1fb174f953c6d139f333d9a4c64be0ee2f445`

---

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
    given: um arquivo com Espécie repetida no cabeçalho e o layout declarado
    when: a leitura termina
    then: o sha256 do arquivo é idêntico, e código e descrição vêm das posições 12 e 13 — não do nome
  - id: B-2
    given: um registro cujo campo monetário é ilegível
    when: os registros são contados
    then: ele entra em linhas_invalidas, não entra na soma, e sai com identidade, valor original e posição
  evals:
  - id: eval_1
    description: Fonte byte-idêntica e leitura posicional com cabeçalho repetido
    bash: pytest -q tests/test_leitura.py -k "sha256 or posicional"
    verifies:
    - B-1
  - id: eval_2
    description: Registro ilegível vira linha inválida com identidade
    bash: pytest -q tests/test_leitura.py -k invalida
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
source_seam_sha256: f3efa25aff9247edc9d003bd2dbc8313b25814c9178adb8fa2ae3ff32a8c566a
---
# A leitura é posicional e não altera a fonte

## Observable proof

sha256 inalterado; a coluna 12 traz código numérico e a 13 descrição de até 20 caracteres.

## Runnable leaves

- `T-20260921-leitura-posicional` — Ler a competência por posição, sem alterar a fonte: sha256 idêntico antes e depois; código e descrição saem de posições distintas; registro ilegível entra em linhas_invalidas.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
