---
schema_version: 1
kind: seam
claim: derived
id: SEAM-VINCULADOR-GRAMATICA
name: Vinculador com a mesma gramática
description: Separa a prova de procedência de uma gramática própria.
evidence:
- E-ANCORA-202601
responsibility: Medir pela mesma gramática do gravador.
consumes:
- produtor e gravador corrigidos
produces: &id001
- vinculador alinhado
owner: medalhao
independent_proof: Vinculador prova a partição gravada pelo gravador corrigido.
decision_ids:
- DEC-CORRIGE-PRODUTOR
rejected_alternatives:
- alternative: Manter os defeitos fixados em teste
  reason: o dono decidiu corrigir em 2026-09-24.
swimlane:
  id: LANE-VINCULADOR-GRAMATICA
  name: Vinculador com a mesma gramática lane
  owner: medalhao
  legs:
  - id: LEG-VINCULADOR-GRAMATICA
    observable_state: Vinculador com a mesma gramática
    proof: Vinculador prova a partição gravada pelo gravador corrigido.
    requires:
    - produtor e gravador corrigidos
    produces: *id001
    tasks:
    - id: T-20260924-vinculador-gramatica
      title: O vinculador de procedência com a mesma gramática do gravador
      goal: Fazer o vinculador medir a partição pela mesma gramática com que o gravador a gravou. Para
        rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml
        exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.
      done_condition: src/produtor/vincular_procedencia.py usa gramatica.valor_decimal; os testes existentes
        de tests/test_vincular_procedencia.py passam sem edição; os testes novos provam que vinculador
        e gravador medem igual e que o vinculador prova uma partição gravada pelo gravador corrigido.
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
      - T-20260924-produtor-e-gravador-corrigem
      touches_paths:
      - src/produtor/vincular_procedencia.py
      - tests/test_vincular_procedencia.py
      creates_paths: []
      behavior:
      - id: B-1
        given: um CSV em tmp_path com '1,5', '-5,00' e valores válidos
        when: o main do gravador corrigido grava esse CSV em tmp_path, num processo filho sem S3_*, e
          vincular_procedencia.vincular confere a partição gravada
        then: ler_fonte usa gramatica.valor_decimal — a regex local sai de vincular_procedencia.py —,
          os cinco controles de ler_fonte e de gravar_lago._ler_fonte sobre o mesmo CSV são iguais, e
          o vínculo da partição gravada pelo gravador corrigido é GRAVADO; a declaração de ANSI que já
          existe fica; nenhuma outra função muda de comportamento.
      - id: B-2
        given: o tests/test_vincular_procedencia.py selado
        when: a tarefa acrescenta os testes novos
        then: todos os test_* existentes ficam como estão e passam; entram só test_vinculador_usa_a_gramatica_do_juiz,
          test_vinculador_e_gravador_medem_igual e test_vinculador_prova_particao_do_gravador_corrigido.
          Nenhum cenário usa skip, xfail ou importorskip.
      evals:
      - id: eval_1
        description: A mesma gramática, e a partição gravada provada
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in vinculador_usa_a_gramatica_do_juiz
          vinculador_e_gravador_medem_igual vinculador_prova_particao_do_gravador_corrigido; do python3
          -m pytest --collect-only -q tests/test_vincular_procedencia.py -k "$c" 2>/dev/null | grep -q
          "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_vincular_procedencia.py
          -k "vinculador_usa_a_gramatica_do_juiz or vinculador_e_gravador_medem_igual or vinculador_prova_particao_do_gravador_corrigido"'
        verifies:
        - B-1
      - id: eval_2
        description: A prova segue igual
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grava_manifesto_hash_e_controles
          rele_o_que_gravou valor_em_decimal_nunca_float; do python3 -m pytest --collect-only -q tests/test_vincular_procedencia.py
          -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
          -m pytest -q tests/test_vincular_procedencia.py -k "grava_manifesto_hash_e_controles or rele_o_que_gravou
          or valor_em_decimal_nunca_float"'
        verifies:
        - B-2
      - id: eval_3
        description: As recusas seguem iguais
        bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in zero_linhas_e_nao_medido
          prova_identica_nao_regrava hash_divergente_nao_grava; do python3 -m pytest --collect-only -q
          tests/test_vincular_procedencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
          exit 1; }; done; python3 -m pytest -q tests/test_vincular_procedencia.py -k "zero_linhas_e_nao_medido
          or prova_identica_nao_regrava or hash_divergente_nao_grava"'
        verifies:
        - B-2
      anti_patterns:
      - action: editar um teste existente
        reason: a tarefa só troca a gramática
        instead: só acrescentar
      - action: regravar a _PROCEDENCIA.json da 2026-01
        reason: a prova anterior nunca é sobrescrita
        instead: o 2026-01 não muda com a gramática nova
      - action: copiar a regex de novo
        reason: é a duplicação que criou a divergência
        instead: importar gramatica
      do_not_touch:
      - _raw
      - contracts
      - cvg/docs/adrs
      - src/pda
      - src/medalhao
      - src/ontologia
      - infra
      - src/produtor/gramatica.py
      - tests/test_gramatica.py
      - src/produtor/spark_produtor.py
      - src/produtor/gravar_lago.py
      - tests/test_produtor.py
      rollback: Reverter src/produtor/vincular_procedencia.py e tests/test_vincular_procedencia.py ao
        commit anterior.
      observability: vínculo divergente do gravador
---
# Vinculador com a mesma gramática

Separa a prova de procedência de uma gramática própria.

## Responsibility

Medir pela mesma gramática do gravador.

## Independent proof

Vinculador prova a partição gravada pelo gravador corrigido.

## Rejected alternatives

- **Manter os defeitos fixados em teste** — o dono decidiu corrigir em 2026-09-24.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
