---
schema_version: 1
kind: seam
claim: derived
id: SEAM-ORQUESTRACAO
name: Orquestração da execução
description: Separa quem decide o desfecho de quem produz cada parte. Nenhuma das cinco costuras possuía
  o fluxo, e a lacuna migrava de vizinho em vizinho a cada correção (objeções C11, C14, C16, C17, C19).
evidence:
- E-ANCORA-202603
responsibility: Encadear as etapas, decidir o veredito terminal e o código de saída, e garantir que TODO
  caminho termina com pacote gravado.
consumes:
- contrato validado
- veredito classificado
- pacote de evidência
produces:
- desfecho da execução
owner: orquestracao
independent_proof: Os quatro desfechos terminam com pacote e código de saída distintos, e a execução completa
  cabe em 600 segundos — a etapa rápida com o resto lento não passa.
decision_ids:
- ADR-0005-VEREDITO-SEM-ANCORA
rejected_alternatives:
- alternative: Deixar cada etapa encerrar o processo por conta própria
  reason: 'Foi o que se tentou: o contrato saía com exit 1 antes da leitura, e o pacote prometido pela
    evidência nunca era gravado. Encerrar é decisão de fluxo, não de etapa.'
swimlane:
  id: LANE-ORQUESTRACAO
  name: Orquestração lane
  owner: orquestracao
  legs:
  - id: LEG-DESFECHO-SEMPRE-COM-PACOTE
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
      done_condition: Os quatro desfechos gravam pacote e saem com código próprio; a execução completa
        é medida contra os 600s de R-6.
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
        given: execução sem âncora, execução ancorada que bate, e execução ancorada com divergência bloqueante
        when: a orquestração decide o desfecho
        then: as três gravam pacote — ACEITO_SEM_ANCORA com causa NAO_MEDIDO, ACEITO, e RECUSADO — com
          códigos de saída distintos, e só ACEITO autoriza publicar
      - id: B-2
        given: uma exceção REAL levantada dentro da leitura, e um caso em que a leitura cabe no limite
          mas o resto estoura
        when: a orquestração conduz a execução
        then: a exceção vira desfecho ERRO com pacote gravado — não escapa encerrando o processo; e R-6
          reprova acima de 600s no TOTAL, etapa rápida com o resto lento não passa. Falha do próprio gravador
          é o único caso sem pacote, e sai com código distinto
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
---
# Orquestração da execução

Separa quem decide o desfecho de quem produz cada parte. Nenhuma das cinco costuras possuía o fluxo, e a lacuna migrava de vizinho em vizinho a cada correção (objeções C11, C14, C16, C17, C19).

## Responsibility

Encadear as etapas, decidir o veredito terminal e o código de saída, e garantir que TODO caminho termina com pacote gravado.

## Independent proof

Os quatro desfechos terminam com pacote e código de saída distintos, e a execução completa cabe em 600 segundos — a etapa rápida com o resto lento não passa.

## Rejected alternatives

- **Deixar cada etapa encerrar o processo por conta própria** — Foi o que se tentou: o contrato saía com exit 1 antes da leitura, e o pacote prometido pela evidência nunca era gravado. Encerrar é decisão de fluxo, não de etapa.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
