> Projetado de `LEG-PERF-GOLD.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `dabd4db4cf286d01ac21cabb9e712491fd8eb5919886f99c0179fe1538b72638`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-PERF-GOLD
seam_id: SEAM-PERF-GOLD
swimlane_id: LANE-PERF-GOLD
observable_state: Gold e assuntos com menos commits e a mesma saída
proof: PERF=MELHOR com resultado idêntico.
requires:
- bronze e silver performaticas
produces:
- gold performatica
tasks:
- id: T-20260924-perf-gold
  title: Cache liberado e constraints num commit só na Gold
  goal: Baixar o custo da Gold e dos assuntos sem mudar a saída.
  done_condition: A Gold e os assuntos reais saem idênticos à produção e o gate dá PERF=MELHOR contra
    perf/baseline-assuntos.
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
    then: 'todo DataFrame persistido é liberado com unpersist depois de publicado e reconferido; uma tabela
      NOVA de assuntos nasce com as colunas monetárias protegidas por UM CHECK que exige todas >= 0 —
      um commit em vez de seis —, e uma tabela que já existe com os seis CHECK é reconhecida como protegida,
      sem receber constraint nova nem perder as antigas; a reconferência passa a uma passada como na Bronze.
      O ganho só vale com o gate da skill spark-perf: PERF=MELHOR contra a baseline gravada em perf/,
      com a saída IDÊNTICA à de produção — controles e multiconjunto 0/0. Otimização que muda o número
      é defeito, não ganho; nenhuma reconferência é removida, só barateada.'
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
      check_unico_no_create tabela_com_seis_check_reconhecida; do python3 -m pytest --collect-only -q
      tests/test_performance_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_performance_gold.py -k "gold_unpersist_depois_de_publicar
      or check_unico_no_create or tabela_com_seis_check_reconhecida"'
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
      fat_especie_fecha_com_a_ancora publica_com_replacewhere; do python3 -m pytest --collect-only -q
      tests/test_gold_assuntos.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
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
source_seam_sha256: 0c9ae44a5466e1ed6d785742de6b19352084c871f5bbc93c638fb745ee8f0609
---
# Gold e assuntos com menos commits e a mesma saída

## Observable proof

PERF=MELHOR com resultado idêntico.

## Runnable leaves

- `T-20260924-perf-gold` — Cache liberado e constraints num commit só na Gold: A Gold e os assuntos reais saem idênticos à produção e o gate dá PERF=MELHOR contra perf/baseline-assuntos.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
