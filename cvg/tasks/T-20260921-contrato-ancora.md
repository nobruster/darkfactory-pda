---
id: T-20260921-contrato-ancora
title: "Carregar contrato, âncora e layout posicional"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: []
creates_paths: [src/pda/contrato.py, tests/test_contrato.py, contracts/competencia-202601.yaml]
source_note: "seamwise/legs/LEG-CONTRATO-RECUSA-SEM-ANCORA.md#T-20260921-contrato-ancora"
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
signed_off_at: 2026-09-22T02:47:11Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-22T02:59:09Z
signed_off_sig: hmac-sha256-v3:85d3c104:869bb3599bdb68b0bb75b9387cb5656b6a5de167401af48d0afc247a23ec43ba
accepted_tier: 1
accepted_attempt_id: 1709086a-867c-44bb-af4c-302bead0fe89
accepted_authorization_ref: hmac-sha256-v3:85d3c104:869bb3599bdb68b0bb75b9387cb5656b6a5de167401af48d0afc247a23ec43ba
acceptance_record_digest: sha256:027f69bd9dbb2ad23c0de94e879ee57fcb8a3bc2bdd061625aa61338b20d55be
---

# Carregar contrato, âncora e layout posicional

> **Why:** Fazer a ausência de prova bloquear em vez de virar verde.

## Goal

Fazer a ausência de prova bloquear em vez de virar verde.

## Context

Intent DI-PDA-BENEFICIOS; seam SEAM-CONTRATO; swimlane LANE-CONTRATO; capability leg LEG-CONTRATO-RECUSA-SEM-ANCORA. Done condition: Os cinco controles e o layout saem com procedência; sem âncora, ou sem aprovador, retorna NAO_MEDIDO como valor.

## Behavior

- **B-1** — GIVEN um contrato com os cinco controles nomeados, a procedência, o layout posicional e os DOIS hashes — o do ZIP publicado e o do CSV extraído sobre o qual a âncora foi medida WHEN o contrato é carregado THEN os controles monetários da ÂNCORA são recusados se vierem como float no YAML — um sum_vl_liquido sem aspas é float, e Decimal(str(v)) apagaria a origem enquanto Decimal(v) traria a aproximação binária; a recusa é do carregamento, antes de qualquer conversão, porque as recusas do agregador e do envelope não protegem o próprio referencial. Âncora, procedência, layout, os dois hashes, a CARDINALIDADE de códigos medida na competência inteira — 65 nesta, não os 51 amostrados pelo ADR 0004 — a CONTAGEM MEDIDA DE COLAPSOS que o ADR 0008 exige junto dela, 11 descrições cobrindo 24 códigos, os DEFEITOS CONHECIDOS pré-classificados com aprovador e data — os 11 colapsos como CONFIRMED_SOURCE_DEFECT — e a POLÍTICA DECIMAL com escala e não-negatividade saem juntas. Os controles da âncora são recusados se vierem não finitos, e as duas CONTAGENS se não forem inteiros não negativos, porque 'Infinity' alcançaria a derivação de precisão e False passaria por igualdade contra um inteiro legítimo — precisão, granularidade e modo de arredondamento são dados carregados do contrato, como o ADR 0003 exige, não escolha privada de quem implementa. Contrato SEM política decimal é NAO_MEDIDO, senão o agregador local fixa a sua, passa nos exemplos, e um produtor externo escolhe outra sem nada acusar. E contrato COM política que contradiz o ADR — HALF_UP, ou granularidade por campo — é RECUSADO no carregamento, não validado, porque um contrato contraditório deixaria o agregador entre obedecer ao contrato e obedecer à decisão vinculante; a validação confere a política contra o ADR, e nunca o contrário. A precisão é conferida por SUFICIÊNCIA e é DERIVADA, como manda o ADR 0009 — dígitos inteiros da âncora mais a escala máxima declarada para os intermediários, 11 + 3 = 14 nesta competência, sob a premissa DECLARADA de soma monotônica; o contrato declara a escala e a NÃO-NEGATIVIDADE do domínio, medidas na fonte, em vez de assumir um padrão, porque um acumulador que exceda o total quebraria a fórmula e 14 perderia o centavo. A escala declarada é verificada por QUEM RECEBE O VALOR, não pelo carregador, que roda antes da leitura e não vê registro nenhum — a leitura confere cada valor da fonte, e a fronteira confere cada monetário do envelope externo, ambos contra a escala do contrato; um valor que a exceda é defeito classificado, nunca somado em silêncio. Escala finita não é escala menor ou igual a 3, e sem essa verificação na etapa consumidora a precisão validada perderia informação durante a soma e ainda devolveria o mesmo total global arredondado, com os mapas por código errados. Precisão 6 com HALF_EVEN e arredondamento final satisfaz presença, modo e granularidade e devolve 7.85218E+10 no lugar de 78.521.752.562,12; prec=13 representa o total e ainda assim perde o centavo ao SOMAR 78521752562,12 + 0,005 + 0,005, porque a perda acontece durante a soma e não na quantização. Contrato com precisão insuficiente é RECUSADO no carregamento, não descoberto durante a agregação. Falta o hash do CSV e também é NAO_MEDIDO, porque hoje só o ZIP tem checksum e a âncora foi medida no CSV — sem o par, trocar o CSV extraído não seria detectado; sem aprovador ou sem data, idem
- **B-2** — GIVEN uma competência sem âncora no contrato WHEN o contrato é carregado THEN retorna NAO_MEDIDO como valor, sem gravar nem encerrar o processo

## Success Criteria

```bash
# eval_1: Hashes distintos; política ausente vira NAO_MEDIDO e política HALF_UP é recusada
eval_1() {
  pytest -q tests/test_contrato.py -k "ancorada or hash_zip_e_csv or sem_politica_decimal or politica_contradiz_adr"
}

# eval_2: Sem âncora retorna NAO_MEDIDO sem escrever em disco
eval_2() {
  pytest -q tests/test_contrato.py -k nao_medido
}

# eval_3: O layout declara as 14 posições, com Espécie em 12 e 13
eval_3() {
  pytest -q tests/test_contrato.py -k layout
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Hashes distintos; política ausente vira NAO_MEDIDO e política HALF_UP é recusada"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Sem âncora retorna NAO_MEDIDO sem escrever em disco"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "O layout declara as 14 posições, com Espécie em 12 e 13"
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

Remover o carregador de contrato e seus testes.

## Observability Hooks

competências ancoradas no contrato

## Anti-Patterns

- Do not gerar a âncora quando ela falta: um número que ninguém viu medir é um palpite; instead retornar NAO_MEDIDO.
- Do not editar a âncora para um veredito passar: falsifica a verdade contra a qual tudo é medido; instead investigar; âncora revista exige nova aprovação.
- Do not declarar colunas por nome no contrato: Espécie aparece duas vezes e o nome não decide qual; instead declarar o índice posicional.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`

## Open Questions

(none — this task is fully specified)
