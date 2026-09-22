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
- sha256 computado na leitura
- totais por código da leitura
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
    then: os três são recusados. O hash computado chega ao validador como capacidade própria, sha256 computado
      na leitura, que a leitura declara entre seus produtos e a fronteira exige entre seus requisitos
      — não como mais um campo do envelope, senão os dois campos viriam da mesma mão e repetir o ancorado
      bastaria. O terceiro é recusado porque o hash que a leitura computou discorda do que o envelope
      declara, e é esse caso, não a mera igualdade, que prova o vínculo. Para produtor externo, que o
      ADR 0006 permite, vale o mesmo — sem a capacidade computada por quem leu os bytes, o envelope é
      recusado por falta de insumo, nunca aceito por ausência de contraditório
  - id: B-2
    given: um envelope onde linhas_invalidas diverge dos defeitos do tipo VALOR_ILEGIVEL, outro com linhas_invalidas=0
      e defeitos de truncamento, outro produzido por motor que não é o juiz, outro cujos três controles
      monetários vêm como número JSON, e outro que OMITE truncamentos que a leitura observou
    when: o envelope é validado
    then: o primeiro é recusado; o segundo é ACEITO — identidade colapsada é defeito numa linha VÁLIDA,
      e a competência 2026-01 tem linhas_invalidas=0 com os 11 defeitos de colapso que o ADR 0008 contratou,
      um por descrição, não um por ocorrência; os dois controles de CONTAGEM são inteiros não negativos,
      recusando float e booleano, porque em Python 41572553.0 == 41572553 e False == 0, e um envelope
      com contagem fracionária ou booleana satisfaria a comparação dos cinco controles; o terceiro é aceito
      sem que o juiz importe nada do motor produtor. O quarto é RECUSADO na fronteira, antes de qualquer
      conversão — TODO campo monetário do envelope é contratado como string ou Decimal FINITO, NÃO NEGATIVO
      e dentro da escala do contrato — 'NaN', 'sNaN', 'Infinity' e Decimal não finito satisfazem o tipo
      e são RECUSADOS pelo domínio, e '-0.01' também, porque a não-negatividade do ADR 0009 vale para
      o produtor externo e carregá-la no contrato não demonstra que a fronteira a aplica; recusar alguns
      negativos por divergência numérica depois não cobre a classificação do domínio. O valor original
      fica preservado na evidência, porque a gramática brasileira roda sobre o CSV e não alcança produtor
      externo; a recusa é do envelope, nunca uma InvalidOperation levantada ao comparar. Há UMA representação
      de ausência declarada no schema, o literal JSON null, para o caso em que nenhum registro é legível
      e min e max não têm valor; campo omitido ou marcador textual é recusado, senão o caso que a agregação
      prevê morreria na validação antes de o juízo comparar, os três controles globais e também cada total
      por código, porque R-4 e o ADR 0003 valem para todo dinheiro e não só para os três; um envelope
      com controles em string e totais por espécie como número JSON satisfaria uma recusa escrita só para
      os três. Converter com Decimal(str(v)) apagaria a prova de que veio float, então a recusa do agregador
      local não cobre produtor externo. O quinto é RECUSADO por omissão — e a conferência é POR IDENTIDADE
      de cada defeito, a que a leitura produz com valor original e posição, não por contagem e tipo —
      dois defeitos A e B do mesmo tipo, com A duplicado e B omitido, preservam contagem e tipo, cada
      entrada declarada recebe sua classificação única, e B nunca é classificado, violando R-6 com juízo
      e rederivação concordando entre si. Conferir por contagem deixaria a substituição passar, e só a
      omissão seria vista. E o envelope declara o agregado POR CÓDIGO de espécie, com as chaves conferidas
      contra a cardinalidade ANCORADA no contrato — medida na competência inteira, nunca os 51 do ADR
      0004, que saíram de ~3 milhões de linhas; exigir 51 recusaria esta competência, que tem 65 códigos,
      entre eles o '60' com 1.395 ocorrências em 41,5 milhões. E cada total por código do envelope é CONFERIDO
      contra os totais por código DA LEITURA, capacidade própria que a leitura produz e a fronteira exige
      — dois valores de origens distintas, o declarado pelo produtor e o de referência; com um mapa só,
      deslocar valores entre códigos seria aprovado por comparação consigo mesmo. Os dois mapas trafegam
      como soma EXATA, não quantizada, e a comparação é exata — um código cuja soma é 2,345 chega 2,345
      dos dois lados, e quantizar um só faria a fronteira recusar dois lados corretos. A soma global vem
      dos valores originais, NUNCA dos totais por código já arredondados, porque arredondar uma vez no
      total é camada do ADR 0007 herdada do 0003 — dois códigos de 2,345 dão 4,69 no total e 4,68 somando
      grupos arredondados. Um produtor que agrupasse por descrição e atribuísse o total ao primeiro código,
      zerando os demais, manteria todas as chaves, os cinco controles, hashes e defeitos idênticos, e
      só a comparação por valor o pega; R-3 prova-se por valor, não por forma, e a referência não vem
      do agregador julgado, pelo mesmo motivo do ADR 0005
  evals:
  - id: eval_1
    description: Sha ausente, divergente, ou copiado de outro arquivo lido é recusado
    bash: pytest -q tests/test_envelope.py -k "sha_ausente or sha_divergente or sha_copiado_outro_arquivo"
    verifies:
    - B-1
  - id: eval_2
    description: Float em todo campo monetário; defeito por identidade; total por código conferido
    bash: pytest -q tests/test_envelope.py -k "invalidas_por_tipo or float_em_todo_monetario or defeito_por_identidade
      or total_por_codigo"
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
    reason: identidade colapsada é defeito numa linha VÁLIDA; a competência 2026-01 tem linhas_invalidas=0
      com os 11 colapsos do ADR 0008, e a regra recusaria o dado correto
    instead: conferir linhas_invalidas só contra defeitos do tipo VALOR_ILEGIVEL
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  rollback: Remover o validador de envelope e seus testes.
  observability: envelopes recusados por motivo
source_seam_sha256: 895f2994f6f10b3578de160f08b43bfbbb8cb0523c95ced8c7ef6e4dc5c1b5ce
---
# O envelope liga o agregado ao arquivo que o gerou

## Observable proof

Envelope sem sha256 do arquivo é recusado; sha256 divergente do ancorado é recusado; linhas_invalidas incoerente com os defeitos observados é recusado.

## Runnable leaves

- `T-20260921-envelope-fronteira` — Declarar e validar o envelope entre produtor e juiz: O envelope declara os cinco controles, o sha256 do arquivo lido e os defeitos; validação recusa sha256 ausente, divergente, ou linhas_invalidas incoerente.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
