---
schema_version: 1
kind: seam
claim: derived
id: SEAM-LEITURA
name: Leitura posicional
description: Separa a extração dos bytes da interpretação monetária.
evidence:
- E-ESPECIE-TRUNCADA
responsibility: Ler os registros por posição declarada, preservando os bytes originais.
consumes:
- arquivo da competência
- contrato validado
produces:
- registros lidos
- defeitos observados
- sha256 computado na leitura
- totais por código da leitura
owner: leitura
independent_proof: O sha256 do arquivo é idêntico após a leitura, e cada campo vem da posição declarada
  mesmo com cabeçalho repetido.
decision_ids:
- ADR-0002-POSICIONAL
rejected_alternatives:
- alternative: Ler por nome de cabeçalho, renomeando a duplicata
  reason: A renomeação é por ordem de aparição, não por significado; se a fonte inverter as colunas, lê
    a errada sem acusar.
swimlane:
  id: LANE-LEITURA
  name: Leitura lane
  owner: leitura
  legs:
  - id: LEG-LEITURA-POSICIONAL
    observable_state: A leitura é posicional e não altera a fonte
    proof: sha256 inalterado; a coluna 12 traz código numérico e a 13 descrição de até 20 caracteres.
    requires:
    - contrato validado
    produces:
    - registros lidos
    - defeitos observados
    - sha256 computado na leitura
    - totais por código da leitura
    tasks:
    - id: T-20260921-leitura-posicional
      title: Ler a competência por posição, sem alterar a fonte
      goal: Extrair registros preservando os bytes e o defeito de origem.
      done_condition: sha256 idêntico antes e depois; código e descrição saem de posições distintas; registro
        ilegível entra em linhas_invalidas.
      effort: M
      profile: standard
      execution_backend: any
      required_tools:
      - git
      - bash
      - python3
      - pytest
      depends_on:
      - T-20260921-contrato-ancora
      touches_paths: []
      creates_paths:
      - src/pda/leitura.py
      - tests/test_leitura.py
      - tests/fixtures/competencia-min.csv
      behavior:
      - id: B-1
        given: um arquivo com Espécie repetida e o layout declarado, e outro em que as DUAS colunas de
          cabeçalho idêntico Espécie — índices 12 e 13 — tiveram os valores trocados entre si, deixando
          o cabeçalho byte a byte igual
        when: a leitura começa
        then: no primeiro o sha256 fica idêntico E a proteção de escrita é conferida antes de ler — W-1
          exige chmod 444 nos bytes de origem, e hash antes/depois não prova proteção, porque um arquivo
          em 0666 passa nesse teste quando ninguém escreve durante ele; a leitura recusa começar se _raw
          não estiver protegido. Código e descrição vêm dos índices 12 e 13; os totais por código que
          a leitura produz são somados em contexto decimal PRÓPRIO, com a precisão derivada do contrato,
          e o teste força um contexto global adverso e exige exatidão mesmo assim — a proteção escrita
          para a agregação não alcança a leitura, e uma referência corrompida faria a fronteira recusar
          um produtor correto com os testes da leitura verdes. No segundo a leitura BLOQUEIA, e o gate
          NÃO pode ser conferência de cabeçalho — cabeçalho idêntico não distingue as duas — e sim o formato
          de cada posição, MEDIDO nas 41.572.553 linhas — o índice 12 é sempre só dígitos, largura 2 após
          strip, alinhado à direita, e o 13 é sempre textual, alinhado à esquerda, sem uma única linha
          em que os dois sejam indistinguíveis; o teste falha se for satisfeito trocando colunas de nomes
          diferentes, porque é esta troca, de nomes iguais, que motivou o ADR 0002 e que os cinco controles
          preservam
      - id: B-2
        given: um registro cujo campo monetário é ilegível, os valores 'NaN', 'Infinity', '1_000' e '1e3',
          e os quatro exemplos do ADR 0004 — entre eles 'Pensão por Morte de ' com 20 caracteres brutos
          e 19 após strip
        when: os registros são contados
        then: o primeiro entra em linhas_invalidas com identidade, valor original e posição. Os quatro
          valores especiais TAMBÉM entram como inválidos, porque legível é o que casa a gramática monetária
          MEDIDA NA FONTE, e não o que Decimal() aceita. A fonte publica no formato brasileiro com preenchimento
          à esquerda — '        1.621,00', ponto de milhar e vírgula decimal, escala 2 nas 41.572.553
          linhas, zero recusas — de modo que Decimal(bruto) RECUSA toda linha legítima e a normalização
          é parte da gramática, não um passo implícito — retira o preenchimento, exige o padrão e só então
          converte. E cada valor convertido é conferido contra a ESCALA CARREGADA do contrato, não contra
          duas casas fixas, antes de entrar nos mapas de referência — é a verificação que o carregador
          delega a quem recebe o valor; fixar duas casas recusaria uma fonte futura com escala maior legitimamente
          declarada, e não conferir deixaria um contrato de escala 1 aceitar '1,23' com a precisão validada
          para outro domínio. Valor fora da escala contratada é defeito classificado, e valor NEGATIVO
          também, porque o ADR 0009 derivou a precisão sob soma monotônica. Uma gramática de ponto decimal
          recusaria a competência inteira — os quatro passam pelo construtor, e um NaN chegaria vivo aos
          extremos, onde min levanta InvalidOperation e transformaria defeito de UMA linha em ERRO da
          execução inteira. E a descrição emite defeito de IDENTIDADE COLAPSADA, sem tornar a linha inválida,
          quando cobre mais de um código — critério do ADR 0008, medido na competência inteira — 11 descrições
          cobrem 24 códigos, entre elas 'Pensão por Morte de ' fundindo 01, 03, 23 e 59. A unidade do
          defeito é a DESCRIÇÃO, não a ocorrência, ele só é emitido ao fim da varredura, porque colapso
          é propriedade do conjunto, e a contagem observada é conferida contra a CONTAGEM MEDIDA que o
          contrato carrega — senão a leitura poderia omitir um colapso, o envelope local reproduzir a
          mesma lista, e a comparação por identidade concordar com cardinalidade, mapas e controles todos
          corretos — um leitor incremental que emitisse a partir do segundo código deixaria sem registro
          todas as ocorrências anteriores, e a fronteira concordaria com a lista incompleta por ter a
          própria leitura como referência. Largura NÃO é critério — as 41.572.553 descrições têm 20 caracteres
          brutos, então bruto==20 acusaria toda linha, e strip==20 deixaria de fora justamente esse colapso
          de quatro códigos, cujo strip é 19
      evals:
      - id: eval_1
        description: Leitura posicional; _raw sem 444 bloqueia; Espécie 12 e 13 trocadas bloqueiam
        bash: pytest -q tests/test_leitura.py -k "sha256 or w1_protecao or especie_12_13_trocadas"
        verifies:
        - B-1
      - id: eval_2
        description: Ilegível vira inválida; NaN também; descrição que colapsa códigos acusa
        bash: pytest -q tests/test_leitura.py -k "invalida or gramatica_monetaria or identidade_colapsada"
        verifies:
        - B-2
      - id: eval_3
        description: A leitura reporta sua duração para a orquestração medir o total
        bash: pytest -q tests/test_leitura.py -k duracao
        verifies:
        - B-1
        - B-2
      anti_patterns:
      - action: escrever no arquivo de origem
        reason: destrói a prova de que a origem publicou aquilo
        instead: tratar _raw/ como somente leitura
      - action: ler colunas por nome de cabeçalho
        reason: Espécie repetida faz perder uma das duas em silêncio
        instead: ler por posição declarada no contrato
      - action: corrigir valor malformado durante a leitura
        reason: apaga o defeito antes da classificação
        instead: preservar e contar como linha inválida
      do_not_touch:
      - _raw
      rollback: Remover o leitor e seus testes.
      observability: registros lidos e defeitos por tipo
---
# Leitura posicional

Separa a extração dos bytes da interpretação monetária.

## Responsibility

Ler os registros por posição declarada, preservando os bytes originais.

## Independent proof

O sha256 do arquivo é idêntico após a leitura, e cada campo vem da posição declarada mesmo com cabeçalho repetido.

## Rejected alternatives

- **Ler por nome de cabeçalho, renomeando a duplicata** — A renomeação é por ordem de aparição, não por significado; se a fonte inverter as colunas, lê a errada sem acusar.

This derived seam is ready only while its cited evidence, named owner, contract,
and rejected alternatives remain intact.
