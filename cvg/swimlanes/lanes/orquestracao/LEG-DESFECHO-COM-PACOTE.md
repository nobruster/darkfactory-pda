> Projetado de `LEG-DESFECHO-COM-PACOTE.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `ef94a338230e4c8ae2880216cb2f2b8b4a8f12e376ad0f070a9aa3ac6e2d2f4e`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-DESFECHO-COM-PACOTE
seam_id: SEAM-ORQUESTRACAO
swimlane_id: LANE-ORQUESTRACAO
observable_state: Todo caminho termina com pacote e código de saída
proof: Os quatro desfechos gravam pacote; uma exceção dentro da leitura vira ERRO com pacote; o tempo
  é medido do início ao veredito.
requires:
- contrato validado
- veredito classificado
- pacote de evidência
produces:
- desfecho da execução
tasks:
- id: T-20260921-orquestra-desfecho
  title: Decidir o desfecho e garantir o pacote em todo caminho
  goal: Dar dono ao fluxo — sem ele a lacuna migra de etapa em etapa.
  done_condition: Os quatro desfechos gravam pacote com código próprio; exceção real vira ERRO; o tempo
    total é medido e registrado no pacote. R-9 é should e NÃO é declarado coberto aqui — medir com relógio
    simulado não demonstra orçamento de competência completa, e inventar recusa por timeout seria afrouxar
    o que a tech-spec não pediu.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  depends_on:
  - T-20260921-evidencia-packet
  touches_paths: []
  creates_paths:
  - src/pda/orquestracao.py
  - tests/test_orquestracao.py
  behavior:
  - id: B-1
    given: execução sem âncora, execução que bate, e a execução de R-7 — um centavo alterado nos bytes
      do arquivo, com o sha256 do arquivo ALTERADO reancorado no contrato, de modo que a fronteira passe
      e o juízo seja quem decide
    when: a orquestração conduz o fluxo inteiro
    then: as três gravam pacote, com ACEITO_SEM_ANCORA, ACEITO e RECUSADO de códigos de saída distintos,
      e só ACEITO autoriza publicar. O caso de R-7 é UMA prova conjunta, não duas separadas — a alteração
      é real nos bytes, a recusa vem do JUÍZO comparando contra a âncora monetária original, e o teste
      FALHA se um juízo permissivo for injetado. Sem reancorar, a fronteira recusaria pelo sha256 antes
      do juízo comparar, e o teste ficaria verde com juízo permissivo — provando metade do que R-7 escreveu
  - id: B-2
    given: uma exceção real levantada dentro da leitura, uma execução com contrato de política HALF_UP,
      e uma execução cujo tempo total é medido
    when: a orquestração conduz a execução
    then: o contrato HALF_UP termina em RECUSADO com pacote gravado, sem chegar à leitura — caminho exercido
      aqui, não só declarado no contrato; a exceção vira ERRO com pacote gravado, e o tempo do início
      da leitura ao veredito é medido e REGISTRADO no pacote, sem virar recusa — R-9 é should, e o pacote
      passa a carregar o número para que a cobertura de R-9 seja decidida contra competência real, não
      contra relógio simulado. Se o PRÓPRIO gravador falhar — permissão negada, disco cheio — o desfecho
      é ERRO com código próprio e a falha vai para a saída de erro; nunca se devolve ACEITO sem pacote,
      porque autorização sem evidência é o que esta fábrica existe para impedir
  evals:
  - id: eval_1
    description: R-7 numa prova só — centavo alterado, hash reancorado, juízo permissivo falha
    bash: pytest -q tests/test_orquestracao.py -k "desfechos or r7_centavo_reancorado"
    verifies:
    - B-1
  - id: eval_2
    description: Exceção real vira ERRO; o tempo é medido no total
    bash: pytest -q tests/test_orquestracao.py -k "excecao or tempo_total"
    verifies:
    - B-2
  - id: eval_3
    description: Só ACEITO autoriza publicar
    bash: pytest -q tests/test_orquestracao.py -k autoriza
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: encerrar o processo dentro de uma etapa
    reason: o pacote prometido nunca é gravado
    instead: retornar o veredito e deixar a orquestração decidir
  - action: medir o tempo por etapa
    reason: etapa rápida com o resto lento passaria
    instead: medir do início da leitura ao veredito
  - action: tratar ACEITO_SEM_ANCORA como autorização
    reason: a palavra aceito nomeia o término, não a prova
    instead: só ACEITO autoriza, com os cinco controles conferidos
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  rollback: Remover a orquestração e seus testes.
  observability: desfechos por tipo e segundos até o veredito
source_seam_sha256: d60e54d99ed9a2cf2cefcb80089ef00582b4abf3140d7695f3c09ec76633dd8b
---
# Todo caminho termina com pacote e código de saída

## Observable proof

Os quatro desfechos gravam pacote; uma exceção dentro da leitura vira ERRO com pacote; o tempo é medido do início ao veredito.

## Runnable leaves

- `T-20260921-orquestra-desfecho` — Decidir o desfecho e garantir o pacote em todo caminho: Os quatro desfechos gravam pacote com código próprio; exceção real vira ERRO; o tempo total é medido e registrado no pacote. R-9 é should e NÃO é declarado coberto aqui — medir com relógio simulado não demonstra orçamento de competência completa, e inventar recusa por timeout seria afrouxar o que a tech-spec não pediu.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
