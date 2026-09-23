> Projetado de `LEG-CONTRATO-EXPOE-GRUPOS.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `baba95afaee8706ec3fa1badb739e796265e5e6655d86ae02f16642af6beb9ee`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-CONTRATO-EXPOE-GRUPOS
seam_id: SEAM-CONTRATO-GRUPOS
swimlane_id: LANE-CONTRATO-GRUPOS
observable_state: O Contrato carregado expõe grupos_especie
proof: O contrato real expõe os grupos; bloco inválido é recusado no carregamento.
requires: []
produces:
- contrato com grupos
tasks:
- id: T-20260923-contrato-expoe-grupos
  title: Expor grupos_especie no Contrato carregado
  goal: Fazer o objeto carregado dizer o mapa de grupos que o YAML aprova.
  done_condition: O contrato real expõe grupos_especie com 5 grupos e 65 códigos; um contrato sem o bloco
    carrega com None; bloco inválido é recusado; e toda a suíte já existente de tests/test_contrato.py
    passa sem edição.
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
  - src/pda/contrato.py
  - tests/test_contrato.py
  creates_paths: []
  behavior:
  - id: B-1
    given: o contrato real da competência 2026-01, com grupos_especie aprovado
    when: o contrato é carregado
    then: o Contrato expõe grupos_especie com aprovador, data, regra e a lista de grupos, cada um com
      seu nome e os códigos como TEXTO, lidos do MESMO carregamento; um contrato sem o bloco carrega com
      None, e é o consumidor que o exige.
  - id: B-2
    given: um bloco grupos_especie presente e inválido
    when: o contrato é carregado
    then: 'é RECUSADO no carregamento: código repetido entre grupos, código que não é texto, grupo sem
      códigos, aprovação sem aprovador ou data, ou total de códigos distintos diferente de cardinalidade.codigos_distintos.
      Nenhum teste já existente de tests/test_contrato.py é editado.'
  evals:
  - id: eval_1
    description: Os grupos expostos, opcionais, em texto
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in expoe_grupos_especie
      grupos_ausentes_viram_none codigos_de_grupo_sao_texto; do python3 -m pytest --collect-only -q tests/test_contrato.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_contrato.py -k "expoe_grupos_especie or grupos_ausentes_viram_none or codigos_de_grupo_sao_texto"'
    verifies:
    - B-1
  - id: eval_2
    description: Bloco inválido recusado no carregamento
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grupo_codigo_repetido_recusado
      grupos_cobertura_diferente_recusada grupos_sem_aprovacao_recusado; do python3 -m pytest --collect-only
      -q tests/test_contrato.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_contrato.py -k "grupo_codigo_repetido_recusado
      or grupos_cobertura_diferente_recusada or grupos_sem_aprovacao_recusado"'
    verifies:
    - B-2
  - id: eval_3
    description: O comportamento selado segue intacto
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in expoe_mapa_de_colapsos
      expoe_particionamento nao_relaxa_recusa_de_float; do python3 -m pytest --collect-only -q tests/test_contrato.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_contrato.py -k "expoe_mapa_de_colapsos or expoe_particionamento or nao_relaxa_recusa_de_float"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: exigir grupos_especie no carregador
    reason: contratos-fixture antigos não o têm
    instead: expor como opcional e deixar a Gold exigir
  - action: converter códigos para inteiro
    reason: '''01'' vira 1 e não casa com o dado'
    instead: manter e exigir texto
  - action: editar um teste já existente de tests/test_contrato.py
    reason: teste selado que precisa mudar denuncia mudança de comportamento
    instead: só acrescentar testes novos
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  rollback: Reverter src/pda/contrato.py e tests/test_contrato.py ao commit assentado.
  observability: contratos carregados sem grupos_especie
source_seam_sha256: e299e3e4d6770f1430e5420ee61b12c5d49ff6d6af6620328968fc8b6624479a
---
# O Contrato carregado expõe grupos_especie

## Observable proof

O contrato real expõe os grupos; bloco inválido é recusado no carregamento.

## Runnable leaves

- `T-20260923-contrato-expoe-grupos` — Expor grupos_especie no Contrato carregado: O contrato real expõe grupos_especie com 5 grupos e 65 códigos; um contrato sem o bloco carrega com None; bloco inválido é recusado; e toda a suíte já existente de tests/test_contrato.py passa sem edição.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
