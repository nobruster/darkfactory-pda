---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-ENVELOPE-VINCULADO
seam_id: SEAM-FRONTEIRA
swimlane_id: LANE-FRONTEIRA
observable_state: O envelope liga o agregado ao arquivo que o gerou
proof: Envelope sem sha256 do arquivo é recusado; sha256 divergente do ancorado é recusado; linhas_invalidas
  incoerente com os defeitos observados é recusado.
requires:
- agregado da competência
- defeitos observados
produces:
- envelope do produtor
tasks:
- id: T-20260921-envelope-fronteira
  title: Declarar e validar o envelope entre produtor e juiz
  goal: Fazer a fronteira ser um contrato escrito, não o que o juiz por acaso aceita.
  done_condition: O envelope declara os cinco controles, o sha256 do arquivo lido e os defeitos; validação
    recusa sha256 ausente, divergente, ou linhas_invalidas incoerente.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on:
  - T-20260921-agregacao-exata
  touches_paths: []
  creates_paths:
  - src/pda/envelope.py
  - tests/test_envelope.py
  - contracts/envelope-produtor.schema.json
  behavior:
  - id: B-1
    given: um envelope sem o sha256 do arquivo lido, e outro cujo sha256 difere do que o contrato ancorou
    when: o envelope é validado
    then: ambos são recusados — a âncora vale para UM arquivo, e sem esse vínculo uma republicação com
      os mesmos cinco controles passaria despercebida
  - id: B-2
    given: um envelope com linhas_invalidas menor que a contagem de defeitos observados, e outro produzido
      por um motor que não é o juiz
    when: o envelope é validado
    then: o primeiro é recusado por incoerência interna; o segundo é aceito sem que o juiz importe nada
      do motor produtor
  evals:
  - id: eval_1
    description: Sha256 ausente ou divergente do ancorado é recusado
    bash: pytest -q tests/test_envelope.py -k "sha_ausente or sha_divergente"
    verifies:
    - B-1
  - id: eval_2
    description: linhas_invalidas incoerente com os defeitos é recusado
    bash: pytest -q tests/test_envelope.py -k invalidas_coerentes
    verifies:
    - B-2
  - id: eval_3
    description: O schema aceita envelope de qualquer produtor, sem importar o motor
    bash: pytest -q tests/test_envelope.py -k produtor_agnostico
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: aceitar envelope sem o sha256 do arquivo lido
    reason: a âncora vale para um arquivo; sem o vínculo, outra publicação da mesma competência passaria
    instead: exigir o sha256 e compará-lo com o ancorado
  - action: importar o motor produtor dentro do validador
    reason: o juiz voltaria a depender de quem ele julga
    instead: validar o envelope como dado, seja qual for a origem
  - action: aceitar linhas_invalidas sem conferir contra os defeitos
    reason: um produtor que conte só as válidas devolveria zero e ninguém acusaria
    instead: exigir coerência entre o controle e os defeitos observados
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  rollback: Remover o validador de envelope e seus testes.
  observability: envelopes recusados por motivo
source_seam_sha256: b7bb7f4e989d287e5387f3a68d68a3cb58a6e3bfc93453c1de786650bbd0f094
---
# O envelope liga o agregado ao arquivo que o gerou

## Observable proof

Envelope sem sha256 do arquivo é recusado; sha256 divergente do ancorado é recusado; linhas_invalidas incoerente com os defeitos observados é recusado.

## Runnable leaves

- `T-20260921-envelope-fronteira` — Declarar e validar o envelope entre produtor e juiz: O envelope declara os cinco controles, o sha256 do arquivo lido e os defeitos; validação recusa sha256 ausente, divergente, ou linhas_invalidas incoerente.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
