---
id: T-20260921-orquestra-desfecho
title: "Decidir o desfecho e garantir o pacote em todo caminho"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260921-evidencia-packet]
supersedes: (none)
touches_paths: []
creates_paths: [src/pda/orquestracao.py, tests/test_orquestracao.py]
source_note: "seamwise/legs/LEG-DESFECHO-COM-PACOTE.md#T-20260921-orquestra-desfecho"
created: "2026-09-21T00:00:00Z"
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
signed_off_at: 2026-09-22T02:47:15Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-22T14:02:14Z
signed_off_sig: hmac-sha256-v3:85d3c104:15c969ac5d8392c78c9be2c31ef5624cc63ce7fa9f634afe1e43ff8e944a9c09
accepted_tier: 1
accepted_attempt_id: d41c97fb-3f5b-427d-a603-cbcd5a59efbc
accepted_authorization_ref: hmac-sha256-v3:85d3c104:15c969ac5d8392c78c9be2c31ef5624cc63ce7fa9f634afe1e43ff8e944a9c09
acceptance_record_digest: sha256:6627bbab4ea42ce62937e0760488bb91144d7f8dbad254151049184502b1ce2f
---

# Decidir o desfecho e garantir o pacote em todo caminho

> **Why:** Dar dono ao fluxo — sem ele a lacuna migra de etapa em etapa.

## Goal

Dar dono ao fluxo — sem ele a lacuna migra de etapa em etapa.

## Context

Intent DI-PDA-BENEFICIOS; seam SEAM-ORQUESTRACAO; swimlane LANE-ORQUESTRACAO; capability leg LEG-DESFECHO-COM-PACOTE. Done condition: Os quatro desfechos gravam pacote com código próprio; exceção real vira ERRO; o tempo total é medido e registrado no pacote. R-9 é should e NÃO é declarado coberto aqui — medir com relógio simulado não demonstra orçamento de competência completa, e inventar recusa por timeout seria afrouxar o que a tech-spec não pediu.

## Behavior

- **B-1** — GIVEN execução sem âncora, execução que bate, e a execução de R-7 — um centavo alterado nos bytes do arquivo, com o sha256 do arquivo ALTERADO reancorado no contrato, de modo que a fronteira passe e o juízo seja quem decide WHEN a orquestração conduz o fluxo inteiro THEN as três gravam pacote, com ACEITO_SEM_ANCORA, ACEITO e RECUSADO de códigos de saída distintos, e só ACEITO autoriza publicar — e a autorização declara a competência SOLICITADA, recusando quando contrato, arquivo ou envelope trazem outra — uma execução pedida para 2026-02 que receba por engano os artefatos coerentes de 2026-01 passaria por hashes, totais e defeitos, todos concordando entre si, e devolveria como resultado de 2026-02 o que é de 2026-01. O caso de R-7 é UMA prova conjunta, não duas separadas — a alteração é real nos bytes, a recusa vem do JUÍZO comparando contra a âncora monetária original, e o teste FALHA se um juízo permissivo for injetado. Sem reancorar, a fronteira recusaria pelo sha256 antes do juízo comparar, e o teste ficaria verde com juízo permissivo — provando metade do que R-7 escreveu
- **B-2** — GIVEN uma exceção real levantada dentro da leitura, uma execução com contrato de política HALF_UP, e uma execução cujo tempo total é medido WHEN a orquestração conduz a execução THEN o contrato HALF_UP termina em RECUSADO com pacote gravado, sem chegar à leitura — caminho exercido aqui, não só declarado no contrato; a exceção vira ERRO com pacote gravado, e o tempo do início da leitura ao veredito é medido e REGISTRADO no pacote, sem virar recusa — R-9 é should, e o pacote passa a carregar o número para que a cobertura de R-9 seja decidida contra competência real, não contra relógio simulado. Se o PRÓPRIO gravador falhar — permissão negada, disco cheio — o desfecho é ERRO com código próprio e a falha vai para a saída de erro; nunca se devolve ACEITO sem pacote, porque autorização sem evidência é o que esta fábrica existe para impedir

## Success Criteria

```bash
# eval_1: R-7 numa prova só; competência solicitada diverge da entregue recusa
eval_1() {
  pytest -q tests/test_orquestracao.py -k "desfechos or r7_centavo_reancorado or competencia_divergente"
}

# eval_2: Exceção real vira ERRO; o tempo é medido no total
eval_2() {
  pytest -q tests/test_orquestracao.py -k "excecao or tempo_total"
}

# eval_3: Só ACEITO autoriza publicar
eval_3() {
  pytest -q tests/test_orquestracao.py -k autoriza
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "R-7 numa prova só; competência solicitada diverge da entregue recusa"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Exceção real vira ERRO; o tempo é medido no total"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Só ACEITO autoriza publicar"
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
  required_tools: [git, bash, python3, pytest]
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

Remover a orquestração e seus testes.

## Observability Hooks

desfechos por tipo e segundos até o veredito

## Anti-Patterns

- Do not encerrar o processo dentro de uma etapa: o pacote prometido nunca é gravado; instead retornar o veredito e deixar a orquestração decidir.
- Do not medir o tempo por etapa: etapa rápida com o resto lento passaria; instead medir do início da leitura ao veredito.
- Do not tratar ACEITO_SEM_ANCORA como autorização: a palavra aceito nomeia o término, não a prova; instead só ACEITO autoriza, com os cinco controles conferidos.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`

## Open Questions

(none — this task is fully specified)
