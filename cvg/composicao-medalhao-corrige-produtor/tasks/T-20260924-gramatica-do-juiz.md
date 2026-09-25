---
id: T-20260924-gramatica-do-juiz
title: "A gramática do juiz, uma só, para os módulos Spark"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: []
creates_paths: [src/produtor/gramatica.py, tests/test_gramatica.py]
source_note: "seamwise/legs/LEG-GRAMATICA-DO-JUIZ.md#T-20260924-gramatica-do-juiz"
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
signed_off_at: 2026-09-25T00:25:45Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-25T00:30:37Z
signed_off_sig: hmac-sha256-v3:85d3c104:eee2340a292332d457e11f3286fa107ec03ec22a365640f0bb70e67dd04afdb3
accepted_tier: 1
accepted_attempt_id: b1f3db41-2d57-43bc-8ef1-84bbca473bc3
accepted_authorization_ref: hmac-sha256-v3:85d3c104:eee2340a292332d457e11f3286fa107ec03ec22a365640f0bb70e67dd04afdb3
acceptance_record_digest: sha256:ed735da3885f5a2d96ab05902ab60d089f02017fa42498343048fefde7e53a59
---

# A gramática do juiz, uma só, para os módulos Spark

> **Why:** Ter num módulo só a gramática monetária e o padrão de espécie que o juiz Python selado usa, expressos em Spark, para os três módulos do produtor pararem de divergir dele. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Ter num módulo só a gramática monetária e o padrão de espécie que o juiz Python selado usa, expressos em Spark, para os três módulos do produtor pararem de divergir dele. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-CORRIGE-PRODUTOR; seam SEAM-GRAMATICA-DO-JUIZ; swimlane LANE-GRAMATICA-DO-JUIZ; capability leg LEG-GRAMATICA-DO-JUIZ. Done condition: src/produtor/gramatica.py dá, para cada caso da tabela, o MESMO veredito que pda.leitura; os testes de tests/test_gramatica.py passam.

## Behavior

- **B-1** — GIVEN os textos '1.518,00', '        1.518,00', '\t1,00', '\xa01,00' (NBSP, existe em latin-1), '1518,00', '1,5', '1,50', '1,500', '-5,00', '-0,00', '0,00', '1.62,00', 'abc', '', 'NaN', '1e3,00' numa coluna Spark, e a escala 2 do contrato WHEN gramatica.valor_decimal(coluna, precisao, escala) é aplicada, numa sessão com ANSI ligado THEN cada linha dá o MESMO veredito que pda.leitura._converter_monetario(texto, escala), comparado com == de Decimal (o Spark não guarda o sinal do zero, e '-0,00' tem de dar igual por ==): tira das pontas os MESMOS caracteres que str.strip() tira no domínio latin-1 do contrato — espaço, \t, \n, \r, \x0b, \x0c, \x1c a \x1f, \x85 e \xa0 —, aplica a regex ^-?\d{1,3}(\.\d{3})*,\d+$, conta as casas decimais NO TEXTO antes do cast (o cast arredondaria '1,500' em vez de recusar) e recusa mais de 'escala' casas, e recusa valor menor que zero: '1,5' vale 1.50, '-5,00' e '1,500' são NULL, '-0,00' é aceito; o resultado é DecimalType(precisao, escala), nunca float. A ORDEM é a do juiz — gramática, casas, sinal — e só DEPOIS a precisão: valor inválido por qualquer das três é NULL e nunca chega ao cast, então '-1.000,00' com precisão 5 é NULL (inválido, como o juiz devolve None); só um valor VÁLIDO que não cabe em DecimalType(precisao, escala) — '1.000,00' com precisão 5 — faz a ação FALHAR com o erro do Spark (ANSI), nunca vira NULL. A regex fica exposta como constante do módulo.
- **B-2** — GIVEN códigos de espécie como '01', ' 01 ', '1', '001', 'ab', '' e nulo WHEN gramatica.especie_valida(coluna) é aplicada THEN dá o mesmo veredito que pda.leitura._especie_valida (^\d{2}$ depois de tirar das pontas os mesmos caracteres de B-1), com nulo tratado como inválido; escala negativa recusa com ValueError antes de montar a expressão. A sessão do teste é uma fixture de escopo de módulo, com spark.sql.ansi.enabled=true, nunca parada pelo módulo. Nenhum cenário usa skip, xfail ou importorskip.

## Success Criteria

```bash
# eval_1: O mesmo veredito do juiz
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in mesmo_veredito_do_juiz texto_com_espacos_nas_pontas nbsp_e_tab_como_o_juiz uma_casa_decimal_vale; do python3 -m pytest --collect-only -q tests/test_gramatica.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gramatica.py -k "mesmo_veredito_do_juiz or texto_com_espacos_nas_pontas or nbsp_e_tab_como_o_juiz or uma_casa_decimal_vale"'
}

# eval_2: O que o juiz recusa
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in negativo_invalido menos_zero_aceito_como_o_juiz casas_demais_invalido fora_da_precisao_falha negativo_fora_da_precisao_e_invalido escala_negativa_recusa; do python3 -m pytest --collect-only -q tests/test_gramatica.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gramatica.py -k "negativo_invalido or menos_zero_aceito_como_o_juiz or casas_demais_invalido or fora_da_precisao_falha or negativo_fora_da_precisao_e_invalido or escala_negativa_recusa"'
}

# eval_3: Espécie e tipos
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in especie_mesmo_veredito_do_juiz resultado_decimal_nunca_float regex_exposta; do python3 -m pytest --collect-only -q tests/test_gramatica.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gramatica.py -k "especie_mesmo_veredito_do_juiz or resultado_decimal_nunca_float or regex_exposta"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "O mesmo veredito do juiz"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "O que o juiz recusa"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Espécie e tipos"
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

Remover os dois arquivos criados.

## Observability Hooks

divergência de veredito entre Spark e juiz

## Anti-Patterns

- Do not copiar a regex para uma quarta constante solta: é a duplicação que criou a divergência; instead um módulo, importado pelos três.
- Do not reimplementar o juiz no teste: o teste compararia a gramática com ela mesma; instead importar pda.leitura e comparar veredito a veredito.
- Do not alterar pda.leitura: o juiz é selado e é o oráculo desta tarefa; instead o módulo Spark se ajusta ao juiz.

## Do-Not-Touch

- `_raw`
- `contracts`
- `cvg/docs/adrs`
- `src/pda`
- `src/medalhao`
- `src/ontologia`
- `infra`
- `src/produtor/spark_produtor.py`
- `src/produtor/gravar_lago.py`
- `src/produtor/vincular_procedencia.py`
- `tests/test_produtor.py`
- `tests/test_vincular_procedencia.py`

## Open Questions

(none — this task is fully specified)
