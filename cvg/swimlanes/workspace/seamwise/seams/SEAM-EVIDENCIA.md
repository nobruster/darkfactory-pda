---
schema_version: 1
kind: seam
claim: derived
id: SEAM-EVIDENCIA
name: Pacote de evidência
description: Separa o registro da prova da decisão que a produziu.
evidence:
- E-ANCORA-202603
responsibility: Gravar o veredito e os números de forma reconstruível.
consumes:
- veredito classificado
produces:
- pacote de evidência
owner: evidencia
independent_proof: O veredito é reconstruído a partir do pacote sem reexecutar o pipeline, e ACEITO_SEM_ANCORA
  nunca aparece como ACEITO.
decision_ids:
- ADR-0002-ANCORA-2026-03
rejected_alternatives:
- alternative: Registrar apenas o veredito final
  reason: Sem os números, ninguém consegue responder meses depois por que aquele número foi aceito.
swimlane:
  id: LANE-EVIDENCIA
  name: Evidência lane
  owner: evidencia
  legs:
  - id: LEG-EVIDENCIA-RECONSTROI
    observable_state: O pacote reconstrói o veredito sem reexecutar
    proof: Ler o pacote reproduz o mesmo veredito; ACEITO_SEM_ANCORA é distinguível de ACEITO no arquivo.
    requires:
    - veredito classificado
    produces:
    - pacote de evidência
    tasks:
    - id: T-20260917-evidencia-packet
      title: Gravar o pacote de evidência por execução
      goal: Tornar o veredito auditável sem reexecutar o pipeline.
      done_condition: O pacote contém veredito, âncora, agregado e classificações, e distingue ACEITO
        de ACEITO_SEM_ANCORA.
      effort: S
      profile: standard
      execution_backend: any
      required_tools:
      - git
      - bash
      - python3
      - pytest
      depends_on:
      - T-20260917-juizo-classifica
      touches_paths: []
      creates_paths:
      - src/fabrica/evidencia.py
      - tests/test_evidencia.py
      behavior:
      - id: B-1
        given: uma execução com âncora medida
        when: o pacote é lido de volta
        then: o veredito é reconstruído sem reexecutar o pipeline
      - id: B-2
        given: qualquer veredito terminal — ACEITO, ACEITO_SEM_ANCORA ou NAO_MEDIDO
        when: o pacote é gravado
        then: o pacote existe e registra QUAL dos três foi, com os campos que existirem; NAO_MEDIDO grava
          sem agregado e nunca aparece como ACEITO
      evals:
      - id: eval_1
        description: O pacote reconstrói o veredito
        bash: pytest -q tests/test_evidencia.py -k reconstroi
        verifies:
        - B-1
      - id: eval_2
        description: Sem âncora nunca vira ACEITO
        bash: pytest -q tests/test_evidencia.py -k sem_ancora
        verifies:
        - B-2
      - id: eval_3
        description: O pacote registra âncora, agregado e classificações
        bash: pytest -q tests/test_evidencia.py -k campos_obrigatorios
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: gravar ACEITO com gate de âncora falso dentro
        reason: foi a objeção 28 — 82 milhões de linhas sem conferência
        instead: publicar ACEITO_SEM_ANCORA de forma visível
      - action: editar um pacote antigo para corrigir o histórico
        reason: falsifica evidência
        instead: gravar evidência nova e manter a antiga
      - action: gravar só o veredito, sem os números
        reason: ninguém consegue reconstruir por que aquilo foi aceito
        instead: registrar âncora, agregado e cada classificação
      do_not_touch:
      - evidence
      rollback: Remover o gravador de evidência e seus testes.
      observability: pacotes gravados por competência
---
# Pacote de evidência

Separa o registro da prova da decisão que a produziu.

## Responsibility

Gravar o veredito e os números de forma reconstruível.

## Independent proof

O veredito é reconstruído a partir do pacote sem reexecutar o pipeline, e ACEITO_SEM_ANCORA nunca aparece como ACEITO.

## Rejected alternatives

- **Registrar apenas o veredito final** — Sem os números, ninguém consegue responder meses depois por que aquele número foi aceito.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
