> Projetado de `LEG-LIMPA-PREPARO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `6c895cb0400eefbcad32719ad64d72c3b1bb0e8f3d31a88e00f3c69354da2fcd`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-LIMPA-PREPARO
seam_id: SEAM-LIMPA-PREPARO
swimlane_id: LANE-LIMPA-PREPARO
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
  done_condition: Para cada camada, o preparo de uma execução é apagado só se o histórico da tabela publicada
    tem o commit daquela execução; qualquer outro caso preserva o preparo e diz por quê.
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
    then: confere o commit pelo id da execução no userMetadata, apaga SÓ o prefixo <camada>/_preparo/.../execucao=<id>
      — um caminho montado de partes validadas, recusado se vier vazio ou fora de _preparo —, e confere
      depois que a tabela publicada mantém a mesma versão, a mesma contagem e a mesma soma.
  - id: B-2
    given: uma execução sem commit no histórico, um id vazio ou um caminho fora do preparo
    when: a limpeza roda
    then: 'não apaga nada e devolve o motivo: execução não publicada preserva o preparo; id vazio ou caminho
      fora de _preparo é RECUSADO antes de qualquer remoção, porque um prefixo vazio já montou uma vez
      o caminho do bucket inteiro.'
  evals:
  - id: eval_1
    description: Apaga só o preparo conferido
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in apaga_preparo_de_execucao_publicada
      publicada_intacta_depois; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null
      | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py
      -k "apaga_preparo_de_execucao_publicada or publicada_intacta_depois"'
    verifies:
    - B-1
  - id: eval_2
    description: Guarda de caminho
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in id_vazio_recusado caminho_fora_do_preparo_recusado
      execucao_nao_publicada_preserva; do python3 -m pytest --collect-only -q tests/test_limpeza.py -k
      "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m
      pytest -q tests/test_limpeza.py -k "id_vazio_recusado or caminho_fora_do_preparo_recusado or execucao_nao_publicada_preserva"'
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
source_seam_sha256: 7777e56995a0bef551452e74dab24ee6e0ae0cf938908a571b58e9938d7a125f
---
# Nenhum preparo de execução publicada e conferida sobrevive

## Observable proof

Só apaga com o commit da execução no histórico; nunca fora do prefixo dela.

## Runnable leaves

- `T-20260923-limpa-preparo` — Apagar o preparo de execuções publicadas e conferidas: Para cada camada, o preparo de uma execução é apagado só se o histórico da tabela publicada tem o commit daquela execução; qualquer outro caso preserva o preparo e diz por quê.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
