---
schema_version: 1
kind: seam
claim: derived
id: SEAM-ORQUESTRACAO
name: Orquestração da execução
description: Separa quem decide o desfecho de quem produz cada parte.
evidence:
- E-ANCORA-202601
responsibility: Encadear as etapas, decidir o veredito terminal e o código de saída, e garantir pacote
  em todo caminho.
consumes:
- contrato validado
- veredito classificado
- pacote de evidência
produces:
- desfecho da execução
owner: orquestracao
independent_proof: Os quatro desfechos terminam com pacote e código distintos, e uma exceção real vira
  ERRO com pacote.
decision_ids:
- ADR-0003-HALF-EVEN
rejected_alternatives:
- alternative: Deixar cada etapa encerrar o processo
  reason: O contrato sairia antes da leitura e o pacote prometido nunca seria gravado; encerrar é decisão
    de fluxo, não de etapa.
swimlane:
  id: LANE-ORQUESTRACAO
  name: Orquestração lane
  owner: orquestracao
  legs:
  - id: LEG-DESFECHO-COM-PACOTE
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
      done_condition: Os quatro desfechos gravam pacote com código próprio; exceção real vira ERRO; o
        tempo total é medido contra R-9.
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
        given: execução sem âncora, execução que bate, e DUAS execuções que devem recusar — a do arquivo
          com um centavo alterado nos bytes, que R-7 exige, e a do arquivo íntegro em que o agregador
          divergiu de um controle
        when: a orquestração conduz o fluxo inteiro
        then: as quatro gravam pacote, com ACEITO_SEM_ANCORA, ACEITO e dois RECUSADO de códigos de saída
          distintos, e só ACEITO autoriza publicar. Os dois casos de recusa provam coisas diferentes e
          nenhum substitui o outro — o do centavo alterado prova que uma mudança real nos bytes atravessa
          o fluxo até a recusa sem publicar, ainda que recusada pela fronteira via sha256; o do arquivo
          íntegro prova que o JUÍZO é chamado e respeitado, porque o teste falha se um juízo permissivo
          for injetado
      - id: B-2
        given: uma exceção real levantada dentro da leitura, e uma execução que estoura o limite de tempo
        when: a orquestração conduz a execução
        then: a exceção vira ERRO com pacote gravado, e o tempo é medido do início da leitura ao veredito,
          no total. Se o PRÓPRIO gravador falhar — permissão negada, disco cheio — o desfecho é ERRO com
          código próprio e a falha vai para a saída de erro; nunca se devolve ACEITO sem pacote, porque
          autorização sem evidência é o que esta fábrica existe para impedir
      evals:
      - id: eval_1
        description: Desfechos gravam pacote; centavo alterado recusa e juízo permissivo faz falhar
        bash: pytest -q tests/test_orquestracao.py -k "desfechos or centavo_alterado or juizo_permissivo_falha"
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
---
# Orquestração da execução

Separa quem decide o desfecho de quem produz cada parte.

## Responsibility

Encadear as etapas, decidir o veredito terminal e o código de saída, e garantir pacote em todo caminho.

## Independent proof

Os quatro desfechos terminam com pacote e código distintos, e uma exceção real vira ERRO com pacote.

## Rejected alternatives

- **Deixar cada etapa encerrar o processo** — O contrato sairia antes da leitura e o pacote prometido nunca seria gravado; encerrar é decisão de fluxo, não de etapa.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
