> Projetado de `LEG-CONTRATO-RECUSA-SEM-ANCORA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `de5cf2c0834888f7b1420c2b9283c77d04139100daddcea08d6d41f9f1a4e38e`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-CONTRATO-RECUSA-SEM-ANCORA
seam_id: SEAM-CONTRATO
swimlane_id: LANE-CONTRATO
observable_state: A fábrica recusa construir sem âncora medida
proof: Competência sem âncora devolve NAO_MEDIDO; com âncora incompleta (sem aprovador ou sem data) também.
requires: []
produces:
- contrato validado
tasks:
- id: T-20260921-contrato-ancora
  title: Carregar contrato, âncora e layout posicional
  goal: Fazer a ausência de prova bloquear em vez de virar verde.
  done_condition: Os cinco controles e o layout saem com procedência; sem âncora, ou sem aprovador, retorna
    NAO_MEDIDO como valor.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on: []
  touches_paths: []
  creates_paths:
  - src/pda/contrato.py
  - tests/test_contrato.py
  - contracts/competencia-202601.yaml
  behavior:
  - id: B-1
    given: um contrato com os cinco controles nomeados, a procedência, o layout posicional e os DOIS hashes
      — o do ZIP publicado e o do CSV extraído sobre o qual a âncora foi medida
    when: o contrato é carregado
    then: os controles monetários da ÂNCORA são recusados se vierem como float no YAML — um sum_vl_liquido
      sem aspas é float, e Decimal(str(v)) apagaria a origem enquanto Decimal(v) traria a aproximação
      binária; a recusa é do carregamento, antes de qualquer conversão, porque as recusas do agregador
      e do envelope não protegem o próprio referencial. Âncora, procedência, layout, os dois hashes, a
      CARDINALIDADE de códigos medida na competência inteira — 65 nesta, não os 51 amostrados pelo ADR
      0004 — a CONTAGEM MEDIDA DE COLAPSOS que o ADR 0008 exige junto dela, 11 descrições cobrindo 24
      códigos, os DEFEITOS CONHECIDOS pré-classificados com aprovador e data — os 11 colapsos como CONFIRMED_SOURCE_DEFECT
      — e a POLÍTICA DECIMAL com escala e não-negatividade saem juntas. Os controles da âncora são recusados
      se vierem não finitos, e as duas CONTAGENS se não forem inteiros não negativos, porque 'Infinity'
      alcançaria a derivação de precisão e False passaria por igualdade contra um inteiro legítimo — precisão,
      granularidade e modo de arredondamento são dados carregados do contrato, como o ADR 0003 exige,
      não escolha privada de quem implementa. Contrato SEM política decimal é NAO_MEDIDO, senão o agregador
      local fixa a sua, passa nos exemplos, e um produtor externo escolhe outra sem nada acusar. E contrato
      COM política que contradiz o ADR — HALF_UP, ou granularidade por campo — é RECUSADO no carregamento,
      não validado, porque um contrato contraditório deixaria o agregador entre obedecer ao contrato e
      obedecer à decisão vinculante; a validação confere a política contra o ADR, e nunca o contrário.
      A precisão é conferida por SUFICIÊNCIA e é DERIVADA, como manda o ADR 0009 — dígitos inteiros da
      âncora mais a escala máxima declarada para os intermediários, 11 + 3 = 14 nesta competência, sob
      a premissa DECLARADA de soma monotônica; o contrato declara a escala e a NÃO-NEGATIVIDADE do domínio,
      medidas na fonte, em vez de assumir um padrão, porque um acumulador que exceda o total quebraria
      a fórmula e 14 perderia o centavo. A escala declarada é verificada por QUEM RECEBE O VALOR, não
      pelo carregador, que roda antes da leitura e não vê registro nenhum — a leitura confere cada valor
      da fonte, e a fronteira confere cada monetário do envelope externo, ambos contra a escala do contrato;
      um valor que a exceda é defeito classificado, nunca somado em silêncio. Escala finita não é escala
      menor ou igual a 3, e sem essa verificação na etapa consumidora a precisão validada perderia informação
      durante a soma e ainda devolveria o mesmo total global arredondado, com os mapas por código errados.
      Precisão 6 com HALF_EVEN e arredondamento final satisfaz presença, modo e granularidade e devolve
      7.85218E+10 no lugar de 78.521.752.562,12; prec=13 representa o total e ainda assim perde o centavo
      ao SOMAR 78521752562,12 + 0,005 + 0,005, porque a perda acontece durante a soma e não na quantização.
      Contrato com precisão insuficiente é RECUSADO no carregamento, não descoberto durante a agregação.
      Falta o hash do CSV e também é NAO_MEDIDO, porque hoje só o ZIP tem checksum e a âncora foi medida
      no CSV — sem o par, trocar o CSV extraído não seria detectado; sem aprovador ou sem data, idem
  - id: B-2
    given: uma competência sem âncora no contrato
    when: o contrato é carregado
    then: retorna NAO_MEDIDO como valor, sem gravar nem encerrar o processo
  evals:
  - id: eval_1
    description: Hashes distintos; política ausente vira NAO_MEDIDO e política HALF_UP é recusada
    bash: pytest -q tests/test_contrato.py -k "ancorada or hash_zip_e_csv or sem_politica_decimal or politica_contradiz_adr"
    verifies:
    - B-1
  - id: eval_2
    description: Sem âncora retorna NAO_MEDIDO sem escrever em disco
    bash: pytest -q tests/test_contrato.py -k nao_medido
    verifies:
    - B-2
  - id: eval_3
    description: O layout declara as 14 posições, com Espécie em 12 e 13
    bash: pytest -q tests/test_contrato.py -k layout
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: gerar a âncora quando ela falta
    reason: um número que ninguém viu medir é um palpite
    instead: retornar NAO_MEDIDO
  - action: editar a âncora para um veredito passar
    reason: falsifica a verdade contra a qual tudo é medido
    instead: investigar; âncora revista exige nova aprovação
  - action: declarar colunas por nome no contrato
    reason: Espécie aparece duas vezes e o nome não decide qual
    instead: declarar o índice posicional
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  rollback: Remover o carregador de contrato e seus testes.
  observability: competências ancoradas no contrato
source_seam_sha256: 9d94d85f0fea3875545728e1414bd3c6410a81d8387fc04332f51735e5289155
---
# A fábrica recusa construir sem âncora medida

## Observable proof

Competência sem âncora devolve NAO_MEDIDO; com âncora incompleta (sem aprovador ou sem data) também.

## Runnable leaves

- `T-20260921-contrato-ancora` — Carregar contrato, âncora e layout posicional: Os cinco controles e o layout saem com procedência; sem âncora, ou sem aprovador, retorna NAO_MEDIDO como valor.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
