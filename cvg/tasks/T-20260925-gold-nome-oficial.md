---
id: T-20260925-gold-nome-oficial
title: "A Gold principal ganha o nome oficial, lido da Silver especie"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [src/medalhao/gold.py, tests/test_gold.py]
creates_paths: [tests/test_gold_nome_oficial.py]
source_note: "seamwise/legs/LEG-GOLD-NOME-OFICIAL.md#T-20260925-gold-nome-oficial"
created: "2026-09-25T00:00:00Z"
tags: []
owner: (none)
priority: P2
severity: feature
due_date: (none)
precondition: (none)
blocked_reason: (none)
security_class: (none)
source_action_item: (none)
tracker_ref: (none)
execution_backend: any
signed_off: true
signed_off_by: nobru
signed_off_at: 2026-09-25T13:55:00Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-25T14:16:57Z
signed_off_sig: hmac-sha256-v3:85d3c104:b7a66d23a7bb4bcb6622577804778218859183e1d1e03eb13d62c5fa72e4dce3
accepted_tier: 1
accepted_attempt_id: 257cc371-9a66-4e6a-9f63-89b7da5cb47a
accepted_authorization_ref: hmac-sha256-v3:85d3c104:b7a66d23a7bb4bcb6622577804778218859183e1d1e03eb13d62c5fa72e4dce3
acceptance_record_digest: sha256:126fe5a6dea22f6775cf1ec336955284e171919ce464705ddc88bd374ef796c7
---

# A Gold principal ganha o nome oficial, lido da Silver especie

> **Why:** Pôr o nome oficial da espécie na Gold principal, ligado pelo código, sem mudar nenhum controle e sem quebrar os testes selados que montam a Gold sem a especie. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Pôr o nome oficial da espécie na Gold principal, ligado pelo código, sem mudar nenhum controle e sem quebrar os testes selados que montam a Gold sem a especie. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-NOME-OFICIAL-GOLD; seam SEAM-GOLD-NOME-OFICIAL; swimlane LANE-GOLD-NOME-OFICIAL; capability leg LEG-GOLD-NOME-OFICIAL. Done condition: GOLD_COLUNAS termina em nome_oficial; com o caminho da Silver especie a Gold publica o nome, sem ele publica nulo com o motivo no commit; em tests/test_gold.py muda só a tupla literal de test_commit_carrega_a_forma; os testes de tests/test_gold_nome_oficial.py e os existentes passam.

## Behavior

- **B-1** — GIVEN uma Silver de benefícios e uma Silver especie da mesma competência, em tmp_path WHEN executar_gold_da_silver, executar_gold e agregar rodam com o parâmetro novo especie_destino (Optional[str], padrão None) apontando para a Silver especie THEN GOLD_COLUNAS passa a ser (especie_codigo, especie_descricao, vl_liquido_total, competencia, nome_oficial) — a coluna nova no FIM, onde a evolução de schema a põe; a Silver especie é lida numa versão V fixada UMA vez (versionAsOf), filtrada pela competência, e juntada DEPOIS do groupBy por especie_codigo, em left join — a contagem, a soma, o mínimo, o máximo e o total_por_codigo saem IDÊNTICOS aos de sem o nome; um código da Gold sem linha na especie devolve DIVERGE com a diferença NOME_OFICIAL_AUSENTE e nada é publicado (Regra 9: nunca nulo calado com a especie presente); o commit registra silver_especie = {caminho: especie_destino, versao: V} — o CAMINHO e a versão, porque o número da versão sozinho não identifica a tabela; _garantir_tabela declara nome_oficial como texto ANULÁVEL, sem CHECK; a reconferência, COM especie_destino, compara as 5 colunas, nome_oficial incluído, como multiconjunto — um nome perdido ou trocado diverge; SÓ sem especie_destino _conferir_tabela compara pelas colunas do esperado, para os testes existentes que montam o esperado com 4 colunas seguirem valendo. Numa tabela Gold já publicada com 4 colunas, a publicação com evolucao_aditiva=True acrescenta nome_oficial e deixa as outras competências intactas, com nome nulo.
- **B-2** — GIVEN a Gold chamada SEM especie_destino, como nos testes selados existentes WHEN a Gold é publicada THEN nome_oficial é nulo em toda linha — e a reconferência CONFERE que é nulo em toda linha do publicado, mesmo comparando as outras colunas pelo esperado —, e o commit registra nome_oficial: 'NAO_MEDIDO' com o motivo 'SEM_SILVER_ESPECIE' — nunca uma ausência calada; todos os controles saem como antes. Em tests/test_gold.py a ÚNICA mudança é acrescentar "nome_oficial" ao FIM da tupla literal de test_commit_carrega_a_forma; nenhum outro test_* muda nem sai. Em tests/test_gold_nome_oficial.py entram test_nome_oficial_vem_da_silver_especie, test_controles_iguais_com_e_sem_nome, test_codigo_sem_nome_diverge_e_nao_publica, test_sem_especie_nome_nulo_e_registrado, test_commit_nomeia_a_versao_da_especie, test_especie_lida_na_versao_fixada, test_reconferencia_acusa_nome_trocado e test_tabela_de_quatro_colunas_evolui_aditiva. Nenhum cenário usa skip, xfail ou importorskip; os testes gravam só em tmp_path, nunca no MinIO; a Silver especie de fixture é uma tabela Delta em tmp_path com o schema de medalhao.especie.

## Success Criteria

```bash
# eval_1: O nome vem da Silver especie e os controles não mudam
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in nome_oficial_vem_da_silver_especie controles_iguais_com_e_sem_nome commit_nomeia_a_versao_da_especie especie_lida_na_versao_fixada; do python3 -m pytest --collect-only -q tests/test_gold_nome_oficial.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_nome_oficial.py -k "nome_oficial_vem_da_silver_especie or controles_iguais_com_e_sem_nome or commit_nomeia_a_versao_da_especie or especie_lida_na_versao_fixada"'
}

# eval_2: Ausência não é silêncio, e a tabela evolui
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in codigo_sem_nome_diverge_e_nao_publica sem_especie_nome_nulo_e_registrado reconferencia_acusa_nome_trocado tabela_de_quatro_colunas_evolui_aditiva; do python3 -m pytest --collect-only -q tests/test_gold_nome_oficial.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold_nome_oficial.py -k "codigo_sem_nome_diverge_e_nao_publica or sem_especie_nome_nulo_e_registrado or reconferencia_acusa_nome_trocado or tabela_de_quatro_colunas_evolui_aditiva"'
}

# eval_3: A Gold existente segue igual
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in commit_carrega_a_forma reconfere_multiconjunto_das_linhas publica_em_um_unico_commit; do python3 -m pytest --collect-only -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gold.py -k "commit_carrega_a_forma or reconfere_multiconjunto_das_linhas or publica_em_um_unico_commit"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "O nome vem da Silver especie e os controles não mudam"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Ausência não é silêncio, e a tabela evolui"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A Gold existente segue igual"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: true
    expected_duration_sec: 10
retry_policy:
  max_iterations: 15
  circuit_breaker_no_progress: 3
  on_terminal_failure: park_with_context
agent_contract:
  version: 2
  read: [intent, behavior, contract, guardrails]
  produce: [code, tests]
  required_tools: [git, bash, python3, pytest, docker]
  timeout_minutes: 30
  sandbox_type: host
  output_artifacts: []
  mcp_dependencies: []
  emit: [pass, fail, retry_with_reason, parked_with_context]
  backend_metadata: {}
```

## Exit Check

```bash
eval_1 && eval_2 && eval_3
```

## Rollback Plan

Reverter src/medalhao/gold.py e tests/test_gold.py; remover tests/test_gold_nome_oficial.py.

## Observability Hooks

Gold publicada sem nome oficial

## Anti-Patterns

- Do not juntar a especie ANTES do groupBy: multiplicaria linhas e mudaria os controles; instead left join depois da agregação por código.
- Do not tornar especie_destino obrigatório: quebraria ~25 testes selados que montam a Gold sem ela; instead opcional, com o motivo registrado quando ausente.
- Do not editar outro teste existente além da tupla de test_commit_carrega_a_forma: a exceção à regra do teste selado é nomeada; instead testes novos no arquivo novo.

## Do-Not-Touch

- `_raw`
- `contracts`
- `cvg/docs/adrs`
- `src/pda`
- `src/ontologia`
- `infra`
- `src/produtor`
- `src/medalhao/especie.py`
- `src/medalhao/bronze.py`
- `src/medalhao/silver.py`
- `tests/test_gold_assuntos.py`
- `tests/test_performance_gold.py`
- `src/medalhao/gold_assuntos.py`

## Open Questions

(none — this task is fully specified)
