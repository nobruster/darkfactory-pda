---
schema_version: 1
kind: seam
claim: derived
id: SEAM-EVIDENCIA
name: Pacote de evidência
description: Separa o registro da prova da decisão que a produziu.
evidence:
- E-ANCORA-202601
responsibility: Gravar veredito, causa e números de forma reconstruível.
consumes:
- veredito classificado
produces:
- pacote de evidência
owner: evidencia
independent_proof: O veredito é reconstruído do pacote sem reexecutar, e uma execução não sobrescreve
  a anterior.
decision_ids:
- ADR-0004-CODIGO-E-CHAVE
rejected_alternatives:
- alternative: Gravar com overwrite, como o carregamento atual
  reason: Destrói a execução anterior; impossível responder depois o que foi publicado ou comparar duas
    execuções.
swimlane:
  id: LANE-EVIDENCIA
  name: Evidência lane
  owner: evidencia
  legs:
  - id: LEG-EVIDENCIA-RECONSTROI
    observable_state: O pacote reconstrói o veredito sem reexecutar
    proof: Ler o pacote reproduz o veredito; gravar duas execuções preserva as duas.
    requires:
    - veredito classificado
    produces:
    - pacote de evidência
    tasks:
    - id: T-20260921-evidencia-packet
      title: Gravar o pacote por execução, sem sobrescrever
      goal: Tornar o veredito auditável sem reexecutar o pipeline.
      done_condition: O pacote traz veredito, causa, âncora, agregado, duração e classificações; duas
        execuções coexistem.
      effort: S
      profile: standard
      execution_backend: any
      required_tools:
      - git
      - bash
      - python3
      - pytest
      depends_on:
      - T-20260921-juizo-classifica
      touches_paths: []
      creates_paths:
      - src/pda/evidencia.py
      - tests/test_evidencia.py
      behavior:
      - id: B-1
        given: uma execução com âncora, e outra que terminou antes da leitura
        when: o pacote é lido de volta
        then: o veredito é reconstruído sem reexecutar, com duração e limite aplicados; campos não percorridos
          são marcados ausentes, nunca zerados
      - id: B-2
        given: duas execuções da mesma competência
        when: a segunda é gravada
        then: as duas coexistem — a segunda não sobrescreve a primeira
      evals:
      - id: eval_1
        description: O pacote reconstrói o veredito e marca ausências
        bash: pytest -q tests/test_evidencia.py -k "reconstroi or ausente"
        verifies:
        - B-1
      - id: eval_2
        description: Duas execuções coexistem, sem overwrite
        bash: pytest -q tests/test_evidencia.py -k nao_sobrescreve
        verifies:
        - B-2
      - id: eval_3
        description: Os quatro vereditos terminais são distinguíveis
        bash: pytest -q tests/test_evidencia.py -k vereditos
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: gravar com mode overwrite
        reason: e o defeito do carregamento atual — destrói a prova
        instead: gravar um pacote por execução
      - action: editar um pacote antigo para corrigir o histórico
        reason: falsifica evidência
        instead: gravar evidência nova e manter a antiga
      - action: preencher campo ausente com zero
        reason: a reconstrução passa a mentir
        instead: marcar como ausente
      do_not_touch:
      - _raw
      - evidence
      rollback: Remover o gravador de evidência e seus testes.
      observability: pacotes gravados por competência
---
# Pacote de evidência

Separa o registro da prova da decisão que a produziu.

## Responsibility

Gravar veredito, causa e números de forma reconstruível.

## Independent proof

O veredito é reconstruído do pacote sem reexecutar, e uma execução não sobrescreve a anterior.

## Rejected alternatives

- **Gravar com overwrite, como o carregamento atual** — Destrói a execução anterior; impossível responder depois o que foi publicado ou comparar duas execuções.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
