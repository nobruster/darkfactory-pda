---
schema_version: 1
kind: decision
id: DEC-ONTOLOGIA-LAYOUT-DO-CONTRATO
status: accepted
owner: Bruno Nunes
rationale: 'Correção de 2026-09-24, depois de TASK_LOOP=STALLED: o plano mandava conferir o cabeçalho
  de todo CSV de _raw, e o agente recusou com razão — medido, 2025-07 e 2025-08 têm 13 colunas com uma
  só ''Espécie'' na posição 0, e 2025-09 e 2026-01 têm 14 com as duas ''Espécie'' em 12 e 13. A fonte
  mudou de layout entre 2025-08 e 2025-09. A ontologia descreve o layout do contrato e confere contra
  a fonte que o contrato declara; outro layout exige contrato próprio, medido.'
---
# DEC-ONTOLOGIA-LAYOUT-DO-CONTRATO

Status: **accepted**

Owner: Bruno Nunes

## Rationale

Correção de 2026-09-24, depois de TASK_LOOP=STALLED: o plano mandava conferir o cabeçalho de todo CSV de _raw, e o agente recusou com razão — medido, 2025-07 e 2025-08 têm 13 colunas com uma só 'Espécie' na posição 0, e 2025-09 e 2026-01 têm 14 com as duas 'Espécie' em 12 e 13. A fonte mudou de layout entre 2025-08 e 2025-09. A ontologia descreve o layout do contrato e confere contra a fonte que o contrato declara; outro layout exige contrato próprio, medido.
