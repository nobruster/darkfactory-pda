---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-DESFECHO-COM-PACOTE
seam_id: SEAM-ORQUESTRACAO
swimlane_id: LANE-ORQUESTRACAO
observable_state: Todo caminho termina com pacote e código de saída
proof: Os quatro desfechos gravam pacote; uma exceção dentro da leitura vira ERRO com pacote; o tempo
  é medido do início ao veredito.
requires:
- contrato validado
- veredito classificado
- pacote de evidência
produces:
- desfecho da execução
tasks:
- id: T-20260921-orquestra-desfecho
  title: Decidir o desfecho e garantir o pacote em todo caminho
  goal: Dar dono ao fluxo — sem ele a lacuna migra de etapa em etapa.
  done_condition: Os quatro desfechos gravam pacote com código próprio; exceção real vira ERRO; o tempo
    total é medido contra R-9.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on:
  - T-20260921-evidencia-packet
  touches_paths: []
  creates_paths:
  - src/pda/orquestracao.py
  - tests/test_orquestracao.py
  behavior:
  - id: B-1
    given: execução sem âncora, execução que bate, e o arquivo com uma linha removida
    when: a orquestração conduz o fluxo inteiro
    then: as três gravam pacote — ACEITO_SEM_ANCORA, ACEITO e RECUSADO — com códigos de saída distintos,
      e só ACEITO autoriza publicar
  - id: B-2
    given: uma exceção real levantada dentro da leitura, e uma execução que estoura o limite de tempo
    when: a orquestração conduz a execução
    then: a exceção vira ERRO com pacote gravado, e o tempo é medido do início da leitura ao veredito,
      no total — nunca por etapa somada depois
  evals:
  - id: eval_1
    description: Os quatro desfechos gravam pacote com código próprio
    bash: pytest -q tests/test_orquestracao.py -k desfechos
    verifies:
    - B-1
  - id: eval_2
    description: Exceção real vira ERRO; o tempo é medido no total
    bash: pytest -q tests/test_orquestracao.py -k "excecao or tempo_total"
    verifies:
    - B-2
  - id: eval_3
    description: Só ACEITO autoriza publicar
    bash: pytest -q tests/test_orquestracao.py -k autoriza
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: encerrar o processo dentro de uma etapa
    reason: o pacote prometido nunca é gravado
    instead: retornar o veredito e deixar a orquestração decidir
  - action: medir o tempo por etapa
    reason: etapa rápida com o resto lento passaria
    instead: medir do início da leitura ao veredito
  - action: tratar ACEITO_SEM_ANCORA como autorização
    reason: a palavra aceito nomeia o término, não a prova
    instead: só ACEITO autoriza, com os cinco controles conferidos
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  rollback: Remover a orquestração e seus testes.
  observability: desfechos por tipo e segundos até o veredito
source_seam_sha256: 6f0228fa48afe590208c2fd0d9eb4a441ea3f51b5b74600bca86d34119fed18a
---
# Todo caminho termina com pacote e código de saída

## Observable proof

Os quatro desfechos gravam pacote; uma exceção dentro da leitura vira ERRO com pacote; o tempo é medido do início ao veredito.

## Runnable leaves

- `T-20260921-orquestra-desfecho` — Decidir o desfecho e garantir o pacote em todo caminho: Os quatro desfechos gravam pacote com código próprio; exceção real vira ERRO; o tempo total é medido contra R-9.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
