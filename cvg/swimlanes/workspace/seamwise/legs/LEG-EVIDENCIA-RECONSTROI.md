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
    then: o veredito é REDERIVADO dos cinco controles, da âncora, das classificações de cada diferença,
      dos hashes e dos PARES de origens distintas que motivaram cada comparação — as duas listas de defeitos,
      a observada na leitura e a declarada no envelope, e os dois mapas de totais por código, o da leitura
      e o do envelope, todos gravados separadamente; sem eles, um RECUSADO legítimo rederivaria ACEITO,
      seja por omissão de defeito, seja por um envelope que transfere 1,00 do código A para o B mantendo
      chaves, controles globais, hashes e defeitos idênticos — casos em que só a divergência entre os
      dois lados explica a recusa. E o pacote preserva o TIPO original de cada campo monetário recebido,
      sem normalizar — serializar tudo como string faria 0.0 e '0.00' virarem insumos numericamente iguais,
      e a recusa legítima por número JSON deixaria de ser rederivável embora controles e hashes coincidam;
      o pacote adulterado é recusado porque o rótulo discorda do que esses insumos produzem. São TRÊS
      os hashes gravados, os mesmos que a fronteira compara — o ANCORADO do contrato, o OBSERVADO computado
      na leitura e o DECLARADO no envelope; com dois só, um pacote legítimo de RECUSADO por ancorado=observado
      e declarado divergente rederivaria ACEITO e seria rejeitado. A ausência não é recusa incondicional,
      ela decide o veredito — e quem decide é a CAUSA registrada, não a falta de um hash. Contrato que
      devolveu NAO_MEDIDO por qualquer motivo — sem âncora, sem aprovador, sem data ou sem política decimal
      — dá ACEITO_SEM_ANCORA, mesmo que o hash ancorado exista e nenhum observado tenha sido produzido;
      e o pacote grava os CAMPOS DE APROVAÇÃO do contrato como foram lidos, presentes ou ausentes, não
      só a causa, porque dois contratos em estados de aprovação diferentes produziriam os mesmos dados
      auditáveis e o leitor apenas confiaria no rótulo da causa — trocar a confiança no rótulo do veredito
      pela confiança noutro rótulo não é rederivar, e uma causa incorreta passaria sem ninguém ver; ler
      a falta do hash como se fosse a causa recusaria justamente o pacote que a orquestração deve gravar.
      Falta o observado COM evento de falha registrado e é execução interrompida, desfecho ERRO. Contrato
      RECUSADO no carregamento, por política que contradiz o ADR, é um terceiro caminho antecipado — termina
      sem hash observado, sem agregado e sem envelope, não é NAO_MEDIDO nem exceção, e o pacote grava
      a política recusada e a cláusula do ADR violada, que é o que a rederivação precisa para reconstruir
      esse RECUSADO sem depender do rótulo. A precedência é declarada, não deduzida — NAO_MEDIDO decide
      antes, RECUSADO por contrato exige a política gravada, e ERRO exige o evento. Os três casos gravam
      pacote válido; recusar qualquer um impediria de gravar justamente a execução que precisa de registro.
      Só é recusado o pacote cujo rótulo não bate com o que os insumos rederivam; campos não percorridos
      são marcados ausentes, nunca zerados
  - id: B-2
    given: duas execuções da mesma competência
    when: a segunda é gravada
    then: as duas coexistem — a segunda não sobrescreve a primeira
  evals:
  - id: eval_1
    description: Rederiva com os três hashes; precedência quando ancorado e observado faltam juntos
    bash: pytest -q tests/test_evidencia.py -k "rederiva or rotulo_adulterado or tres_hashes or precedencia_sem_ancora"
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
source_seam_sha256: 3976ca5bfeee6c425fc18401d3c329bd099e2ff7c1aecc3020f4692aa79780b7
---
# O pacote reconstrói o veredito sem reexecutar

## Observable proof

Ler o pacote reproduz o veredito; gravar duas execuções preserva as duas.

## Runnable leaves

- `T-20260921-evidencia-packet` — Gravar o pacote por execução, sem sobrescrever: O pacote traz veredito, causa, âncora, agregado, duração e classificações; duas execuções coexistem.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
