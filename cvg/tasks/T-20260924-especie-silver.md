---
id: T-20260924-especie-silver
title: "Tabela Delta especie: o nome oficial ao lado do texto da fonte"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260924-ontologia-versionada]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/especie.py, tests/test_especie.py]
source_note: "seamwise/legs/LEG-ESPECIE-SILVER.md#T-20260924-especie-silver"
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
signed_off_at: 2026-09-24T22:52:44Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:f260dedd1e1b0edc14eb5efbd8eabb8c6bc303577cd6b90690d20b945e98882e
---

# Tabela Delta especie: o nome oficial ao lado do texto da fonte

> **Why:** Publicar, por competência, uma tabela Delta com cada código de espécie, o nome oficial da ontologia, o grupo e o texto que a fonte publicou, sem corrigir nada. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Publicar, por competência, uma tabela Delta com cada código de espécie, o nome oficial da ontologia, o grupo e o texto que a fonte publicou, sem corrigir nada. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-ONTOLOGIA; seam SEAM-ESPECIE-SILVER; swimlane LANE-ESPECIE-SILVER; capability leg LEG-ESPECIE-SILVER. Done condition: publicar_especie grava a tabela com uma linha por código da competência, reconfere o que gravou, e recusa sem gravar quando a Silver e a ontologia não conferem; os testes de tests/test_especie.py passam.

## Behavior

- **B-1** — GIVEN a ontologia carregada e uma Silver Delta com especie_codigo e especie_descricao da competência WHEN publicar_especie(spark, ontologia, silver, destino, competencia) roda THEN lê a Silver UMA vez, na versão V fixada no início (versionAsOf), e usa essa mesma leitura para conferir e calcular; grava em Delta, por replaceWhere da competência — que deixa as outras competências intactas —, numa tabela criada pela própria tarefa com o seu schema (não o _garantir_tabela da Silver), uma linha por código com: especie_codigo, nome_oficial, grupo, descricao_fonte (o texto da Silver COMO VEIO, espaços à direita inclusive, Regra 4), texto_fonte_confere_prefixo (verdadeiro quando descricao_fonte sem espaços à direita é igual aos 20 primeiros caracteres do nome oficial sem espaços à direita — medido: 43 de 65 na 2026-01, com ou sem NFC) e competencia; o commit leva em userMetadata a versão V, o sha256 da ontologia e um id_execucao; a reconferência lê o destino na versão do PRÓPRIO commit, achada pelo id_execucao no histórico, nunca a versão atual, e confere o multiconjunto nos dois sentidos contra o calculado, numa função reconferir_especie que acusa uma linha alterada. Sobre a Silver real de 2026-01 o resultado tem 65 linhas, 65 nomes oficiais distintos e 43 linhas com texto_fonte_confere_prefixo verdadeiro.
- **B-2** — GIVEN uma Silver que não confere com a ontologia, ou vazia WHEN publicar_especie confere antes de gravar THEN recusa SEM gravar nada: código na Silver que a ontologia não tem, código da ontologia ausente da competência, código com mais de uma descrição na competência — cada um com o motivo e os códigos; competência sem nenhuma linha devolve NAO_MEDIDO (Regra 9); cada recusa afirma que o destino não ganhou versão nova. Os testes gravam só em tmp_path, nunca no MinIO; os cenários da Silver real leem o MinIO UMA vez, numa fixture de escopo de módulo, e gravam em tmp_path. Nenhum cenário usa skip, xfail ou importorskip: MinIO ou Silver indisponível FALHA o teste.

## Success Criteria

```bash
# eval_1: A tabela guarda os dois textos e fecha com a Silver
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grava_nome_oficial_e_texto_da_fonte descricao_fonte_como_veio reconferencia_acusa_linha_alterada outra_competencia_intacta linhagem_no_commit; do python3 -m pytest --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_especie.py -k "grava_nome_oficial_e_texto_da_fonte or descricao_fonte_como_veio or reconferencia_acusa_linha_alterada or outra_competencia_intacta or linhagem_no_commit"'
}

# eval_2: Divergência recusa sem gravar
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in codigo_fora_da_ontologia_recusa codigo_ausente_recusa duas_descricoes_recusa competencia_vazia_nao_medido; do python3 -m pytest --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_especie.py -k "codigo_fora_da_ontologia_recusa or codigo_ausente_recusa or duas_descricoes_recusa or competencia_vazia_nao_medido"'
}

# eval_3: A Silver real de 2026-01
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in especie_real_2026_01 colapsos_desfeitos_pelo_nome; do python3 -m pytest --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_especie.py -k "especie_real_2026_01 or colapsos_desfeitos_pelo_nome"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A tabela guarda os dois textos e fecha com a Silver"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Divergência recusa sem gravar"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A Silver real de 2026-01"
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

Remover os dois arquivos criados; a tabela especie de produção só é publicada fora do loop.

## Observability Hooks

códigos de espécie que a ontologia não conhece

## Anti-Patterns

- Do not sobrescrever especie_descricao da Silver com o nome oficial: o texto truncado é a prova do defeito da fonte (Regra 4); instead guardar os dois lado a lado.
- Do not escolher uma descrição quando o código tem duas: escolher é decidir em silêncio; instead recusar com o código e as descrições.
- Do not gravar e só depois conferir a cobertura de códigos: publica uma tabela que a conferência reprovaria; instead conferir antes, gravar, e reconferir o gravado.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/pda`
- `infra`
- `src/ontologia/beneficios-emitidos.yaml`
- `src/medalhao/ontologia.py`

## Open Questions

(none — this task is fully specified)
