> Projetado de `LEG-LEITURA-POSICIONAL.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `09e218b811801bf57c3e6e9359bf4a5773f37f347c48b409390ea45c2095e0b4`

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
    given: um arquivo com Espécie repetida e o layout declarado, e outro com duas colunas não monetárias
      trocadas de lugar
    when: a leitura começa
    then: no primeiro o sha256 fica idêntico e código e descrição vêm das posições 12 e 13; no segundo
      a leitura BLOQUEIA antes de ler qualquer registro — trocar colunas não monetárias preserva os cinco
      controles, então o juiz monetário não supriria este gate
  - id: B-2
    given: um registro cujo campo monetário é ilegível, e outro cuja descrição tem exatamente 20 caracteres
      com dinheiro válido
    when: os registros são contados
    then: o primeiro entra em linhas_invalidas com identidade, valor original e posição; o segundo NÃO
      é inválido mas emite defeito de truncamento — o defeito do ADR 0004 tem de chegar ao juízo, não
      ficar só documentado
  evals:
  - id: eval_1
    description: Leitura posicional; cabeçalho fora de ordem bloqueia antes de ler
    bash: pytest -q tests/test_leitura.py -k "sha256 or posicional or layout_incompativel"
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
source_seam_sha256: baf78fca28fa858f3b6207e736d54a07173bf7bd80788c26961e0a872db75e61
---
# A leitura é posicional e não altera a fonte

## Observable proof

sha256 inalterado; a coluna 12 traz código numérico e a 13 descrição de até 20 caracteres.

## Runnable leaves

- `T-20260921-leitura-posicional` — Ler a competência por posição, sem alterar a fonte: sha256 idêntico antes e depois; código e descrição saem de posições distintas; registro ilegível entra em linhas_invalidas.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
