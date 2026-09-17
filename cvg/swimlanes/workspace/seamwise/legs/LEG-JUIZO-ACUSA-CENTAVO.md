---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-JUIZO-ACUSA-CENTAVO
seam_id: SEAM-JUIZO
swimlane_id: LANE-JUIZO
observable_state: O juiz recusa um centavo de divergência
proof: Teste que corrompe uma linha em um centavo exige recusa; o teste falha se o juiz aceitar.
requires:
- agregado da competência
- contrato validado
produces:
- veredito classificado
tasks:
- id: T-20260917-juizo-classifica
  title: Comparar contra a âncora e classificar a diferença
  goal: Fazer o juiz acusar, não apenas aprovar.
  done_condition: Um centavo alterado é recusado, e diferença sem classificação bloqueia a publicação.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on:
  - T-20260917-agregacao-exata
  touches_paths: []
  creates_paths:
  - src/fabrica/juizo.py
  - tests/test_juizo.py
  behavior:
  - id: B-1
    given: um agregado com um centavo alterado
    when: o juízo compara contra a âncora
    then: o veredito é recusado e o processo sai com código 1
  - id: B-2
    given: uma diferença sem classificação atribuída
    when: o veredito é calculado
    then: o resultado é UNRESOLVED e bloqueia
  evals:
  - id: eval_1
    description: Um centavo de divergência é recusado
    bash: pytest -q tests/test_juizo.py -k um_centavo
    verifies:
    - B-1
  - id: eval_2
    description: Diferença não classificada bloqueia
    bash: pytest -q tests/test_juizo.py -k unresolved
    verifies:
    - B-2
  - id: eval_3
    description: As seis classificações são exaustivas e exclusivas
    bash: pytest -q tests/test_juizo.py -k classificacoes
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: introduzir parâmetro de tolerância
    reason: um centavo inexplicado viraria um centavo aceito
    instead: classificar a diferença ou consertar o pipeline
  - action: editar a âncora para o veredito passar
    reason: falsifica a prova em vez de investigar
    instead: investigar; âncora revista exige nova aprovação
  - action: classificar como UNRESOLVED para destravar
    reason: UNRESOLVED bloqueia; usá-lo como atalho esconde a causa
    instead: medir a diferença e atribuir a classificação certa
  do_not_touch:
  - cvg/docs/adrs
  - contracts
  rollback: Remover o juízo e seus testes.
  observability: vereditos por classificação
source_seam_sha256: 8eb328041f2e216e1e2a8ccfcfb6deea2cdb8604c867993c314d8d3abf522cb7
---
# O juiz recusa um centavo de divergência

## Observable proof

Teste que corrompe uma linha em um centavo exige recusa; o teste falha se o juiz aceitar.

## Runnable leaves

- `T-20260917-juizo-classifica` — Comparar contra a âncora e classificar a diferença: Um centavo alterado é recusado, e diferença sem classificação bloqueia a publicação.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
