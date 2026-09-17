---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-EVIDENCIA-RECONSTROI
seam_id: SEAM-EVIDENCIA
swimlane_id: LANE-EVIDENCIA
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
  done_condition: O pacote contém veredito, âncora, agregado e classificações, e distingue ACEITO de ACEITO_SEM_ANCORA.
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
    given: uma execução sem âncora
    when: o pacote é gravado
    then: o veredito registrado é ACEITO_SEM_ANCORA
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
source_seam_sha256: 621eee49cc00c6e6d1992b21ebb0ff6215ba720ac0a83feb610b6d7b70d5b4c2
---
# O pacote reconstrói o veredito sem reexecutar

## Observable proof

Ler o pacote reproduz o mesmo veredito; ACEITO_SEM_ANCORA é distinguível de ACEITO no arquivo.

## Runnable leaves

- `T-20260917-evidencia-packet` — Gravar o pacote de evidência por execução: O pacote contém veredito, âncora, agregado e classificações, e distingue ACEITO de ACEITO_SEM_ANCORA.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
