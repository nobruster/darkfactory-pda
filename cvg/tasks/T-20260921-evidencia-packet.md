---
id: T-20260921-evidencia-packet
title: "Gravar o pacote por execução, sem sobrescrever"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260921-juizo-classifica]
supersedes: (none)
touches_paths: []
creates_paths: [src/pda/evidencia.py, tests/test_evidencia.py]
source_note: "seamwise/legs/LEG-EVIDENCIA-RECONSTROI.md#T-20260921-evidencia-packet"
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
signed_off_at: 2026-09-22T02:47:13Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:66b47ddad5da94db645025826c136d8902de3f431d1384576e7ed731eea9cb2e
---

# Gravar o pacote por execução, sem sobrescrever

> **Why:** Tornar o veredito auditável sem reexecutar o pipeline.

## Goal

Tornar o veredito auditável sem reexecutar o pipeline.

## Context

Intent DI-PDA-BENEFICIOS; seam SEAM-EVIDENCIA; swimlane LANE-EVIDENCIA; capability leg LEG-EVIDENCIA-RECONSTROI. Done condition: O pacote traz veredito, causa, âncora, agregado, duração e classificações; duas execuções coexistem.

## Behavior

- **B-1** — GIVEN uma execução com âncora, outra que terminou antes da leitura, e um pacote adulterado onde só o rótulo do veredito foi trocado WHEN o pacote é lido de volta THEN o veredito é REDERIVADO dos cinco controles, da âncora, das classificações de cada diferença, dos hashes, da COMPETÊNCIA SOLICITADA gravada ao lado das recebidas do contrato e do envelope — sem ela a execução de 2026-02 recusada por trazer artefatos coerentes de 2026-01 é indistinguível de uma execução legítima de janeiro, e rederivaria ACEITO, rejeitando o pacote legítimo de RECUSADO — e dos PARES de origens distintas que motivaram cada comparação — as duas listas de defeitos, a observada na leitura e a declarada no envelope, e os dois mapas de totais por código, o da leitura e o do envelope, todos gravados separadamente; sem eles, um RECUSADO legítimo rederivaria ACEITO, seja por omissão de defeito, seja por um envelope que transfere 1,00 do código A para o B mantendo chaves, controles globais, hashes e defeitos idênticos — casos em que só a divergência entre os dois lados explica a recusa. E o pacote preserva o TIPO original de cada campo monetário recebido, sem normalizar — serializar tudo como string faria 0.0 e '0.00' virarem insumos numericamente iguais, e a recusa legítima por número JSON deixaria de ser rederivável embora controles e hashes coincidam. Como JSON não tem Decimal, cada monetário é gravado como um par declarado — o tipo recebido e o texto exato dos bytes originais — de modo que Decimal('0.00'), a string '0.00' e o número 0.0 fiquem distinguíveis, e um Decimal('sNaN') recebido e recusado seja gravado sem que o próprio gravador falhe ao registrar a recusa; o pacote adulterado é recusado porque o rótulo discorda do que esses insumos produzem. São TRÊS os hashes gravados, os mesmos que a fronteira compara — o ANCORADO do contrato, o OBSERVADO computado na leitura e o DECLARADO no envelope; com dois só, um pacote legítimo de RECUSADO por ancorado=observado e declarado divergente rederivaria ACEITO e seria rejeitado. A ausência não é recusa incondicional, ela decide o veredito — e quem decide é a CAUSA registrada, não a falta de um hash. Contrato que devolveu NAO_MEDIDO por qualquer motivo — sem âncora, sem aprovador, sem data ou sem política decimal — dá ACEITO_SEM_ANCORA, mesmo que o hash ancorado exista e nenhum observado tenha sido produzido; e o pacote grava TODOS os campos que determinam a validade do contrato como foram lidos — aprovador, data, política decimal e a escala declarada que deriva a precisão — cada um distinguindo CHAVE AUSENTE de valor null, porque montar o pacote com get() tornaria os dois indistinguíveis e a fronteira trata um como estrutura recusada e o outro como ausência aceita; numa competência ancorada sem registros legíveis essa perda mudaria o próprio veredito rederivado. Grava os campos, não só a causa, porque dois contratos em estados de aprovação diferentes produziriam os mesmos dados auditáveis e o leitor apenas confiaria no rótulo da causa — trocar a confiança no rótulo do veredito pela confiança noutro rótulo não é rederivar, e uma causa incorreta passaria sem ninguém ver; ler a falta do hash como se fosse a causa recusaria justamente o pacote que a orquestração deve gravar. Falta o observado COM evento de falha registrado e é execução interrompida, desfecho ERRO. Contrato RECUSADO no carregamento, por política que contradiz o ADR, é um terceiro caminho antecipado — termina sem hash observado, sem agregado e sem envelope, não é NAO_MEDIDO nem exceção, e o pacote grava a política recusada e a cláusula do ADR violada, que é o que a rederivação precisa para reconstruir esse RECUSADO sem depender do rótulo. A precedência é declarada, não deduzida — NAO_MEDIDO decide antes, RECUSADO por contrato exige a política gravada, e ERRO exige o evento. Os três casos gravam pacote válido; recusar qualquer um impediria de gravar justamente a execução que precisa de registro. Só é recusado o pacote cujo rótulo não bate com o que os insumos rederivam; campos não percorridos são marcados ausentes, nunca zerados
- **B-2** — GIVEN duas execuções da mesma competência WHEN a segunda é gravada THEN as duas coexistem — a segunda não sobrescreve a primeira

## Success Criteria

```bash
# eval_1: Rederiva com os três hashes; precedência quando ancorado e observado faltam juntos
eval_1() {
  pytest -q tests/test_evidencia.py -k "rederiva or rotulo_adulterado or tres_hashes or precedencia_sem_ancora"
}

# eval_2: Duas execuções coexistem, sem overwrite
eval_2() {
  pytest -q tests/test_evidencia.py -k nao_sobrescreve
}

# eval_3: Os quatro vereditos terminais são distinguíveis
eval_3() {
  pytest -q tests/test_evidencia.py -k vereditos
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Rederiva com os três hashes; precedência quando ancorado e observado faltam juntos"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Duas execuções coexistem, sem overwrite"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Os quatro vereditos terminais são distinguíveis"
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

Remover o gravador de evidência e seus testes.

## Observability Hooks

pacotes gravados por competência

## Anti-Patterns

- Do not gravar com mode overwrite: e o defeito do carregamento atual — destrói a prova; instead gravar um pacote por execução.
- Do not editar um pacote antigo para corrigir o histórico: falsifica evidência; instead gravar evidência nova e manter a antiga.
- Do not ler o veredito do rótulo gravado no pacote: o rótulo é conclusão, não prova — trocá-lo basta para mentir; instead rederivar dos controles, da âncora e dos hashes.

## Do-Not-Touch

- `_raw`
- `evidence`

## Open Questions

(none — this task is fully specified)
