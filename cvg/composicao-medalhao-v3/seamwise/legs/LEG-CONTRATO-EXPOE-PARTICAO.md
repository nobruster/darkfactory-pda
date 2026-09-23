---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-CONTRATO-EXPOE-PARTICAO
seam_id: SEAM-CONTRATO-EXT
swimlane_id: LANE-CONTRATO-EXT
observable_state: O Contrato carregado expõe particionamento e limites de expoente
proof: O contrato real expõe os dois blocos; um contrato sem eles carrega com os campos None, e a suíte
  selada passa inalterada.
requires: []
produces:
- contrato estendido
tasks:
- id: T-20260923-contrato-expoe-particao
  title: Expor particionamento e limites de expoente no Contrato carregado
  goal: Fazer o objeto carregado dizer o que o YAML já declara, sem quebrar a primeira descida.
  done_condition: O contrato real expõe particionamento e politica_decimal.emax/emin; um contrato sem
    esses blocos carrega com os campos None; e TODA a suíte já existente de tests/test_contrato.py passa
    sem que um teste dela seja editado.
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
    given: o contrato real da competência 2026-01, que declara particionamento — chave, caminho, formato,
      valores medidos, objetos auxiliares ignorados — e politica_decimal com emax 999999 e emin -999999,
      com aprovador e data
    when: o contrato é carregado
    then: 'o objeto Contrato expõe um campo particionamento com os cinco atributos, a politica_decimal
      expõe emax e emin, e o Contrato expõe o MAPA DE COLAPSOS APROVADO — os grupos, cada um com a descrição
      original e a lista dos códigos que ela cobre, e o aprovador e a data da aprovação —, porque a decisão
      DEC-MAPA-APROVADO-OBRIGATORIO torna o mapa condição de publicação e, sem este campo, ele não teria
      caminho do YAML até Silver nem depois de aprovado, lidos do MESMO carregamento — uma única leitura
      do YAML, nunca uma segunda porta para o mesmo oráculo. Os campos novos são OPCIONAIS no carregador:
      um contrato sem esses blocos carrega com eles None, e None não é zero nem vazio — é ausência declarada,
      que Bronze, e não o carregador, trata como NAO_MEDIDO. Exigi-los aqui recusaria os contratos-fixture
      da primeira descida, que não os têm, e quebraria a suíte selada: o requisito é do consumidor, e
      é ele que o impõe. Já um bloco PRESENTE E INVÁLIDO é RECUSADO no carregamento, como o carregador
      selado já faz com política contraditória — emax que não é inteiro, emin maior que emax, e — porque
      ordem entre inteiros é proxy e não garante contexto utilizável — o carregador CONSTRÓI o Context
      declarado inteiro (precisão, arredondamento, traps=[], emax, emin) e RECUSA quando o construtor
      recusa ou quando o total e o máximo da âncora não o atravessam intactos, sem Overflow: MEDIDO, emin=-10
      com emax=9 leva a âncora, de expoente ajustado 10, a Infinity em silêncio. Conferir o total e o
      máximo basta pela ADR 0009 — soma monotônica sem negativos, nenhum intermediário excede o total;
      particionamento sem chave, mapa com grupo de um código só ou código repetido entre grupos, aprovação
      sem aprovador ou sem data. Entregar o bloco e deixar a camada tropeçar ao construir o Context trocaria
      uma recusa com motivo por uma exceção longe da causa'
  - id: B-2
    given: a suíte já existente de tests/test_contrato.py, selada na primeira descida
    when: o carregador estendido é testado
    then: 'toda a suíte existente passa SEM que um teste dela seja editado, e o comportamento selado fica
      intacto — recusa de float nos controles, precisão derivada por suficiência, política contraditória
      recusada no carregamento, NAO_MEDIDO sem âncora. Estender não é afrouxar: a tarefa só ACRESCENTA
      atributos, e um teste selado que precisasse mudar denunciaria que o carregador mudou de comportamento,
      que é o que a Regra 11 existe para impedir sem autorização'
  evals:
  - id: eval_1
    description: Os dois blocos expostos, opcionais, e None não é zero
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in expoe_particionamento
      expoe_limites_de_expoente campos_novos_sao_opcionais ausencia_vira_none_nao_zero expoe_mapa_de_colapsos
      limites_que_estouram_a_ancora_recusados; do python3 -m pytest --collect-only -q tests/test_contrato.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_contrato.py -k "expoe_particionamento or expoe_limites_de_expoente or campos_novos_sao_opcionais
      or ausencia_vira_none_nao_zero or expoe_mapa_de_colapsos or limites_que_estouram_a_ancora_recusados"'
    verifies:
    - B-1
  - id: eval_2
    description: A suíte selada passa inteira, e o contrato real expõe os dois
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in suite_selada_continua_passando
      fixture_sem_campos_novos contrato_real_expoe_os_dois; do python3 -m pytest --collect-only -q tests/test_contrato.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_contrato.py && python3 -m pytest -q tests/test_contrato.py -k "suite_selada_continua_passando
      or fixture_sem_campos_novos or contrato_real_expoe_os_dois"'
    verifies:
    - B-1
    - B-2
  - id: eval_3
    description: Nada do comportamento selado afrouxou
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in nao_relaxa_recusa_de_float
      nao_muda_precisao_derivada nao_le_o_yaml_duas_vezes bloco_presente_e_invalido_recusado; do python3
      -m pytest --collect-only -q tests/test_contrato.py -k "$c" 2>/dev/null | grep -q "::" || { echo
      "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_contrato.py -k "nao_relaxa_recusa_de_float
      or nao_muda_precisao_derivada or nao_le_o_yaml_duas_vezes or bloco_presente_e_invalido_recusado"'
    verifies:
    - B-2
  anti_patterns:
  - action: exigir no carregador os campos novos como obrigatórios
    reason: os contratos-fixture da primeira descida não os têm, e a suíte selada quebraria
    instead: expô-los como opcionais e deixar o consumidor exigi-los
  - action: editar um teste já existente de tests/test_contrato.py para ele passar
    reason: teste selado que precisa mudar denuncia mudança de comportamento no carregador
    instead: só acrescentar testes novos; se um antigo falhar, o carregador é que está errado
  - action: ler o YAML uma segunda vez para achar os blocos novos
    reason: duas leituras do mesmo oráculo podem divergir, e o contrato passa a ter duas verdades
    instead: extrair os blocos no mesmo carregamento que já existe
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  rollback: Reverter src/pda/contrato.py e tests/test_contrato.py ao commit selado.
  observability: contratos carregados sem os blocos novos
source_seam_sha256: 2f73670ab88c541301ec3f39979bd682e1d741146b24e8c3d5afcde901ade7c7
---
# O Contrato carregado expõe particionamento e limites de expoente

## Observable proof

O contrato real expõe os dois blocos; um contrato sem eles carrega com os campos None, e a suíte selada passa inalterada.

## Runnable leaves

- `T-20260923-contrato-expoe-particao` — Expor particionamento e limites de expoente no Contrato carregado: O contrato real expõe particionamento e politica_decimal.emax/emin; um contrato sem esses blocos carrega com os campos None; e TODA a suíte já existente de tests/test_contrato.py passa sem que um teste dela seja editado.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
