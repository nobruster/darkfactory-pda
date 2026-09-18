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
    proof: Um agregado derivado de arquivo com UMA LINHA corrompida em um centavo exige recusa, e a diferença
      é comparada controle a controle. A prova PONTA A PONTA — corromper o arquivo e rodar o fluxo inteiro
      — pertence à orquestração, que é quem o possui (objeções C6 e C44).
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
        given: um agregado derivado de arquivo com UMA LINHA corrompida em um centavo, e outro que redistribui
          valores mantendo soma e contagem
        when: o juízo compara contra a âncora
        then: os CINCO controles são comparados individualmente (count_linhas, sum_vl_liquido, min_vl_liquido,
          max_vl_liquido, linhas_invalidas) e qualquer divergência recusa — soma e contagem iguais não
          bastam
      - id: B-2
        given: uma diferença de cada uma das seis classificações, incluindo um controle divergente classificado
          como CONFIRMED_SOURCE_DEFECT, e o mesmo dado agregado com meio-para-cima
        when: o veredito é calculado
        then: PRECEDÊNCIA — divergência em qualquer dos cinco controles RECUSA, mesmo classificada como
          CONFIRMED ou APPROVED; a classificação explica, nunca autoriza. Fora dos controles, MODERN_DEFECT,
          CONTRACT_AMBIGUITY e UNRESOLVED bloqueiam e as três CONFIRMED/APPROVED apenas registram. E o
          arredondamento errado muda o VEREDITO, não só o total
      evals:
      - id: eval_1
        description: Um centavo na linha recusa; extremos alterados com soma igual também
        bash: pytest -q tests/test_juizo.py -k "um_centavo_na_linha or cinco_controles"
        verifies:
        - B-1
      - id: eval_2
        description: Cada uma das seis decide publicar ou bloquear; arredondamento muda o veredito
        bash: pytest -q tests/test_juizo.py -k "politica_por_classificacao or arredondamento_muda_veredito"
        verifies:
        - B-2
      - id: eval_3
        description: Defeito observado sem classificação bloqueia; nenhum é ignorado
        bash: pytest -q tests/test_juizo.py -k "classificacoes or defeito_sem_classe"
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
