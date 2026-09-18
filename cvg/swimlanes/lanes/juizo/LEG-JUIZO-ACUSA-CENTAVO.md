> Projetado de `LEG-JUIZO-ACUSA-CENTAVO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `391f610ab2763b22c131de3eada8ded3d43b0aa6909e27d847b3180cd60ee902`

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
    given: o arquivo da competência com UMA LINHA corrompida em um centavo
    when: o pipeline roda de ponta a ponta e o juízo compara contra a âncora
    then: o veredito é recusado e o processo sai com código 1
  - id: B-2
    given: uma diferença sem classificação, e o mesmo dado agregado com meio-para-cima em vez de meio-para-par
    when: o veredito é calculado
    then: a primeira é UNRESOLVED e bloqueia; a segunda produz VEREDITO diferente — total diferente não
      basta, o juízo poderia re-arredondar e anular
  evals:
  - id: eval_1
    description: Um centavo corrompido NA LINHA é recusado ponta a ponta
    bash: pytest -q tests/test_juizo.py -k um_centavo_na_linha
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
source_seam_sha256: ed493cacf515e84d9c5c1000b9183342c87d634f45175695f03a712eff6fab87
---
# O juiz recusa um centavo de divergência

## Observable proof

Teste que corrompe UMA LINHA do arquivo em um centavo e roda o pipeline de ponta a ponta exige recusa. Partir de um agregado já alterado não serve: passaria mesmo se a leitura descartasse a linha ou a agregação anulasse a diferença (objeção C6).

## Runnable leaves

- `T-20260917-juizo-classifica` — Comparar contra a âncora e classificar a diferença: Um centavo alterado é recusado, e diferença sem classificação bloqueia a publicação.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
