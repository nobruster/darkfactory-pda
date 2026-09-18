---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-DESFECHO-SEMPRE-COM-PACOTE
seam_id: SEAM-ORQUESTRACAO
swimlane_id: LANE-ORQUESTRACAO
observable_state: Todo caminho termina com pacote e código de saída
proof: Os quatro desfechos (ACEITO, ACEITO_SEM_ANCORA, RECUSADO, ERRO) gravam pacote e saem com código
  distinto; o tempo é medido da leitura ao veredito, não por etapa.
requires:
- contrato validado
- veredito classificado
- pacote de evidência
produces:
- desfecho da execução
tasks:
- id: T-20260917-orquestra-desfecho
  title: Decidir o desfecho e garantir o pacote em todo caminho
  goal: Dar dono ao fluxo — sem ele a lacuna migra de costura em costura.
  done_condition: Os quatro desfechos gravam pacote e saem com código próprio; a execução completa é medida
    contra os 600s de R-6.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on:
  - T-20260917-evidencia-packet
  touches_paths: []
  creates_paths:
  - src/fabrica/orquestracao.py
  - tests/test_orquestracao.py
  behavior:
  - id: B-1
    given: execução sem âncora, execução ancorada que bate, e o ARQUIVO com uma linha corrompida em um
      centavo
    when: a orquestração conduz o fluxo inteiro e decide o desfecho
    then: as três gravam pacote — ACEITO_SEM_ANCORA com causa NAO_MEDIDO, ACEITO, e RECUSADO — com códigos
      de saída distintos; o centavo corrompido chega ao juízo e é recusado PONTA A PONTA, e só ACEITO
      autoriza publicar
  - id: B-2
    given: uma exceção REAL levantada dentro da leitura, e um caso em que a leitura cabe no limite mas
      o resto estoura
    when: a orquestração conduz a execução
    then: a exceção vira desfecho ERRO com pacote gravado — não escapa encerrando o processo; e R-6 reprova
      acima de 600s no TOTAL, etapa rápida com o resto lento não passa. Falha do próprio gravador é o
      único caso sem pacote, e sai com código distinto
  evals:
  - id: eval_1
    description: Os quatro desfechos gravam pacote com código de saída próprio
    bash: pytest -q tests/test_orquestracao.py -k desfechos
    verifies:
    - B-1
  - id: eval_2
    description: Exceção real vira ERRO com pacote; R-6 mede o total, não a etapa
    bash: pytest -q tests/test_orquestracao.py -k "excecao_vira_erro or tempo_total"
    verifies:
    - B-2
  - id: eval_3
    description: Só ACEITO autoriza publicar
    bash: pytest -q tests/test_orquestracao.py -k autoriza_publicar
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: encerrar o processo dentro de uma etapa
    reason: o pacote prometido nunca é gravado
    instead: retornar o veredito e deixar a orquestração decidir
  - action: medir o tempo por etapa
    reason: leitura em 530s mais o resto em 120s viola R-6 e passa
    instead: medir do início da leitura ao veredito
  - action: tratar ACEITO_SEM_ANCORA como autorização
    reason: a palavra aceito nomeia o término, não a prova
    instead: só ACEITO autoriza, e só com os cinco controles conferidos
  do_not_touch:
  - cvg/docs/adrs
  rollback: Remover a orquestração e seus testes.
  observability: desfechos por tipo e segundos da leitura ao veredito
source_seam_sha256: 3db2401a2e978fb76869d56194a739b4201cd57707a9ece22b756a231f21d065
---
# Todo caminho termina com pacote e código de saída

## Observable proof

Os quatro desfechos (ACEITO, ACEITO_SEM_ANCORA, RECUSADO, ERRO) gravam pacote e saem com código distinto; o tempo é medido da leitura ao veredito, não por etapa.

## Runnable leaves

- `T-20260917-orquestra-desfecho` — Decidir o desfecho e garantir o pacote em todo caminho: Os quatro desfechos gravam pacote e saem com código próprio; a execução completa é medida contra os 600s de R-6.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
