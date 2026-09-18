> Projetado de `LEG-JUIZO-ACUSA-CENTAVO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `3913e6e461cd82edd7d2bb010d273fd59e107d763c15725878d56c2da23d1dd3`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-JUIZO-ACUSA-CENTAVO
seam_id: SEAM-JUIZO
swimlane_id: LANE-JUIZO
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
    then: os CINCO controles são comparados individualmente (count_linhas, sum_vl_liquido, min, max, linhas_invalidas)
      e qualquer divergência recusa — soma e contagem iguais não bastam
  - id: B-2
    given: uma diferença de cada uma das seis classificações, incluindo um controle divergente classificado
      como CONFIRMED_SOURCE_DEFECT, e o mesmo dado agregado com meio-para-cima
    when: o veredito é calculado
    then: PRECEDÊNCIA — divergência em qualquer dos cinco controles RECUSA, mesmo classificada como CONFIRMED
      ou APPROVED; a classificação explica, nunca autoriza. Fora dos controles, MODERN_DEFECT, CONTRACT_AMBIGUITY
      e UNRESOLVED bloqueiam e as três CONFIRMED/APPROVED apenas registram. E o arredondamento errado
      muda o VEREDITO, não só o total
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
    description: As seis são exaustivas e exclusivas
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
source_seam_sha256: c591e98509ba64835843b55ac4e8064bda64a9a3fd8fe5f1fbd0b5907ec5849a
---
# O juiz recusa um centavo de divergência

## Observable proof

Teste que corrompe UMA LINHA do arquivo em um centavo e roda o pipeline de ponta a ponta exige recusa. Partir de um agregado já alterado não serve: passaria mesmo se a leitura descartasse a linha ou a agregação anulasse a diferença (objeção C6).

## Runnable leaves

- `T-20260917-juizo-classifica` — Comparar contra a âncora e classificar a diferença: Um centavo alterado é recusado, e diferença sem classificação bloqueia a publicação.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
