> Projetado de `LEG-JUIZO-NA-INGESTAO.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `58c75585de90bd69b0bc81d8edbd58363578c4866c112b01767243befc37dbd3`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-JUIZO-NA-INGESTAO
seam_id: SEAM-JUIZO-NA-INGESTAO
swimlane_id: LANE-JUIZO-NA-INGESTAO
observable_state: A Bronze publicada carrega o pacote ACEITO da ingestão
proof: Sem ACEITO, a Bronze não publica; com ACEITO, o commit nomeia o pacote.
requires: []
produces:
- bronze julgada
tasks:
- id: T-20260923-ingestao-julgada
  title: Julgar a ingestão com o segundo motor e publicar a Bronze só com ACEITO
  goal: Ler o arquivo bruto uma vez, na ingestão, com os dois motores.
  done_condition: Sobre uma landing vinculada, conduzir julga a Bronze contra o CSV; só com autorizado_publicar
    a Bronze publica, e o commit nomeia o pacote; sem autorização, nada é publicado.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  depends_on: []
  touches_paths:
  - src/medalhao/bronze.py
  creates_paths:
  - src/medalhao/ingestao.py
  - tests/test_ingestao.py
  behavior:
  - id: B-1
    given: a landing vinculada ao CSV, o contrato e o CSV original em _raw/
    when: a ingestão roda para a competência
    then: chama orquestracao.conduzir com um executar_leitura que mede a Bronze no motor Spark SEM gravar
      e lê o CSV pelo segundo motor, o leitor posicional em Python já selado, montando InsumosExecucao;
      só com Desfecho.autorizado_publicar a Bronze publica pelo protocolo que já existe — preparo, replaceWhere,
      reconferência —, e o userMetadata do commit nomeia o caminho_pacote e o sha256 do pacote do juízo.
      O orquestrador e o juiz selados são reusados, nunca alterados.
  - id: B-2
    given: um juízo que não autoriza — RECUSADO, ERRO ou ACEITO_SEM_ANCORA
    when: a ingestão termina
    then: a Bronze não publica nada, o pacote do juízo fica gravado como evidência com o motivo, e a ingestão
      devolve o veredito do orquestrador sem traduzi-lo; nenhum teste já existente de tests/test_bronze.py
      é editado.
  evals:
  - id: eval_1
    description: O juízo acontece na ingestão, com os dois motores
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in julga_na_ingestao_com_segundo_motor
      publica_bronze_so_com_aceito commit_da_bronze_nomeia_o_pacote; do python3 -m pytest --collect-only
      -q tests/test_ingestao.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_ingestao.py -k "julga_na_ingestao_com_segundo_motor
      or publica_bronze_so_com_aceito or commit_da_bronze_nomeia_o_pacote"'
    verifies:
    - B-1
  - id: eval_2
    description: Sem autorização, nada publica
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in recusado_nao_publica
      erro_nao_publica pacote_fica_como_evidencia; do python3 -m pytest --collect-only -q tests/test_ingestao.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_ingestao.py -k "recusado_nao_publica or erro_nao_publica or pacote_fica_como_evidencia"'
    verifies:
    - B-2
  - id: eval_3
    description: Orquestrador reusado, não alterado
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in reusa_conduzir_selado
      reusa_leitor_posicional; do python3 -m pytest --collect-only -q tests/test_ingestao.py -k "$c" 2>/dev/null
      | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_ingestao.py
      -k "reusa_conduzir_selado or reusa_leitor_posicional"'
    verifies:
    - B-1
  anti_patterns:
  - action: reimplementar o juiz ou o orquestrador dentro da ingestão
    reason: são selados; uma segunda versão pode divergir em silêncio
    instead: chamar orquestracao.conduzir
  - action: ler o CSV pelo Spark no lugar do leitor Python
    reason: dois motores iguais não se conferem (ADR 0006)
    instead: usar o leitor posicional já selado
  - action: publicar a Bronze antes do veredito
    reason: publicação sem juízo é o que o portão existe para impedir
    instead: publicar só com autorizado_publicar
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src/pda
  rollback: Reverter src/medalhao/bronze.py; remover ingestao.py e seu teste.
  observability: competências com Bronze publicada sem pacote no commit
source_seam_sha256: d43dcaf7d30366fd452f5f731ddde362f6b884ec328aad9eea8944a420c284dc
---
# A Bronze publicada carrega o pacote ACEITO da ingestão

## Observable proof

Sem ACEITO, a Bronze não publica; com ACEITO, o commit nomeia o pacote.

## Runnable leaves

- `T-20260923-ingestao-julgada` — Julgar a ingestão com o segundo motor e publicar a Bronze só com ACEITO: Sobre uma landing vinculada, conduzir julga a Bronze contra o CSV; só com autorizado_publicar a Bronze publica, e o commit nomeia o pacote; sem autorização, nada é publicado.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
