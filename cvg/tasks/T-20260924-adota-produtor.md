---
id: T-20260924-adota-produtor
title: "Adotar o produtor Spark e o gravador do lago, sem mudar o que eles fazem"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: [src/produtor/spark_produtor.py, src/produtor/gravar_lago.py]
creates_paths: [tests/test_produtor.py]
source_note: "seamwise/legs/LEG-ADOTA-PRODUTOR.md#T-20260924-adota-produtor"
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
signed_off_at: 2026-09-24T23:43:16Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-24T23:54:59Z
signed_off_sig: hmac-sha256-v3:85d3c104:a275b8a74137f320d45be379e3ee5649c9e17192ec725cceed230a42e7c813b0
accepted_tier: 1
accepted_attempt_id: cc12a9c6-8e4c-435d-b6dd-18121a91b090
accepted_authorization_ref: hmac-sha256-v3:85d3c104:a275b8a74137f320d45be379e3ee5649c9e17192ec725cceed230a42e7c813b0
acceptance_record_digest: sha256:7f5e762457dbbf50cd76b7412616fa331ee67e776610fba933509eab62f69bf6
---

# Adotar o produtor Spark e o gravador do lago, sem mudar o que eles fazem

> **Why:** Pôr sob Task-Spec o código que gravou o landing de 2026-01, provando por testes o comportamento que ele já tem, sem alterá-lo. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Pôr sob Task-Spec o código que gravou o landing de 2026-01, provando por testes o comportamento que ele já tem, sem alterá-lo. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-ADOTA-PRODUTOR; seam SEAM-ADOTA-PRODUTOR; swimlane LANE-ADOTA-PRODUTOR; capability leg LEG-ADOTA-PRODUTOR. Done condition: tests/test_produtor.py prova o comportamento atual de src/produtor/spark_produtor.py e src/produtor/gravar_lago.py sobre fixtures em tmp_path; a única mudança de código é o parâmetro --destino em src/produtor/gravar_lago.py.main, com o padrão de hoje; todos os testes passam, numa JVM compartilhada sem ser derrubada.

## Behavior

- **B-1** — GIVEN um CSV pequeno em tmp_path, em latin-1 com separador ';', no layout do contrato de 2026-01 (14 colunas, o cabeçalho com 'Espécie' duas vezes), valores no formato brasileiro com espaços à esquerda ('        1.518,00') e pelo menos um valor fora da gramática WHEN spark_produtor.produzir(csv, contrato, competencia) roda THEN o envelope traz motor 'spark', o sha256 do arquivo lido (igual ao hashlib do teste), e os cinco controles como TEXTO — count_linhas, linhas_invalidas, sum_vl_liquido, min_vl_liquido e max_vl_liquido — IGUAIS, comparados como Decimal, a valores LITERAIS da fixture calculados à mão no teste (o juiz Python não serve de oráculo aqui: exige chmod 444, 65 códigos e 11 colapsos); a fixture tem DOIS CÓDIGOS COM A MESMA DESCRIÇÃO, e total_por_codigo os soma SEPARADOS, por código, nunca pela descrição (R-3, ADR 0008); a espécie é lida pela POSIÇÃO do contrato. O comportamento atual da gramática fica FIXADO, sem corrigir (Regra 4): '1,5' conta em linhas_invalidas e nunca como zero, e '-5,00' é aceito e somado — divergência conhecida com o juiz Python, que aceita '1,5' e recusa negativo, registrada para decisão do dono; e um código vazio fica fora de total_por_codigo, também fixado e registrado. Nenhum float em nenhum valor do envelope. Como produzir chama spark.stop(), ele só roda num PROCESSO FILHO, sem as variáveis S3_* no ambiente, com toda saída em tmp_path.
- **B-2** — GIVEN o mesmo CSV e um destino em tmp_path passado por --destino WHEN gravar_lago._ler_fonte, gravar_lago._controles e gravar_lago.main rodam THEN _ler_fonte seguido de _controles mede os mesmos cinco controles que produzir, pela mesma gramática; main recusa com o token LAGO=RECUSADO na saída um contrato NAO_MEDIDO e uma fonte de zero linhas, e o destino NÃO existe depois; com uma cópia do contrato em tmp_path cuja âncora é a da fixture, a PRIMEIRA carga dá LAGO=GRAVADO, e uma SEGUNDA carga da mesma competência no mesmo destino dá LAGO=DIVERGE com o dobro de linhas relidas e os arquivos da primeira ainda lá — o append sem conferir partição vazia fica FIXADO e registrado como defeito latente; cada um dos cinco controles divergindo SOZINHO na releitura — o processo filho substitui a releitura por um DataFrame com um único controle alterado — dá LAGO=DIVERGE, para provar que a comparação não é só por contagem. O padrão de --destino é o destino de hoje, s3a://landing/pda/beneficios-emitidos, conferido pelo argparse SEM executar main. main só roda num processo filho SEM as variáveis S3_* — qualquer acesso ao MinIO falha em vez de gravar —, com --destino e --out em tmp_path e subprocess com timeout. Nenhum cenário usa skip, xfail ou importorskip, e um cenário confere pelo AST do próprio arquivo de teste que produzir e main nunca são chamados no processo do pytest.

## Success Criteria

```bash
# eval_1: O produtor mede o que a fixture tem
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in produtor_totais_literais_da_fixture codigos_com_mesma_descricao_somam_separados gramatica_atual_fixada codigo_vazio_fora_do_total_fixado sha256_e_motor_no_envelope envelope_sem_float; do python3 -m pytest --collect-only -q tests/test_produtor.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_produtor.py -k "produtor_totais_literais_da_fixture or codigos_com_mesma_descricao_somam_separados or gramatica_atual_fixada or codigo_vazio_fora_do_total_fixado or sha256_e_motor_no_envelope or envelope_sem_float"'
}

# eval_2: O gravador prova o que gravou
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gravador_mede_igual_ao_produtor contrato_nao_medido_recusa zero_linhas_nao_grava primeira_grava_segunda_diverge_sem_apagar cada_controle_divergente_acusa; do python3 -m pytest --collect-only -q tests/test_produtor.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_produtor.py -k "gravador_mede_igual_ao_produtor or contrato_nao_medido_recusa or zero_linhas_nao_grava or primeira_grava_segunda_diverge_sem_apagar or cada_controle_divergente_acusa"'
}

# eval_3: Sem mudar o que já gravou e sem tocar o MinIO
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in destino_padrao_e_o_landing_de_hoje filho_sem_credencial_s3 produzir_e_main_so_em_processo_filho controles_em_texto; do python3 -m pytest --collect-only -q tests/test_produtor.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_produtor.py -k "destino_padrao_e_o_landing_de_hoje or filho_sem_credencial_s3 or produzir_e_main_so_em_processo_filho or controles_em_texto"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "O produtor mede o que a fixture tem"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "O gravador prova o que gravou"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Sem mudar o que já gravou e sem tocar o MinIO"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
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

Reverter src/produtor/spark_produtor.py e src/produtor/gravar_lago.py ao commit anterior e remover tests/test_produtor.py.

## Observability Hooks

divergência entre o produtor Spark e o juiz Python sobre o mesmo arquivo

## Anti-Patterns

- Do not mudar a leitura, a gramática, o schema ou os controles para um teste passar: o landing de 2026-01 foi gravado por este código e fecha com a âncora; mudar muda o dado; instead o teste descreve o comportamento que existe; divergência é achado, reportado.
- Do not refatorar, renomear ou 'melhorar' qualquer função além de acrescentar --destino: adoção não é reescrita; cada mudança exigiria provar de novo contra os 41,5 milhões; instead só o parâmetro --destino, com o padrão de hoje.
- Do not chamar produzir ou main no processo do pytest: spark.stop() derruba a sessão compartilhada da suíte numa JVM só; instead processo filho (subprocess) com o Python do contêiner.

## Do-Not-Touch

- `_raw`
- `contracts`
- `cvg/docs/adrs`
- `src/pda`
- `src/medalhao`
- `src/ontologia`
- `infra`
- `src/produtor/vincular_procedencia.py`

## Open Questions

(none — this task is fully specified)
