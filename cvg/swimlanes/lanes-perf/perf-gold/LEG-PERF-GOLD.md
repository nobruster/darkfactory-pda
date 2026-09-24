> Projetado de `LEG-PERF-GOLD.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `a513a7b0cd0e163f28203048a5cb2be28ac0726241d896dcad96c60fe355bbed`

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
  goal: Baixar o custo da Gold e dos assuntos sem mudar a saída. Para rodar testes, o ÚNICO comando liberado
    ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo>
    -k <cenarios>` — outras formas são recusadas pela permissão.
  done_condition: 'A Gold e os assuntos reais saem idênticos à produção. O PERF=MELHOR contra perf/ é
    VERIFICAÇÃO PÓS-ASSENTAMENTO: roda na execução real com a skill spark-perf, fora do loop, porque tempo
    medido dentro de eval é instável; a entrega exige saída idêntica e o comportamento declarado.'
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
    then: 'todo DataFrame persistido é liberado com unpersist num finally, em TODOS os caminhos — publicado,
      divergente, CHECK que recusou ou exceção de escrita —, e nunca antes da reconferência; uma tabela
      NOVA de assuntos nasce com os CHECK POR COLUNA — os mesmos nomes <coluna>_nao_negativo que já existem
      — declarados NO PRÓPRIO CREATE, pelo builder do Delta: um commit em vez de sete, e medido que o
      Delta 3.2.1 aceita e aplica; uma tabela que já existe com esses CHECK é reconhecida como protegida,
      sem receber constraint nova nem perder as antigas, e a reentrada não adiciona nada; a reconferência
      passa a uma passada como na Bronze. O ganho só vale com o gate da skill spark-perf: PERF=MELHOR
      contra a baseline gravada em perf/, com a saída IDÊNTICA à de produção — controles e multiconjunto
      0/0. Otimização que muda o número é defeito, não ganho; nenhuma reconferência é removida, só barateada.'
  - id: B-2
    given: uma saída com valor monetário negativo ou uma linha trocada
    when: a publicação roda
    then: os CHECK criados no CREATE recusam o negativo exatamente como os adicionados por ALTER recusavam,
      e a reconferência numa passada devolve DIVERGE; nada é publicado; nenhum teste já existente de tests/test_gold.py
      ou tests/test_gold_assuntos.py é editado.
  evals:
  - id: eval_1
    description: Cache liberado e um CHECK só
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_unpersist_depois_de_publicar
      checks_no_proprio_create tabela_existente_reconhecida gold_unpersist_tambem_na_falha; do python3
      -m pytest --collect-only -q tests/test_performance_gold.py -k "$c" 2>/dev/null | grep -q "::" ||
      { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_performance_gold.py
      -k "gold_unpersist_depois_de_publicar or checks_no_proprio_create or tabela_existente_reconhecida
      or gold_unpersist_tambem_na_falha"'
    verifies:
    - B-1
  - id: eval_2
    description: A proteção é a mesma
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in checks_do_create_recusam_negativo
      gold_uma_passada_diverge_linha_trocada; do python3 -m pytest --collect-only -q tests/test_performance_gold.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_performance_gold.py -k "checks_do_create_recusam_negativo or gold_uma_passada_diverge_linha_trocada"'
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
    instead: os mesmos CHECK por coluna, criados no CREATE
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
source_seam_sha256: dea70f982a9a7aec9b54152cc8fdf614fae8742bef3b9c747fc1136df61968e3
---
# Gold e assuntos com menos commits e a mesma saída

## Observable proof

PERF=MELHOR com resultado idêntico.

## Runnable leaves

- `T-20260924-perf-gold` — Cache liberado e constraints num commit só na Gold: A Gold e os assuntos reais saem idênticos à produção. O PERF=MELHOR contra perf/ é VERIFICAÇÃO PÓS-ASSENTAMENTO: roda na execução real com a skill spark-perf, fora do loop, porque tempo medido dentro de eval é instável; a entrega exige saída idêntica e o comportamento declarado.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
