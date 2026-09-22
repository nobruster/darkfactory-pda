---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-CONTRATO-RECUSA-SEM-ANCORA
seam_id: SEAM-CONTRATO
swimlane_id: LANE-CONTRATO
observable_state: A fábrica recusa construir sem âncora medida
proof: Competência sem âncora devolve NAO_MEDIDO; com âncora incompleta (sem aprovador ou sem data) também.
requires: []
produces:
- contrato validado
tasks:
- id: T-20260921-contrato-ancora
  title: Carregar contrato, âncora e layout posicional
  goal: Fazer a ausência de prova bloquear em vez de virar verde.
  done_condition: Os cinco controles e o layout saem com procedência; sem âncora, ou sem aprovador, retorna
    NAO_MEDIDO como valor.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on: []
  touches_paths: []
  creates_paths:
  - src/pda/contrato.py
  - tests/test_contrato.py
  - contracts/competencia-202601.yaml
  behavior:
  - id: B-1
    given: um contrato com os cinco controles nomeados, a procedência, o layout posicional e os DOIS hashes
      — o do ZIP publicado e o do CSV extraído sobre o qual a âncora foi medida
    when: o contrato é carregado
    then: âncora, procedência, layout, os dois hashes e a POLÍTICA DECIMAL saem juntos — precisão, granularidade
      e modo de arredondamento são dados carregados do contrato, como o ADR 0003 exige, não escolha privada
      de quem implementa. Contrato SEM política decimal é NAO_MEDIDO, senão o agregador local fixa a sua,
      passa nos exemplos, e um produtor externo escolhe outra sem nada acusar. E contrato COM política
      que contradiz o ADR — HALF_UP, ou granularidade por campo — é RECUSADO no carregamento, não validado,
      porque um contrato contraditório deixaria o agregador entre obedecer ao contrato e obedecer à decisão
      vinculante; a validação confere a política contra o ADR, e nunca o contrário. Falta o hash do CSV
      e também é NAO_MEDIDO, porque hoje só o ZIP tem checksum e a âncora foi medida no CSV — sem o par,
      trocar o CSV extraído não seria detectado; sem aprovador ou sem data, idem
  - id: B-2
    given: uma competência sem âncora no contrato
    when: o contrato é carregado
    then: retorna NAO_MEDIDO como valor, sem gravar nem encerrar o processo
  evals:
  - id: eval_1
    description: Hashes distintos; política ausente vira NAO_MEDIDO e política HALF_UP é recusada
    bash: pytest -q tests/test_contrato.py -k "ancorada or hash_zip_e_csv or sem_politica_decimal or politica_contradiz_adr"
    verifies:
    - B-1
  - id: eval_2
    description: Sem âncora retorna NAO_MEDIDO sem escrever em disco
    bash: pytest -q tests/test_contrato.py -k nao_medido
    verifies:
    - B-2
  - id: eval_3
    description: O layout declara as 14 posições, com Espécie em 12 e 13
    bash: pytest -q tests/test_contrato.py -k layout
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: gerar a âncora quando ela falta
    reason: um número que ninguém viu medir é um palpite
    instead: retornar NAO_MEDIDO
  - action: editar a âncora para um veredito passar
    reason: falsifica a verdade contra a qual tudo é medido
    instead: investigar; âncora revista exige nova aprovação
  - action: declarar colunas por nome no contrato
    reason: Espécie aparece duas vezes e o nome não decide qual
    instead: declarar o índice posicional
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  rollback: Remover o carregador de contrato e seus testes.
  observability: competências ancoradas no contrato
source_seam_sha256: e549ab80d1662c71292dbcce33d197a713af88a5f6405ee638563437c00a4000
---
# A fábrica recusa construir sem âncora medida

## Observable proof

Competência sem âncora devolve NAO_MEDIDO; com âncora incompleta (sem aprovador ou sem data) também.

## Runnable leaves

- `T-20260921-contrato-ancora` — Carregar contrato, âncora e layout posicional: Os cinco controles e o layout saem com procedência; sem âncora, ou sem aprovador, retorna NAO_MEDIDO como valor.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
