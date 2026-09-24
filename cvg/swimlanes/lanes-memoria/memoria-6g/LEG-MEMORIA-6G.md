> Projetado de `LEG-MEMORIA-6G.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `1474ab7229209c3703d10d00c5e580d539a5820f49a76a7c5ca486c836c13404`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-MEMORIA-6G
seam_id: SEAM-MEMORIA-6G
swimlane_id: LANE-MEMORIA-6G
observable_state: Sessão padrão com 6 GB de heap efetivo
proof: maxMemory da JVM, não a propriedade.
requires: []
produces:
- sessao com memoria medida
tasks:
- id: T-20260924-memoria-6g
  title: Memória do driver declarada com o valor medido
  goal: Fazer a sessão nascer com o heap que as baselines mediram, e não com o 1 GB de antes. Para rodar
    testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark
    python3 -m pytest <arquivo> -k <cenarios>`.
  done_condition: Uma sessão criada por criar_sessao sem memória explícita tem spark.driver.memory = 6g
    e heap efetivo de pelo menos 5,5 GiB; a recusa de heap menor que o declarado segue valendo; toda a
    suíte já existente de tests/test_performance.py passa sem edição.
  effort: S
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
  - tests/test_performance.py
  creates_paths: []
  behavior:
  - id: B-1
    given: uma sessão criada por criar_sessao sem memória explícita, numa JVM ainda não iniciada
    when: a sessão é criada
    then: o padrão MEMORIA_DRIVER_PADRAO é "6g" — o valor com que as baselines de perf/ foram medidas
      e que tirou a Bronze de 506s para 374s de executor —, declarado no builder, e o heap EFETIVO lido
      por Runtime.getRuntime().maxMemory() é de pelo menos 5,5 GiB, porque a JVM desconta o espaço de
      sobrevivente; o valor fica como constante nomeada com o porquê, nunca espalhado.
  - id: B-2
    given: uma sessão cujo heap efetivo é menor que o declarado — JVM já iniciada com menos
    when: criar_sessao confere a sessão
    then: recusa como já recusava, com o heap efetivo e o declarado na mensagem; um pedido explícito de
      memória continua prevalecendo sobre o padrão; nenhum teste já existente de tests/test_performance.py
      é editado.
  evals:
  - id: eval_1
    description: O padrão é o valor medido
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in memoria_padrao_e_seis_gigas
      heap_efetivo_do_padrao; do python3 -m pytest --collect-only -q tests/test_performance.py -k "$c"
      2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest
      -q tests/test_performance.py -k "memoria_padrao_e_seis_gigas or heap_efetivo_do_padrao"'
    verifies:
    - B-1
  - id: eval_2
    description: A recusa e o pedido explícito seguem
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in heap_menor_que_declarado_recusado
      pedido_explicito_prevalece; do python3 -m pytest --collect-only -q tests/test_performance.py -k
      "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m
      pytest -q tests/test_performance.py -k "heap_menor_que_declarado_recusado or pedido_explicito_prevalece"'
    verifies:
    - B-2
  - id: eval_3
    description: O que já existia segue verde
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sessao_declara_memoria
      heap_efetivo_conferido_pela_jvm uma_passada_igual_a_duas; do python3 -m pytest --collect-only -q
      tests/test_performance.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_performance.py -k "sessao_declara_memoria or heap_efetivo_conferido_pela_jvm
      or uma_passada_igual_a_duas"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: declarar a memória por PYSPARK_SUBMIT_ARGS ou spark-defaults
    reason: esconde a declaração fora da sessão
    instead: a constante no builder de criar_sessao
  - action: baixar o padrão para caber num teste
    reason: é o 1 GB que estourou a suíte
    instead: o teste pede memória explícita quando precisa de outra
  - action: editar um teste já existente
    reason: teste selado que precisa mudar denuncia mudança de comportamento
    instead: só acrescentar testes novos
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src/pda
  rollback: Reverter src/medalhao/bronze.py e tests/test_performance.py ao commit assentado.
  observability: sessões com heap efetivo abaixo do declarado
source_seam_sha256: 6ecc328765a2f4b2b7dcff318b61c0887956234092327e3eefe5c4e1af4f1079
---
# Sessão padrão com 6 GB de heap efetivo

## Observable proof

maxMemory da JVM, não a propriedade.

## Runnable leaves

- `T-20260924-memoria-6g` — Memória do driver declarada com o valor medido: Uma sessão criada por criar_sessao sem memória explícita tem spark.driver.memory = 6g e heap efetivo de pelo menos 5,5 GiB; a recusa de heap menor que o declarado segue valendo; toda a suíte já existente de tests/test_performance.py passa sem edição.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
