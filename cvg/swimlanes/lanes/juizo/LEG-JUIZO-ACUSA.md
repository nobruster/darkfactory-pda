> Projetado de `LEG-JUIZO-ACUSA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `722432f019464c94f280bb65d9705050119ceef9fda4b7c268a0eb8a55d291e7`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-JUIZO-ACUSA
seam_id: SEAM-JUIZO
swimlane_id: LANE-JUIZO
observable_state: O juiz recusa divergência em qualquer controle
proof: Agregado com uma linha a menos é recusado; controle divergente classificado como CONFIRMED também
  recusa.
requires:
- envelope do produtor
- contrato validado
produces:
- veredito classificado
tasks:
- id: T-20260921-juizo-classifica
  title: Comparar os cinco controles e classificar a diferença
  goal: Fazer o juiz acusar, não apenas aprovar.
  done_condition: Os cinco controles comparados individualmente; divergência recusa mesmo classificada;
    defeito sem classificação bloqueia.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on:
  - T-20260921-envelope-fronteira
  touches_paths: []
  creates_paths:
  - src/pda/juizo.py
  - tests/test_juizo.py
  behavior:
  - id: B-1
    given: um agregado com uma linha a menos, e outro que redistribui valores mantendo soma e contagem
    when: o juízo compara contra a âncora
    then: os cinco controles são comparados individualmente e qualquer divergência recusa — soma e contagem
      iguais não bastam
  - id: B-2
    given: uma diferença de cada uma das seis classificações, incluindo um controle divergente marcado
      CONFIRMED
    when: o veredito é calculado
    then: divergência em qualquer controle RECUSA mesmo classificada; fora dos controles, MODERN_DEFECT,
      CONTRACT_AMBIGUITY e UNRESOLVED bloqueiam e as três CONFIRMED/APPROVED apenas registram
  evals:
  - id: eval_1
    description: Linha a menos recusa; extremos alterados com soma igual também
    bash: pytest -q tests/test_juizo.py -k "linha_a_menos or cinco_controles"
    verifies:
    - B-1
  - id: eval_2
    description: Precedência — controle divergente recusa mesmo classificado
    bash: pytest -q tests/test_juizo.py -k precedencia
    verifies:
    - B-2
  - id: eval_3
    description: Defeito observado sem classificação bloqueia
    bash: pytest -q tests/test_juizo.py -k defeito_sem_classe
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
  - action: deixar a classificação autorizar publicação
    reason: CONFIRMED explica a diferença, não a aprova
    instead: divergência em controle recusa, classificada ou não
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  rollback: Remover o juízo e seus testes.
  observability: vereditos por classificação
source_seam_sha256: 34b0096968f0bf7b9b48e9e9f90bb76ccf82f7bcf6cf9477c6999292558627dc
---
# O juiz recusa divergência em qualquer controle

## Observable proof

Agregado com uma linha a menos é recusado; controle divergente classificado como CONFIRMED também recusa.

## Runnable leaves

- `T-20260921-juizo-classifica` — Comparar os cinco controles e classificar a diferença: Os cinco controles comparados individualmente; divergência recusa mesmo classificada; defeito sem classificação bloqueia.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
