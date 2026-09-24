---
schema_version: 1
kind: seam
claim: derived
id: SEAM-PERF-GOLD
name: Performance da Gold e dos assuntos
description: Liberar o cache e reduzir os commits de constraint, sem mudar a saída.
evidence:
- E-ANCORA-202601
responsibility: Liberar o cache e reduzir os commits de constraint, sem mudar a saída.
consumes:
- bronze e silver performaticas
produces: &id001
- gold performatica
owner: medalhao
independent_proof: Sobre o dado real, a Gold e os assuntos saem idênticos à produção, com menos commits
  e PERF=MELHOR.
decision_ids:
- DEC-PERFORMANCE-MEDIDA
- DEC-CAMADAS-EM-DELTA
rejected_alternatives:
- alternative: Tirar o CHECK das colunas monetárias
  reason: O CHECK é o domínio da ADR 0009; o que se reduz é o número de commits, não a proteção.
swimlane:
  id: LANE-PERF-GOLD
  name: Performance da Gold e dos assuntos lane
  owner: medalhao
  legs:
  - id: LEG-PERF-GOLD
    observable_state: Gold e assuntos com menos commits e a mesma saída
    proof: PERF=MELHOR com resultado idêntico.
    requires:
    - bronze e silver performaticas
    produces: *id001
    tasks:
    - id: T-20260924-perf-gold
      title: Cache liberado e constraints num commit só na Gold
      goal: Baixar o custo da Gold e dos assuntos sem mudar a saída.
      done_condition: 'A Gold e os assuntos reais saem idênticos à produção. O PERF=MELHOR contra perf/
        é VERIFICAÇÃO PÓS-ASSENTAMENTO: roda na execução real com a skill spark-perf, fora do loop, porque
        tempo medido dentro de eval é instável; a entrega exige saída idêntica e o comportamento declarado.'
      effort: M
      profile: standard
      execution_backend: any
      required_tools:
      - git
      - bash
      - python3
      - pytest
      - docker
      depends_on:
      - T-20260924-perf-bronze-silver
      touches_paths:
      - src/medalhao/gold.py
      - src/medalhao/gold_assuntos.py
      creates_paths:
      - tests/test_performance_gold.py
      behavior:
      - id: B-1
        given: a Gold principal e os assuntos publicando a competência
        when: rodam
        then: 'todo DataFrame persistido é liberado com unpersist num finally, em TODOS os caminhos —
          publicado, divergente, CHECK que recusou ou exceção de escrita —, e nunca antes da reconferência;
          uma tabela NOVA de assuntos nasce com as colunas monetárias protegidas por UM CHECK que exige
          todas >= 0 — um commit em vez de seis —, e uma tabela que já existe com os seis CHECK é reconhecida
          como protegida, sem receber constraint nova nem perder as antigas; a reconferência passa a uma
          passada como na Bronze. O ganho só vale com o gate da skill spark-perf: PERF=MELHOR contra a
          baseline gravada em perf/, com a saída IDÊNTICA à de produção — controles e multiconjunto 0/0.
          Otimização que muda o número é defeito, não ganho; nenhuma reconferência é removida, só barateada.'
      - id: B-2
        given: uma saída com valor monetário negativo ou uma linha trocada
        when: a publicação roda
        then: o CHECK único recusa o negativo como os seis recusavam, e a reconferência numa passada devolve
          DIVERGE; nada é publicado; nenhum teste já existente de tests/test_gold.py ou tests/test_gold_assuntos.py
          é editado.
      evals:
      - id: eval_1
        description: Cache liberado e um CHECK só
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_unpersist_depois_de_publicar
          check_unico_no_create tabela_com_seis_check_reconhecida gold_unpersist_tambem_na_falha; do python3
          -m pytest --collect-only -q tests/test_performance_gold.py -k "$c" 2>/dev/null | grep -q "::"
          || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_performance_gold.py
          -k "gold_unpersist_depois_de_publicar or check_unico_no_create or tabela_com_seis_check_reconhecida
          or gold_unpersist_tambem_na_falha"'
        verifies:
        - B-1
      - id: eval_2
        description: A proteção é a mesma
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in check_unico_recusa_negativo
          gold_uma_passada_diverge_linha_trocada; do python3 -m pytest --collect-only -q tests/test_performance_gold.py
          -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
          -m pytest -q tests/test_performance_gold.py -k "check_unico_recusa_negativo or gold_uma_passada_diverge_linha_trocada"'
        verifies:
        - B-2
      - id: eval_3
        description: Nada do comportamento selado mudou
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in check_nao_negativo_monetario
          fat_especie_fecha_com_a_ancora publica_com_replacewhere; do python3 -m pytest --collect-only
          -q tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
          exit 1; }; done; python3 -m pytest -q tests/test_gold_assuntos.py -k "check_nao_negativo_monetario
          or fat_especie_fecha_com_a_ancora or publica_com_replacewhere"'
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: tirar o CHECK monetário
        reason: é o domínio da ADR 0009
        instead: um CHECK combinado
      - action: dropar os seis CHECK de uma tabela existente
        reason: desproteger para trocar é janela sem domínio
        instead: reconhecer os seis como proteção equivalente
      - action: unpersist antes da reconferência
        reason: releria a origem
        instead: liberar depois de publicado e reconferido
      do_not_touch:
      - _raw
      - cvg/docs/adrs
      - contracts
      - src/pda
      - src/medalhao/bronze.py
      - src/medalhao/silver.py
      rollback: Reverter os arquivos tocados ao commit assentado; remover os criados.
      observability: execuções com memória herdada ou cache não liberado
---
# Performance da Gold e dos assuntos

Liberar o cache e reduzir os commits de constraint, sem mudar a saída.

## Responsibility

Liberar o cache e reduzir os commits de constraint, sem mudar a saída.

## Independent proof

Sobre o dado real, a Gold e os assuntos saem idênticos à produção, com menos commits e PERF=MELHOR.

## Rejected alternatives

- **Tirar o CHECK das colunas monetárias** — O CHECK é o domínio da ADR 0009; o que se reduz é o número de commits, não a proteção.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
