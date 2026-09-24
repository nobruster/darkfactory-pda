---
schema_version: 1
kind: seam
claim: derived
id: SEAM-LIMPA-PREPARO
name: Limpeza do preparo — só depois da publicação conferida
description: Separa o estágio privado da evidência que fica.
evidence:
- E-ANCORA-202601
responsibility: Apagar o _preparo de uma execução só quando a tabela publicada tem o commit dessa execução,
  e nunca nada fora do prefixo do preparo dela.
consumes:
- gold principal publicada
produces:
- preparo limpo
owner: medalhao
independent_proof: Com a publicação real conferida, o preparo da execução some e as tabelas publicadas
  ficam com o mesmo tamanho e a mesma soma.
decision_ids:
- DEC-PREPARO-APAGADO-APOS-CONFERIR
rejected_alternatives:
- alternative: Apagar todo o _preparo de uma vez
  reason: Apagaria o estágio de uma execução ainda em curso.
swimlane:
  id: LANE-LIMPA-PREPARO
  name: Limpeza do preparo lane
  owner: medalhao
  legs:
  - id: LEG-LIMPA-PREPARO
    observable_state: Nenhum preparo de execução publicada e conferida sobrevive
    proof: Só apaga com o commit da execução no histórico; nunca fora do prefixo dela.
    requires:
    - gold principal publicada
    produces:
    - preparo limpo
    tasks:
    - id: T-20260923-limpa-preparo
      title: Apagar o preparo de execuções publicadas e conferidas
      goal: Não deixar o estágio privado ocupar o armazenamento.
      done_condition: Para cada camada, o preparo de uma execução é apagado só se o histórico da tabela
        publicada tem o commit daquela execução; qualquer outro caso preserva o preparo e diz por quê.
      effort: S
      profile: standard
      execution_backend: any
      required_tools:
      - git
      - bash
      - python3
      - pytest
      - docker
      depends_on:
      - T-20260923-gold-le-silver
      touches_paths: []
      creates_paths:
      - src/medalhao/limpeza.py
      - tests/test_limpeza.py
      behavior:
      - id: B-1
        given: o preparo de uma execução cujo commit está no histórico da tabela publicada
        when: a limpeza roda para a camada e a execução
        then: confere que o ÚLTIMO commit que nomeia a competência no userMetadata é o dessa execução,
          com estado de publicação e NÃO de reversão — um commit revertido ou seguido de outro não é publicação
          conferida —, apaga SÓ o prefixo <camada>/_preparo/.../execucao=<id> — um caminho montado de
          partes validadas, recusado se vier vazio ou fora de _preparo —, e confere depois que a tabela
          publicada mantém a mesma versão, a mesma contagem e a mesma soma.
      - id: B-2
        given: uma execução sem commit no histórico, um id vazio ou um caminho fora do preparo
        when: a limpeza roda
        then: 'não apaga nada e devolve o motivo: execução não publicada preserva o preparo; id vazio
          ou caminho fora de _preparo é RECUSADO antes de qualquer remoção, porque um prefixo vazio já
          montou uma vez o caminho do bucket inteiro.'
      evals:
      - id: eval_1
        description: Apaga só o preparo conferido
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in apaga_preparo_de_execucao_publicada
          publicada_intacta_depois; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c"
          2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m
          pytest -q tests/test_limpeza.py -k "apaga_preparo_de_execucao_publicada or publicada_intacta_depois"'
        verifies:
        - B-1
      - id: eval_2
        description: Guarda de caminho
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in id_vazio_recusado
          caminho_fora_do_preparo_recusado execucao_nao_publicada_preserva commit_revertido_preserva;
          do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::"
          || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py
          -k "id_vazio_recusado or caminho_fora_do_preparo_recusado or execucao_nao_publicada_preserva
          or commit_revertido_preserva"'
        verifies:
        - B-2
      - id: eval_3
        description: Nada além do prefixo da execução
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in outra_execucao_intacta
          prefixo_montado_de_partes_validadas; do python3 -m pytest --collect-only -q tests/test_limpeza.py
          -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
          -m pytest -q tests/test_limpeza.py -k "outra_execucao_intacta or prefixo_montado_de_partes_validadas"'
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: montar o caminho a apagar com variável não validada
        reason: um valor vazio vira o bucket inteiro
        instead: validar cada parte e exigir o prefixo _preparo/…/execucao=<id>
      - action: apagar preparo de execução sem commit publicado
        reason: pode ser uma execução ainda em curso
        instead: exigir o commit da execução no histórico
      - action: usar VACUUM para liberar espaço
        reason: VACUUM apaga histórico, que é evidência
        instead: apagar só o preparo, que não é histórico de tabela publicada
      do_not_touch:
      - _raw
      - cvg/docs/adrs
      - contracts
      rollback: Remover limpeza.py e seu teste; o preparo apagado é regenerável rodando a camada.
      observability: preparos de execuções já publicadas
---
# Limpeza do preparo — só depois da publicação conferida

Separa o estágio privado da evidência que fica.

## Responsibility

Apagar o _preparo de uma execução só quando a tabela publicada tem o commit dessa execução, e nunca nada fora do prefixo do preparo dela.

## Independent proof

Com a publicação real conferida, o preparo da execução some e as tabelas publicadas ficam com o mesmo tamanho e a mesma soma.

## Rejected alternatives

- **Apagar todo o _preparo de uma vez** — Apagaria o estágio de uma execução ainda em curso.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
