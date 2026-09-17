---
schema_version: 1
kind: seam
claim: derived
id: SEAM-JUIZO
name: Juízo do agregado
description: Separa a decisão de aceitar da produção do número.
evidence:
- E-ANCORA-202603
responsibility: Comparar agregado contra âncora e classificar toda diferença.
consumes:
- agregado da competência
- contrato validado
produces:
- veredito classificado
owner: juizo
independent_proof: Uma divergência de um centavo introduzida de propósito é recusada, e diferença não
  classificada bloqueia.
decision_ids:
- ADR-0001-HALF-EVEN
- ADR-0002-ANCORA-2026-03
rejected_alternatives:
- alternative: Aceitar diferença abaixo de um limite configurável
  reason: Tolerância configurável é como um centavo inexplicado vira um centavo aceito.
swimlane:
  id: LANE-JUIZO
  name: Juízo lane
  owner: juizo
  legs:
  - id: LEG-JUIZO-ACUSA-CENTAVO
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
---
# Juízo do agregado

Separa a decisão de aceitar da produção do número.

## Responsibility

Comparar agregado contra âncora e classificar toda diferença.

## Independent proof

Uma divergência de um centavo introduzida de propósito é recusada, e diferença não classificada bloqueia.

## Rejected alternatives

- **Aceitar diferença abaixo de um limite configurável** — Tolerância configurável é como um centavo inexplicado vira um centavo aceito.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
