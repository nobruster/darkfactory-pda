---
schema_version: 1
kind: seam
claim: derived
id: SEAM-PERF-BRONZE-SILVER
name: Performance da Bronze e da Silver
description: Declarar a memória da sessão, liberar o cache e reconferir numa passada, sem mudar a saída.
evidence:
- E-ANCORA-202601
responsibility: Declarar a memória da sessão, liberar o cache e reconferir numa passada, sem mudar a saída.
consumes:
- bronze julgada
produces: &id001
- bronze e silver performaticas
owner: medalhao
independent_proof: Sobre o dado real, Bronze e Silver saem com controles e multiconjunto idênticos à produção
  e PERF=MELHOR.
decision_ids:
- DEC-PERFORMANCE-MEDIDA
- DEC-CAMADAS-EM-DELTA
rejected_alternatives:
- alternative: Remover um dos exceptAll da reconferência
  reason: Tirar a prova para ganhar tempo é o que o guardião proíbe; a passada única prova o mesmo.
swimlane:
  id: LANE-PERF-BRONZE-SILVER
  name: Performance da Bronze e da Silver lane
  owner: medalhao
  legs:
  - id: LEG-PERF-BRONZE-SILVER
    observable_state: Bronze e Silver mais rápidas com a mesma saída
    proof: PERF=MELHOR com resultado idêntico.
    requires: []
    produces: *id001
    tasks:
    - id: T-20260924-perf-bronze-silver
      title: Memória declarada, cache liberado e reconferência numa passada
      goal: Baixar executor, shuffle e spill da Bronze e da Silver sem mudar a saída.
      done_condition: 'Bronze e Silver reais saem idênticas à produção. O PERF=MELHOR contra perf/ é VERIFICAÇÃO
        PÓS-ASSENTAMENTO: roda na execução real com a skill spark-perf, fora do loop, porque tempo medido
        dentro de eval é instável; a entrega exige saída idêntica e o comportamento declarado.'
      effort: M
      profile: standard
      execution_backend: any
      required_tools:
      - git
      - bash
      - python3
      - pytest
      - docker
      depends_on: []
      touches_paths:
      - src/medalhao/bronze.py
      - src/medalhao/silver.py
      creates_paths:
      - tests/test_performance.py
      behavior:
      - id: B-1
        given: a sessão criada por criar_sessao e as leituras e gravações da Bronze e da Silver
        when: Bronze e Silver rodam
        then: 'criar_sessao DECLARA spark.driver.memory, spark.sql.adaptive.enabled e spark.sql.shuffle.partitions
          a partir de parâmetros com padrão explícito — nunca herda — e confere depois de criar o heap
          EFETIVO da JVM — Runtime.getRuntime().maxMemory() por spark._jvm, não a propriedade de configuração,
          que não prova nada numa JVM já iniciada —, recusando sessão cujo heap efetivo seja menor que
          o declarado; todo DataFrame persistido é liberado com unpersist num finally, em TODOS os caminhos
          — publicado, divergente, CHECK que recusou ou exceção de escrita —, e nunca antes da reconferência,
          inclusive no caminho INTEGRO; e a reconferência de _conferir_tabela passa a UMA passada: um
          exceptAll e a igualdade das contagens — multiconjuntos de mesmo tamanho em que um está contido
          no outro são iguais —, provando o mesmo que os dois exceptAll. O ganho só vale com o gate da
          skill spark-perf: PERF=MELHOR contra a baseline gravada em perf/, com a saída IDÊNTICA à de
          produção — controles e multiconjunto 0/0. Otimização que muda o número é defeito, não ganho;
          nenhuma reconferência é removida, só barateada.'
      - id: B-2
        given: uma saída alterada — linha trocada, centavo a mais ou linha a menos
        when: a reconferência numa passada roda
        then: 'acusa exatamente o que os dois exceptAll acusavam: DIVERGE com a diferença nomeada, e nada
          é publicado; nenhum teste já existente de tests/test_bronze.py ou tests/test_silver.py é editado.'
      evals:
      - id: eval_1
        description: Memória declarada e cache liberado
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sessao_declara_memoria
          sessao_com_memoria_herdada_recusada unpersist_depois_de_publicar heap_efetivo_conferido_pela_jvm
          unpersist_tambem_na_falha; do python3 -m pytest --collect-only -q tests/test_performance.py
          -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
          -m pytest -q tests/test_performance.py -k "sessao_declara_memoria or sessao_com_memoria_herdada_recusada
          or unpersist_depois_de_publicar or heap_efetivo_conferido_pela_jvm or unpersist_tambem_na_falha"'
        verifies:
        - B-1
      - id: eval_2
        description: Uma passada prova o mesmo que duas
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in uma_passada_igual_a_duas
          linha_trocada_diverge centavo_a_mais_diverge linha_a_menos_diverge; do python3 -m pytest --collect-only
          -q tests/test_performance.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
          exit 1; }; done; python3 -m pytest -q tests/test_performance.py -k "uma_passada_igual_a_duas
          or linha_trocada_diverge or centavo_a_mais_diverge or linha_a_menos_diverge"'
        verifies:
        - B-2
      - id: eval_3
        description: Nada do comportamento selado mudou
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in cinco_controles
          reconfere_no_preparo_antes_de_publicar reverte_so_a_competencia; do python3 -m pytest --collect-only
          -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
          exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "cinco_controles or reconfere_no_preparo_antes_de_publicar
          or reverte_so_a_competencia"'
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: remover um exceptAll sem a igualdade de contagem
        reason: prova só um sentido
        instead: um exceptAll E contagens iguais
      - action: definir a memória por PYSPARK_SUBMIT_ARGS no código
        reason: esconde a declaração fora da sessão
        instead: declarar no builder de criar_sessao e conferir
      - action: chamar unpersist antes de reconferir
        reason: a reconferência releria da origem
        instead: liberar só depois de publicado e reconferido
      do_not_touch:
      - _raw
      - cvg/docs/adrs
      - contracts
      - src/pda
      rollback: Reverter os arquivos tocados ao commit assentado; remover os criados.
      observability: execuções com memória herdada ou cache não liberado
---
# Performance da Bronze e da Silver

Declarar a memória da sessão, liberar o cache e reconferir numa passada, sem mudar a saída.

## Responsibility

Declarar a memória da sessão, liberar o cache e reconferir numa passada, sem mudar a saída.

## Independent proof

Sobre o dado real, Bronze e Silver saem com controles e multiconjunto idênticos à produção e PERF=MELHOR.

## Rejected alternatives

- **Remover um dos exceptAll da reconferência** — Tirar a prova para ganhar tempo é o que o guardião proíbe; a passada única prova o mesmo.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
