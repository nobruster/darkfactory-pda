---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-EVIDENCIA-RECONSTROI
seam_id: SEAM-EVIDENCIA
swimlane_id: LANE-EVIDENCIA
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
  done_condition: O pacote traz veredito, causa, âncora, agregado, duração e classificações; duas execuções
    coexistem.
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
    given: uma execução com âncora, outra que terminou antes da leitura, e um pacote adulterado onde só
      o rótulo do veredito foi trocado
    when: o pacote é lido de volta
    then: o veredito é REDERIVADO dos cinco controles, da âncora, das classificações de cada diferença
      e dos hashes gravados — nunca lido do rótulo; o pacote adulterado é recusado porque o rótulo discorda
      do que esses insumos produzem. A ausência de hash não é recusa incondicional — ela decide o veredito,
      porque sem hash do CSV o desfecho é ACEITO_SEM_ANCORA com causa NAO_MEDIDO e o pacote é válido;
      recusar aqui impediria de gravar justamente a execução que não tinha âncora. Só é recusado o pacote
      cujo rótulo não bate com o que os insumos rederivam; campos não percorridos são marcados ausentes,
      nunca zerados
  - id: B-2
    given: duas execuções da mesma competência
    when: a segunda é gravada
    then: as duas coexistem — a segunda não sobrescreve a primeira
  evals:
  - id: eval_1
    description: Rederiva com classificações; rótulo trocado recusa; sem hash grava ACEITO_SEM_ANCORA
    bash: pytest -q tests/test_evidencia.py -k "rederiva or ausente or rotulo_adulterado or sem_hash_aceito_sem_ancora"
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
  - action: ler o veredito do rótulo gravado no pacote
    reason: o rótulo é conclusão, não prova — trocá-lo basta para mentir
    instead: rederivar dos controles, da âncora e dos hashes
  do_not_touch:
  - _raw
  - evidence
  rollback: Remover o gravador de evidência e seus testes.
  observability: pacotes gravados por competência
source_seam_sha256: 3474e47fccc93c6ac733c088241d5c486d8640ff33c7f4c02457fbda0a0d39c2
---
# O pacote reconstrói o veredito sem reexecutar

## Observable proof

Ler o pacote reproduz o veredito; gravar duas execuções preserva as duas.

## Runnable leaves

- `T-20260921-evidencia-packet` — Gravar o pacote por execução, sem sobrescrever: O pacote traz veredito, causa, âncora, agregado, duração e classificações; duas execuções coexistem.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
