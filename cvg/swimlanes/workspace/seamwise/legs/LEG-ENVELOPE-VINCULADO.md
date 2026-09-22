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
    given: um envelope sem o sha256 do arquivo lido, outro cujo sha256 difere do ancorado, e um terceiro
      que COPIOU o sha256 ancorado mas foi produzido lendo outro arquivo
    when: o envelope é validado
    then: os três são recusados — o sha256 não é campo declarado e sim SAÍDA do leitor, computado sobre
      os mesmos bytes que alimentaram os controles e emitido junto com eles; o terceiro é recusado porque
      o hash que o leitor computou discorda do que o envelope declara, e é esse caso, não a mera igualdade,
      que prova o vínculo — um hash copiado, com os cinco controles coincidindo, passaria em qualquer
      teste de igualdade
  - id: B-2
    given: um envelope onde linhas_invalidas diverge da contagem de defeitos do tipo VALOR_ILEGIVEL, e
      outro com linhas_invalidas=0 e defeitos de truncamento, e outro produzido por um motor que não é
      o juiz
    when: o envelope é validado
    then: o primeiro é recusado; o segundo é ACEITO — truncamento é defeito numa linha válida, e a competência
      2026-01 tem linhas_invalidas=0 com milhões de truncamentos; o terceiro é aceito sem que o juiz importe
      nada do motor produtor
  evals:
  - id: eval_1
    description: Sha ausente, divergente, ou copiado de outro arquivo lido é recusado
    bash: pytest -q tests/test_envelope.py -k "sha_ausente or sha_divergente or sha_copiado_outro_arquivo"
    verifies:
    - B-1
  - id: eval_2
    description: linhas_invalidas confere com VALOR_ILEGIVEL; truncamento não a incrementa
    bash: pytest -q tests/test_envelope.py -k "invalidas_por_tipo or truncamento_nao_invalida"
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
  - action: somar todo defeito em linhas_invalidas
    reason: truncamento é defeito numa linha VÁLIDA; a competência 2026-01 tem linhas_invalidas=0 com
      milhões de truncamentos, e a regra recusaria o dado correto
    instead: conferir linhas_invalidas só contra defeitos do tipo VALOR_ILEGIVEL
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  rollback: Remover o validador de envelope e seus testes.
  observability: envelopes recusados por motivo
source_seam_sha256: 79d576add826943381a84fde5b1b3cf823fff30277e7c47dcf9b9a1a5ae40a49
---
# O envelope liga o agregado ao arquivo que o gerou

## Observable proof

Envelope sem sha256 do arquivo é recusado; sha256 divergente do ancorado é recusado; linhas_invalidas incoerente com os defeitos observados é recusado.

## Runnable leaves

- `T-20260921-envelope-fronteira` — Declarar e validar o envelope entre produtor e juiz: O envelope declara os cinco controles, o sha256 do arquivo lido e os defeitos; validação recusa sha256 ausente, divergente, ou linhas_invalidas incoerente.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
