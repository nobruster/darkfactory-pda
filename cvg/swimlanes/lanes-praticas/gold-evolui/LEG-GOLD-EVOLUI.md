> Projetado de `LEG-GOLD-EVOLUI.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `f0efbad6a2639b2c9a0bb76243585c27ba7f2a7583331ec1925ac1dec9e8f32d`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-GOLD-EVOLUI
seam_id: SEAM-GOLD-EVOLUI
swimlane_id: LANE-GOLD-EVOLUI
observable_state: Gold evolui por padrão
proof: Coluna nova entra sem sinalizador.
requires:
- silver evolui
produces:
- gold evolui
tasks:
- id: T-20260925-gold-evolui-por-padrao
  title: A Gold evolui por padrão
  goal: Fazer a Gold principal evoluir de forma aditiva por padrão. Para rodar testes, o ÚNICO comando
    liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo>
    -k <cenarios>`.
  done_condition: publicar, executar_gold e executar_gold_da_silver têm evolucao_aditiva=True por padrão;
    em tests/test_gold_nome_oficial.py muda só o teste nomeado e entra o novo; todos passam.
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
  - T-20260925-silver-e-ingestao-evoluem-por-padrao
  touches_paths:
  - src/medalhao/gold.py
  - tests/test_gold_nome_oficial.py
  creates_paths: []
  behavior:
  - id: B-1
    given: uma Gold de 4 colunas já publicada em tmp_path
    when: a Gold publica com nome_oficial SEM passar evolucao_aditiva
    then: 'publicar, executar_gold e executar_gold_da_silver têm evolucao_aditiva=True por padrão: a coluna
      nova entra e a outra competência fica intacta; com evolucao_aditiva=False explícito, recusa como
      antes; a guarda recusa troca de tipo.'
  - id: B-2
    given: o tests/test_gold_nome_oficial.py da receita D, que esperava recusa SEM o sinalizador
    when: a tarefa atualiza os testes
    then: 'EXATAMENTE isto, e nada mais: em test_tabela_de_quatro_colunas_evolui_aditiva, a asserção de
      recusa sem o sinalizador passa a usar evolucao_aditiva=False EXPLÍCITO; entra test_gold_evolui_por_padrao_sem_sinalizador,
      que chama executar_gold_da_silver — a entrada da carga real — sem passar evolucao_aditiva, e não
      só publicar; os demais test_* do arquivo ficam como estão; test_gold.py não é tocado. Nenhum cenário
      usa skip, xfail ou importorskip; os testes gravam só em tmp_path, nunca no MinIO; nenhuma função
      para a sessão Spark da suíte.'
  evals:
  - id: eval_1
    description: A Gold evolui por padrão
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_evolui_por_padrao_sem_sinalizador
      tabela_de_quatro_colunas_evolui_aditiva; do python3 -m pytest --collect-only -q tests/test_gold_nome_oficial.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_gold_nome_oficial.py -k "gold_evolui_por_padrao_sem_sinalizador or tabela_de_quatro_colunas_evolui_aditiva"'
    verifies:
    - B-1
    - B-2
  - id: eval_2
    description: O nome oficial segue igual
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in nome_oficial_vem_da_silver_especie
      controles_iguais_com_e_sem_nome; do python3 -m pytest --collect-only -q tests/test_gold_nome_oficial.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_gold_nome_oficial.py -k "nome_oficial_vem_da_silver_especie or controles_iguais_com_e_sem_nome"'
    verifies:
    - B-2
  - id: eval_3
    description: A Gold existente segue igual
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in commit_carrega_a_forma
      publica_em_um_unico_commit reconfere_multiconjunto_das_linhas; do python3 -m pytest --collect-only
      -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit
      1; }; done; python3 -m pytest -q tests/test_gold.py -k "commit_carrega_a_forma or publica_em_um_unico_commit
      or reconfere_multiconjunto_das_linhas"'
    verifies:
    - B-2
  anti_patterns:
  - action: tocar test_gold.py
    reason: a guarda test_testes_leves protege os corpos
    instead: só o arquivo do nome oficial
  - action: apagar a asserção de recusa
    reason: a recusa com False explícito continua sendo contrato
    instead: trocar para False explícito
  - action: desligar a guarda
    reason: Regra 5
    instead: manter verificar_evolucao
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
  - src/medalhao/gold_assuntos.py
  - tests/test_assuntos_nome_oficial.py
  rollback: Reverter os caminhos tocados e remover os criados.
  observability: Gold recusada por coluna nova
source_seam_sha256: be19c48095fe422331a058d79a30fdc1d43debe6651f5e4065714640ed5f9f35
---
# Gold evolui por padrão

## Observable proof

Coluna nova entra sem sinalizador.

## Runnable leaves

- `T-20260925-gold-evolui-por-padrao` — A Gold evolui por padrão: publicar, executar_gold e executar_gold_da_silver têm evolucao_aditiva=True por padrão; em tests/test_gold_nome_oficial.py muda só o teste nomeado e entra o novo; todos passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
