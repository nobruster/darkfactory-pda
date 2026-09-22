---
schema_version: 1
kind: seam
claim: derived
id: SEAM-FRONTEIRA
name: Fronteira produtor-juiz
description: Separa quem produz o agregado de quem o julga. O ADR 0005 decidiu que são motores diferentes;
  esta costura escreve o contrato entre eles, para que o produtor real implemente contra algo declarado
  em vez de contra o que o juiz por acaso aceita.
evidence:
- E-ANCORA-202601
responsibility: Declarar e validar o envelope que o produtor entrega ao juiz — os cinco controles, a procedência
  do arquivo lido e os defeitos observados.
consumes:
- agregado da competência
- defeitos observados
produces:
- envelope do produtor
owner: fronteira
independent_proof: Um envelope sem o sha256 do arquivo lido é recusado; um envelope cujo sha256 difere
  do que o contrato ancorou é recusado; e linhas_invalidas é conferido contra a contagem de defeitos,
  não aceito de graça.
decision_ids:
- ADR-0005-MOTORES-SEPARADOS
rejected_alternatives:
- alternative: Deixar o juiz ler o Parquet do lago diretamente
  reason: O juiz passaria a depender do formato e do motor que julga — se a leitura distribuída perder
    uma coluna, os dois lados concordariam.
- alternative: Definir o envelope só quando o Spark existir
  reason: O produtor implementaria contra o que o juiz por acaso aceita, e a fronteira nasceria implícita
    — que é como C1, C4 e C5 apareceram.
swimlane:
  id: LANE-FRONTEIRA
  name: Fronteira lane
  owner: fronteira
  legs:
  - id: LEG-ENVELOPE-VINCULADO
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
        given: um envelope sem o sha256 do arquivo lido, e outro cujo sha256 difere do que o contrato
          ancorou
        when: o envelope é validado
        then: ambos são recusados — a âncora vale para UM arquivo, e sem esse vínculo uma republicação
          com os mesmos cinco controles passaria despercebida
      - id: B-2
        given: um envelope onde linhas_invalidas diverge da contagem de defeitos do tipo VALOR_ILEGIVEL,
          e outro com linhas_invalidas=0 e defeitos de truncamento, e outro produzido por um motor que
          não é o juiz
        when: o envelope é validado
        then: o primeiro é recusado; o segundo é ACEITO — truncamento é defeito numa linha válida, e a
          competência 2026-01 tem linhas_invalidas=0 com milhões de truncamentos; o terceiro é aceito
          sem que o juiz importe nada do motor produtor
      evals:
      - id: eval_1
        description: Sha256 ausente ou divergente do ancorado é recusado
        bash: pytest -q tests/test_envelope.py -k "sha_ausente or sha_divergente"
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
        reason: truncamento é defeito numa linha VÁLIDA; a competência 2026-01 tem linhas_invalidas=0
          com milhões de truncamentos, e a regra recusaria o dado correto
        instead: conferir linhas_invalidas só contra defeitos do tipo VALOR_ILEGIVEL
      do_not_touch:
      - _raw
      - cvg/docs/adrs
      rollback: Remover o validador de envelope e seus testes.
      observability: envelopes recusados por motivo
---
# Fronteira produtor-juiz

Separa quem produz o agregado de quem o julga. O ADR 0005 decidiu que são motores diferentes; esta costura escreve o contrato entre eles, para que o produtor real implemente contra algo declarado em vez de contra o que o juiz por acaso aceita.

## Responsibility

Declarar e validar o envelope que o produtor entrega ao juiz — os cinco controles, a procedência do arquivo lido e os defeitos observados.

## Independent proof

Um envelope sem o sha256 do arquivo lido é recusado; um envelope cujo sha256 difere do que o contrato ancorou é recusado; e linhas_invalidas é conferido contra a contagem de defeitos, não aceito de graça.

## Rejected alternatives

- **Deixar o juiz ler o Parquet do lago diretamente** — O juiz passaria a depender do formato e do motor que julga — se a leitura distribuída perder uma coluna, os dois lados concordariam.
- **Definir o envelope só quando o Spark existir** — O produtor implementaria contra o que o juiz por acaso aceita, e a fronteira nasceria implícita — que é como C1, C4 e C5 apareceram.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
