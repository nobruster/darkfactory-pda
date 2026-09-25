> Projetado de `LEG-SILVER-E-INGESTAO-EVOLUEM.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `d6255fee48f5e6f6fe0ea953526ad29ea1aa81a34ca0eab54f7b184e05367039`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-SILVER-E-INGESTAO-EVOLUEM
seam_id: SEAM-SILVER-E-INGESTAO-EVOLUEM
swimlane_id: LANE-SILVER-E-INGESTAO-EVOLUEM
observable_state: Silver e ingestão evoluem por padrão
proof: Coluna nova entra; tipo trocado recusa.
requires:
- sessao declarada
produces:
- silver evolui
tasks:
- id: T-20260925-silver-e-ingestao-evoluem-por-padrao
  title: A Silver e a ingestão evoluem por padrão
  goal: Fazer a Silver e a ingestão evoluírem de forma aditiva por padrão, com a guarda. Para rodar testes,
    o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3
    -m pytest <arquivo> -k <cenarios>`.
  done_condition: executar_classificacao e executar_ingestao têm evolucao_aditiva=True por padrão; os
    testes de tests/test_delta_padroes_silver.py passam.
  effort: M
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  depends_on:
  - T-20260925-sessao-e-bronze-com-padroes-delta
  touches_paths:
  - src/medalhao/silver.py
  - src/medalhao/ingestao.py
  creates_paths:
  - tests/test_delta_padroes_silver.py
  behavior:
  - id: B-1
    given: uma Bronze de fixture em tmp_path
    when: a Silver (executar_classificacao) e a ingestão (executar_ingestao) publicam
    then: 'as duas passam a ter evolucao_aditiva=True por padrão: coluna nova entra; troca de tipo e coluna
      removida continuam recusadas pela guarda verificar_evolucao; evolucao_aditiva=False explícito recusa
      coluna nova; a ingestão repassa o valor recebido à Bronze.'
  - id: B-2
    given: os testes selados de test_silver.py, test_ingestao.py e test_orquestracao.py
    when: a tarefa termina
    then: nenhum teste existente muda e todos passam; em tests/test_delta_padroes_silver.py entram test_silver_evolui_por_padrao,
      test_silver_troca_de_tipo_recusada, test_silver_coluna_removida_recusada, test_silver_evolucao_desligada_recusa,
      test_ingestao_evolui_por_padrao e test_ingestao_repassa_o_sinalizador. Nenhum cenário usa skip,
      xfail ou importorskip; os testes gravam só em tmp_path, nunca no MinIO; nenhuma função para a sessão
      Spark da suíte.
  evals:
  - id: eval_1
    description: A Silver evolui por padrão
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in silver_evolui_por_padrao
      silver_troca_de_tipo_recusada silver_coluna_removida_recusada silver_evolucao_desligada_recusa;
      do python3 -m pytest --collect-only -q tests/test_delta_padroes_silver.py -k "$c" 2>/dev/null |
      grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_delta_padroes_silver.py
      -k "silver_evolui_por_padrao or silver_troca_de_tipo_recusada or silver_coluna_removida_recusada
      or silver_evolucao_desligada_recusa"'
    verifies:
    - B-1
  - id: eval_2
    description: A ingestão evolui e repassa
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in ingestao_evolui_por_padrao
      ingestao_repassa_o_sinalizador; do python3 -m pytest --collect-only -q tests/test_delta_padroes_silver.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_delta_padroes_silver.py -k "ingestao_evolui_por_padrao or ingestao_repassa_o_sinalizador"'
    verifies:
    - B-1
  - id: eval_3
    description: O que existia segue igual
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in resolve_versao_uma_vez
      metadados_do_commit_dono_da_competencia reverte_so_a_competencia; do python3 -m pytest --collect-only
      -q tests/test_silver.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_silver.py -k "resolve_versao_uma_vez or metadados_do_commit_dono_da_competencia
      or reverte_so_a_competencia"'
    verifies:
    - B-2
  anti_patterns:
  - action: desligar a guarda verificar_evolucao
    reason: troca de tipo passaria (Regra 5)
    instead: manter antes do mergeSchema
  - action: editar um teste existente
    reason: acrescentar, não mudar
    instead: arquivo novo
  - action: mudar publicar_competencia
    reason: fica False por decisão (ADR 0017)
    instead: só as entradas
  do_not_touch:
  - _raw
  - contracts
  - cvg/docs/adrs
  - src/pda
  - src/ontologia
  - src/produtor
  - infra
  - tests/test_gold.py
  - tests/test_gold_assuntos.py
  - tests/test_testes_leves.py
  - src/medalhao/bronze.py
  - src/medalhao/gold.py
  - src/medalhao/gold_assuntos.py
  - tests/test_delta_padroes.py
  rollback: Reverter os caminhos tocados e remover os criados.
  observability: cargas da Silver recusadas por coluna nova
source_seam_sha256: 2e3fc27055ae967912baed21688a5ea769173298719056c196c509d6f18645ed
---
# Silver e ingestão evoluem por padrão

## Observable proof

Coluna nova entra; tipo trocado recusa.

## Runnable leaves

- `T-20260925-silver-e-ingestao-evoluem-por-padrao` — A Silver e a ingestão evoluem por padrão: executar_classificacao e executar_ingestao têm evolucao_aditiva=True por padrão; os testes de tests/test_delta_padroes_silver.py passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
