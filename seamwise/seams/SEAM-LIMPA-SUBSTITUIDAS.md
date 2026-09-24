---
schema_version: 1
kind: seam
claim: derived
id: SEAM-LIMPA-SUBSTITUIDAS
name: Limpeza do preparo de execuções substituídas
description: Apagar também o preparo de execuções substituídas cuja publicação foi conferida, com a mesma
  guarda.
evidence:
- E-ANCORA-202601
responsibility: Apagar também o preparo de execuções substituídas cuja publicação foi conferida, com a
  mesma guarda.
consumes:
- testes leves
produces: &id001
- preparo sem sobras
owner: medalhao
independent_proof: O preparo de uma execução substituída sai; o de uma execução revertida ou em curso
  fica.
decision_ids:
- DEC-PREPARO-APAGADO-APOS-CONFERIR
rejected_alternatives:
- alternative: Apagar todo o _preparo
  reason: Apagaria o estágio de uma execução em curso.
swimlane:
  id: LANE-LIMPA-SUBSTITUIDAS
  name: Limpeza do preparo de execuções substituídas lane
  owner: medalhao
  legs:
  - id: LEG-LIMPA-SUBSTITUIDAS
    observable_state: Nenhum preparo de execução conferida sobrevive
    proof: Substituída e conferida sai; revertida ou em curso fica.
    requires:
    - testes leves
    produces: *id001
    tasks:
    - id: T-20260924-limpa-substituidas
      title: Limpar o preparo de execuções substituídas
      goal: Não deixar sobras de execuções antigas. Para rodar testes, o ÚNICO comando liberado ao agente
        é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`
        — outras formas são recusadas pela permissão.
      done_condition: O preparo de execução substituída cuja publicação foi conferida é apagado; revertida,
        em curso ou sem commit fica.
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
      - T-20260924-testes-leves
      touches_paths:
      - src/medalhao/limpeza.py
      - tests/test_limpeza.py
      creates_paths: []
      behavior:
      - id: B-1
        given: o preparo de uma execução cujo commit de publicação está no histórico e foi SUBSTITUÍDO
          por outro posterior
        when: a limpeza roda
        then: 'apaga o preparo dessa execução se o commit dela tem estado INTEGRO, NÃO é de reversão e
          nenhum commit de reversão a desfez — publicação conferida e depois substituída —, com a mesma
          guarda de caminho — sob a INVARIANTE declarada de que execução não é retomada: cada execução
          nasce com id novo e nunca reusa o preparo de outra, então um preparo cuja execução já tem commit
          publicado e foi substituída não está em uso —; a tabela publicada segue com a mesma versão,
          contagem e soma.'
      - id: B-2
        given: uma execução revertida, uma sem commit, ou um caminho fora do preparo
        when: a limpeza roda
        then: preserva o preparo e diz o motivo — inclusive o da execução ATIVA, que ainda não tem commit;
          caminho fora de _preparo ou id vazio é RECUSADO antes de qualquer remoção; nenhum teste já existente
          de tests/test_limpeza.py é editado.
      evals:
      - id: eval_1
        description: Substituída e conferida sai
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in substituida_conferida_apaga
          publicada_intacta_apos_limpar_substituida; do python3 -m pytest --collect-only -q tests/test_limpeza.py
          -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
          -m pytest -q tests/test_limpeza.py -k "substituida_conferida_apaga or publicada_intacta_apos_limpar_substituida"'
        verifies:
        - B-1
      - id: eval_2
        description: Revertida e em curso ficam
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in revertida_preserva
          sem_commit_preserva id_vazio_recusado execucao_ativa_preserva; do python3 -m pytest --collect-only
          -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
          exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "revertida_preserva or sem_commit_preserva
          or id_vazio_recusado or execucao_ativa_preserva"'
        verifies:
        - B-2
      - id: eval_3
        description: O comportamento selado segue
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in apaga_preparo_de_execucao_publicada
          caminho_fora_do_preparo_recusado; do python3 -m pytest --collect-only -q tests/test_limpeza.py
          -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
          -m pytest -q tests/test_limpeza.py -k "apaga_preparo_de_execucao_publicada or caminho_fora_do_preparo_recusado"'
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: apagar preparo de execução revertida
        reason: é evidência de uma divergência
        instead: preservar
      - action: montar o caminho com variável não validada
        reason: um valor vazio vira o bucket
        instead: montar_prefixo com partes validadas
      - action: usar VACUUM
        reason: apaga histórico, que é evidência
        instead: apagar só o preparo
      do_not_touch:
      - _raw
      - cvg/docs/adrs
      - contracts
      - src/pda
      rollback: Reverter os arquivos tocados ao commit assentado; remover os criados.
      observability: execuções com memória herdada ou cache não liberado
---
# Limpeza do preparo de execuções substituídas

Apagar também o preparo de execuções substituídas cuja publicação foi conferida, com a mesma guarda.

## Responsibility

Apagar também o preparo de execuções substituídas cuja publicação foi conferida, com a mesma guarda.

## Independent proof

O preparo de uma execução substituída sai; o de uma execução revertida ou em curso fica.

## Rejected alternatives

- **Apagar todo o _preparo** — Apagaria o estágio de uma execução em curso.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
