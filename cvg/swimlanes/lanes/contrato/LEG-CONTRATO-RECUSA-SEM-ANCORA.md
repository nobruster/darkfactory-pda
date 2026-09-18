> Projetado de `LEG-CONTRATO-RECUSA-SEM-ANCORA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `060ea64f257cc12265db0f5fbe36e02aa66b7c2e4ac94cba32d12506b9cf1a18`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-CONTRATO-RECUSA-SEM-ANCORA
seam_id: SEAM-CONTRATO-ANCORA
swimlane_id: LANE-CONTRATO
observable_state: A fábrica recusa construir sem âncora medida
proof: Competência sem âncora no contrato produz NAO_MEDIDO e exit diferente de zero, antes de qualquer
  leitura de dado.
requires: []
produces:
- contrato validado
tasks:
- id: T-20260917-contrato-ancora
  title: Carregar o contrato e recusar competência sem âncora
  goal: Fazer a ausência de prova bloquear, em vez de virar verde.
  done_condition: Competência com âncora carrega os cinco valores; sem âncora retorna NAO_MEDIDO e exit
    1.
  effort: S
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
  - src/fabrica/contrato.py
  - tests/test_contrato.py
  behavior:
  - id: B-1
    given: uma âncora com os cinco números nomeados (count_linhas, sum_vl_liquido, min, max, linhas_invalidas)
      E a procedência — aprovador, data e comando que mediu
    when: o contrato é carregado
    then: os cinco valores saem com a procedência; a MESMA âncora sem aprovador ou sem data de medição
      resulta em NAO_MEDIDO, porque número presente não é âncora autorizada
  - id: B-2
    given: uma competência sem âncora no contrato
    when: o contrato é carregado
    then: o resultado é NAO_MEDIDO, o veredito CHEGA à evidência antes da saída, e só então o processo
      sai com código 1
  evals:
  - id: eval_1
    description: Cinco valores nomeados com procedência; sem aprovador ou data vira NAO_MEDIDO
    bash: pytest -q tests/test_contrato.py -k "ancorada or sem_procedencia"
    verifies:
    - B-1
  - id: eval_2
    description: Sem âncora recusa construir E grava o veredito na evidência
    bash: pytest -q tests/test_contrato.py -k "nao_medido or nao_medido_vira_evidencia"
    verifies:
    - B-2
  - id: eval_3
    description: A âncora carregada bate com o contrato em disco
    bash: pytest -q tests/test_contrato.py -k integridade
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: gerar a âncora automaticamente quando ela falta
    reason: um número que ninguém viu medir é um palpite
    instead: retornar NAO_MEDIDO e parar
  - action: tratar âncora ausente como zero
    reason: o gate compararia contra nada e publicaria ACEITO
    instead: distinguir ausência de valor
  - action: editar a âncora para um veredito passar
    reason: falsifica a verdade contra a qual tudo é medido
    instead: investigar; âncora revista exige nova aprovação
  do_not_touch:
  - cvg/docs/adrs
  rollback: Remover o carregador de contrato e seus testes.
  observability: contagem de competências ancoradas no contrato
source_seam_sha256: fe6717183e4d19e368d79982795a09be4996fa8580917815b509bf68d4aba467
---
# A fábrica recusa construir sem âncora medida

## Observable proof

Competência sem âncora no contrato produz NAO_MEDIDO e exit diferente de zero, antes de qualquer leitura de dado.

## Runnable leaves

- `T-20260917-contrato-ancora` — Carregar o contrato e recusar competência sem âncora: Competência com âncora carrega os cinco valores; sem âncora retorna NAO_MEDIDO e exit 1.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
