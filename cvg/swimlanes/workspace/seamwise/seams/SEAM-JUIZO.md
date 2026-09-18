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
- defeitos observados
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
    proof: 'Teste que corrompe UMA LINHA do arquivo em um centavo e roda o pipeline de ponta a ponta exige
      recusa. Partir de um agregado já alterado não serve: passaria mesmo se a leitura descartasse a linha
      ou a agregação anulasse a diferença (objeção C6).'
    requires:
    - agregado da competência
    - contrato validado
    - defeitos observados
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
        given: o arquivo da competência com UMA LINHA corrompida, e um caso que redistribui valores mantendo
          soma e contagem
        when: o pipeline roda de ponta a ponta e o juízo compara contra a âncora
        then: os CINCO controles são comparados individualmente (count_linhas, sum_vl_liquido, min, max,
          linhas_invalidas) e qualquer divergência recusa — soma e contagem iguais não bastam
      - id: B-2
        given: uma diferença sem classificação, e o mesmo dado agregado com meio-para-cima em vez de meio-para-par
        when: o veredito é calculado
        then: a primeira é UNRESOLVED e bloqueia; a segunda produz VEREDITO diferente — total diferente
          não basta, o juízo poderia re-arredondar e anular
      evals:
      - id: eval_1
        description: Um centavo na linha recusa; extremos alterados com soma igual também
        bash: pytest -q tests/test_juizo.py -k "um_centavo_na_linha or cinco_controles"
        verifies:
        - B-1
      - id: eval_2
        description: Diferença não classificada bloqueia; arredondamento errado muda o veredito
        bash: pytest -q tests/test_juizo.py -k "unresolved or arredondamento_muda_veredito"
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
