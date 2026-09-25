> Projetado de `LEG-ASSUNTOS-EVOLUEM.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `a69ee49b156550a7a1291cf6ead1105eaafa1b84eccaf473ce1d01e5b12cd185`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-ASSUNTOS-EVOLUEM
seam_id: SEAM-ASSUNTOS-EVOLUEM
swimlane_id: LANE-ASSUNTOS-EVOLUEM
observable_state: Assuntos evoluem por padrão
proof: fat evolui sem sinalizador.
requires:
- gold evolui
produces:
- assuntos evoluem
tasks:
- id: T-20260925-assuntos-evoluem-por-padrao
  title: Os assuntos evoluem por padrão
  goal: Fazer a Gold por assuntos evoluir de forma aditiva por padrão. Para rodar testes, o ÚNICO comando
    liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo>
    -k <cenarios>`.
  done_condition: _executar_gold_assuntos tem evolucao_aditiva=True por padrão; em tests/test_assuntos_nome_oficial.py
    muda só o teste nomeado e entra o novo; todos passam.
  effort: S
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  depends_on:
  - T-20260925-gold-evolui-por-padrao
  touches_paths:
  - src/medalhao/gold_assuntos.py
  - tests/test_assuntos_nome_oficial.py
  creates_paths: []
  behavior:
  - id: B-1
    given: uma fat_especie já publicada com o schema antigo em tmp_path
    when: os assuntos publicam com nome_oficial SEM passar evolucao_aditiva
    then: '_executar_gold_assuntos tem evolucao_aditiva=True por padrão: a coluna nova entra e a outra
      competência fica intacta; com evolucao_aditiva=False explícito, recusa como antes.'
  - id: B-2
    given: o tests/test_assuntos_nome_oficial.py da receita D
    when: a tarefa atualiza os testes
    then: 'EXATAMENTE isto: em test_fat_existente_evolui_e_outra_competencia_intacta, a asserção de recusa
      sem o sinalizador passa a usar evolucao_aditiva=False EXPLÍCITO; entra test_fat_evolui_por_padrao_sem_sinalizador;
      os demais test_* ficam como estão; test_gold_assuntos.py não é tocado. Nenhum cenário usa skip,
      xfail ou importorskip; os testes gravam só em tmp_path, nunca no MinIO; nenhuma função para a sessão
      Spark da suíte.'
  evals:
  - id: eval_1
    description: A fat evolui por padrão
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_evolui_por_padrao_sem_sinalizador
      fat_existente_evolui_e_outra_competencia_intacta; do python3 -m pytest --collect-only -q tests/test_assuntos_nome_oficial.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_assuntos_nome_oficial.py -k "fat_evolui_por_padrao_sem_sinalizador or fat_existente_evolui_e_outra_competencia_intacta"'
    verifies:
    - B-1
    - B-2
  - id: eval_2
    description: O nome da fat segue igual
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_nome_da_mesma_especie_da_gold
      fat_controles_iguais_com_e_sem_nome; do python3 -m pytest --collect-only -q tests/test_assuntos_nome_oficial.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_assuntos_nome_oficial.py -k "fat_nome_da_mesma_especie_da_gold or fat_controles_iguais_com_e_sem_nome"'
    verifies:
    - B-2
  - id: eval_3
    description: Os assuntos existentes seguem iguais
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in fat_especie_fecha_com_a_ancora
      publica_com_replacewhere commit_nomeia_versoes_lidas; do python3 -m pytest --collect-only -q tests/test_gold_assuntos.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_gold_assuntos.py -k "fat_especie_fecha_com_a_ancora or publica_com_replacewhere
      or commit_nomeia_versoes_lidas"'
    verifies:
    - B-2
  anti_patterns:
  - action: tocar test_gold_assuntos.py
    reason: a guarda protege os corpos
    instead: só o arquivo do nome oficial
  - action: apagar a asserção de recusa
    reason: a recusa com False explícito é contrato
    instead: False explícito
  - action: overwriteSchema
    reason: proibido (test_gold_assuntos.py:245)
    instead: mergeSchema com a guarda
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
  - src/medalhao/silver.py
  - src/medalhao/ingestao.py
  - src/medalhao/gold.py
  - tests/test_gold_nome_oficial.py
  rollback: Reverter os caminhos tocados e remover os criados.
  observability: fat recusada por coluna nova
source_seam_sha256: e86b2434e3a9d9550e5a9abce5920b8634515c96f0f4a3e389fdf4a72a7be733
---
# Assuntos evoluem por padrão

## Observable proof

fat evolui sem sinalizador.

## Runnable leaves

- `T-20260925-assuntos-evoluem-por-padrao` — Os assuntos evoluem por padrão: _executar_gold_assuntos tem evolucao_aditiva=True por padrão; em tests/test_assuntos_nome_oficial.py muda só o teste nomeado e entra o novo; todos passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
