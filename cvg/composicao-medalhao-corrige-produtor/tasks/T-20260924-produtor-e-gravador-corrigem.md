---
id: T-20260924-produtor-e-gravador-corrigem
title: "Produtor e gravador com a gramática do juiz, carga única e rejeitos com o texto bruto"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-gramatica-do-juiz]
supersedes: (none)
touches_paths: [src/produtor/spark_produtor.py, src/produtor/gravar_lago.py, tests/test_produtor.py]
creates_paths: []
source_note: "seamwise/legs/LEG-PRODUTOR-E-GRAVADOR-CORRIGEM.md#T-20260924-produtor-e-gravador-corrigem"
created: "2026-09-24T00:00:00Z"
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
signed_off_at: 2026-09-25T00:26:26Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-25T00:50:06Z
signed_off_sig: hmac-sha256-v3:85d3c104:4b4f2a06f6e44c59d2043adaf54a9596e6db860a6ce45352eacda0a83ab9ec48
accepted_tier: 1
accepted_attempt_id: bda78fe7-6e30-4c13-b367-1655af26c45a
accepted_authorization_ref: hmac-sha256-v3:85d3c104:4b4f2a06f6e44c59d2043adaf54a9596e6db860a6ce45352eacda0a83ab9ec48
acceptance_record_digest: sha256:3048f768d6f7788c7412567e74335d2a951252d454b05af1daff5b5302d30c14
---

# Produtor e gravador com a gramática do juiz, carga única e rejeitos com o texto bruto

> **Why:** Corrigir no produtor e no gravador, NUMA tarefa só, os defeitos latentes que a adoção fixou em teste — juntos porque dividem as fixtures de tests/test_produtor.py. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Corrigir no produtor e no gravador, NUMA tarefa só, os defeitos latentes que a adoção fixou em teste — juntos porque dividem as fixtures de tests/test_produtor.py. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-CORRIGE-PRODUTOR; seam SEAM-PRODUTOR-E-GRAVADOR-CORRIGEM; swimlane LANE-PRODUTOR-E-GRAVADOR-CORRIGEM; capability leg LEG-PRODUTOR-E-GRAVADOR-CORRIGEM. Done condition: src/produtor/spark_produtor.py e src/produtor/gravar_lago.py usam a gramática do juiz, declaram ANSI, recusam espécie fora do padrão e valor fora da precisão; o gravador recusa partição ou rejeitos já ocupados e grava os rejeitos com o texto bruto fora da tabela; só o que B-2 nomeia muda em tests/test_produtor.py; todos passam.

## Behavior

- **B-1** — GIVEN o CSV de fixture, e um destino e um diretório de rejeitos em tmp_path WHEN produzir e o main do gravador rodam, cada um num processo filho sem S3_* THEN os dois convertem o valor por gramatica.valor_decimal e validam a espécie por gramatica.especie_valida — as regexes locais saem dos dois arquivos —, e as duas sessões declaram spark.sql.ansi.enabled=true; '1,5' entra como 1.50 e '-5,00' conta em linhas_invalidas; QUALQUER linha de espécie inválida recusa o arquivo — produzir levanta ProdutorRecusado('ESPECIE_FORA_DO_PADRAO', contagem) e o main do produtor imprime PRODUTOR=RECUSADO sem escrever envelope; o gravador imprime LAGO=RECUSADO sem gravar nada; valor que casa com a gramática mas não cabe na precisão do contrato recusa o arquivo nos dois com o motivo VALOR_FORA_DA_PRECISAO. O gravador, ANTES de gravar, recusa com LAGO=RECUSADO se a partição competencia=<c> do destino OU a do diretório de rejeitos já tem QUALQUER objeto — motivos PARTICAO_JA_CARREGADA e REJEITOS_JA_OCUPADOS; nada é sobrescrito nem apagado, e a retomada depois de uma tentativa que falhou é decisão do dono. Premissa declarada: um escritor por competência; se outra carga entrar entre a conferência e a escrita, a releitura acusa LAGO=DIVERGE. A TABELA continua como hoje: TODAS as linhas do CSV, a de valor inválido com vl_liquido NULL — os rejeitos são uma CÓPIA a mais, não uma segregação, para o vinculador e a Bronze seguirem vendo a contagem inteira. Grava primeiro os rejeitos — as linhas de valor inválido, em Parquet, com as colunas brutas do CSV COMO VIERAM e o motivo VALOR_FORA_DA_GRAMATICA — e depois a tabela; relê os dois, e a contagem de rejeitos relida tem de ser igual a linhas_invalidas, senão LAGO=DIVERGE; sem linha inválida, nenhum rejeito é criado. --rejeitos tem padrão s3a://landing/pda/beneficios-emitidos-rejeitos, FORA do diretório da tabela, para a Bronze não o ler.
- **B-2** — GIVEN o tests/test_produtor.py selado pela adoção, que fixava o comportamento antigo WHEN a tarefa atualiza os testes THEN EXATAMENTE estas mudanças nas funções test_*, e nenhuma outra: SAEM test_gramatica_atual_fixada, test_codigo_vazio_fora_do_total_fixado e test_primeira_grava_segunda_diverge_sem_apagar; ENTRAM test_gramatica_do_juiz, test_especie_fora_do_padrao_recusa, test_especie_fora_do_padrao_nao_grava, test_sessao_do_produtor_ansi, test_valor_fora_da_precisao_recusa, test_segunda_carga_recusada_sem_gravar (a primeira dá LAGO=GRAVADO, a segunda LAGO=RECUSADO, e os objetos da primeira ficam os mesmos em nome e quantidade), test_residuo_de_rejeitos_recusa, test_rejeitos_guardam_o_texto_bruto, test_rejeitos_fora_da_tabela e test_contagem_de_rejeitos_reconferida; MUDAM só os valores esperados de test_produtor_totais_literais_da_fixture, test_codigos_com_mesma_descricao_somam_separados e test_cada_controle_divergente_acusa, recalculados à mão pela gramática nova — neste último pode mudar também QUAL linha cada mutação altera, para uma linha VÁLIDA pela gramática nova, mantendo a asserção de que só o controle alterado diverge (a linha '-5,00' agora é inválida, e alterá-la mudaria três controles de uma vez). As funções que não são test_* — LINHAS, ESPERADO, ESPERADO_POR_CODIGO, a âncora da fixture contratos, _rodar_main (que passa a mandar --rejeitos em tmp_path) e _Leitor (que passa a substituir só a releitura da tabela, não a dos rejeitos) — mudam só para isso; a linha de espécie vazia sai da fixture principal para uma fixture própria. Os demais test_* ficam como estão e passam. Nenhum cenário usa skip, xfail ou importorskip.

## Success Criteria

```bash
# eval_1: A gramática do juiz nos dois
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gramatica_do_juiz produtor_totais_literais_da_fixture codigos_com_mesma_descricao_somam_separados especie_fora_do_padrao_recusa sessao_do_produtor_ansi valor_fora_da_precisao_recusa; do python3 -m pytest --collect-only -q tests/test_produtor.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_produtor.py -k "gramatica_do_juiz or produtor_totais_literais_da_fixture or codigos_com_mesma_descricao_somam_separados or especie_fora_do_padrao_recusa or sessao_do_produtor_ansi or valor_fora_da_precisao_recusa"'
}

# eval_2: Carga única e rejeitos
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in segunda_carga_recusada_sem_gravar residuo_de_rejeitos_recusa rejeitos_guardam_o_texto_bruto rejeitos_fora_da_tabela contagem_de_rejeitos_reconferida especie_fora_do_padrao_nao_grava; do python3 -m pytest --collect-only -q tests/test_produtor.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_produtor.py -k "segunda_carga_recusada_sem_gravar or residuo_de_rejeitos_recusa or rejeitos_guardam_o_texto_bruto or rejeitos_fora_da_tabela or contagem_de_rejeitos_reconferida or especie_fora_do_padrao_nao_grava"'
}

# eval_3: O resto igual, os dois medindo igual
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gravador_mede_igual_ao_produtor cada_controle_divergente_acusa destino_padrao_e_o_landing_de_hoje filho_sem_credencial_s3 produzir_e_main_so_em_processo_filho envelope_sem_float; do python3 -m pytest --collect-only -q tests/test_produtor.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_produtor.py -k "gravador_mede_igual_ao_produtor or cada_controle_divergente_acusa or destino_padrao_e_o_landing_de_hoje or filho_sem_credencial_s3 or produzir_e_main_so_em_processo_filho or envelope_sem_float"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A gramática do juiz nos dois"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Carga única e rejeitos"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "O resto igual, os dois medindo igual"
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

Reverter src/produtor/spark_produtor.py, src/produtor/gravar_lago.py e tests/test_produtor.py ao commit anterior.

## Observability Hooks

arquivos recusados por espécie, precisão ou partição ocupada

## Anti-Patterns

- Do not apagar ou sobrescrever a partição ou os rejeitos já existentes para gravar de novo: destrói a carga anterior, que é evidência; instead recusar sem gravar.
- Do not gravar os rejeitos dentro do diretório da tabela: a Bronze leria os rejeitos como dado; instead o prefixo -rejeitos, irmão da tabela.
- Do not editar um test_* fora da lista nomeada em B-2: a exceção à regra do teste selado é nomeada; instead só o que B-2 lista.

## Do-Not-Touch

- `_raw`
- `contracts`
- `cvg/docs/adrs`
- `src/pda`
- `src/medalhao`
- `src/ontologia`
- `infra`
- `src/produtor/gramatica.py`
- `tests/test_gramatica.py`
- `src/produtor/vincular_procedencia.py`
- `tests/test_vincular_procedencia.py`

## Open Questions

(none — this task is fully specified)
