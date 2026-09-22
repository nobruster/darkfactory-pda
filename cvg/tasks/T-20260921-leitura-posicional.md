---
id: T-20260921-leitura-posicional
title: "Ler a competência por posição, sem alterar a fonte"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260921-contrato-ancora]
supersedes: (none)
touches_paths: []
creates_paths: [src/pda/leitura.py, tests/test_leitura.py, tests/fixtures/competencia-min.csv]
source_note: "seamwise/legs/LEG-LEITURA-POSICIONAL.md#T-20260921-leitura-posicional"
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
signed_off_at: 2026-09-22T02:47:14Z
accepted: false
accepted_by: (none)
accepted_at: (none)
signed_off_sig: hmac-sha256-v3:85d3c104:4cead650a3723a41439d76317c4bb0dac933d55886291ee84c85618e791c6e2f
---

# Ler a competência por posição, sem alterar a fonte

> **Why:** Extrair registros preservando os bytes e o defeito de origem.

## Goal

Extrair registros preservando os bytes e o defeito de origem.

## Context

Intent DI-PDA-BENEFICIOS; seam SEAM-LEITURA; swimlane LANE-LEITURA; capability leg LEG-LEITURA-POSICIONAL. Done condition: sha256 idêntico antes e depois; código e descrição saem de posições distintas; registro ilegível entra em linhas_invalidas.

## Behavior

- **B-1** — GIVEN um arquivo com Espécie repetida e o layout declarado, e outro em que as DUAS colunas de cabeçalho idêntico Espécie — índices 12 e 13 — tiveram os valores trocados entre si, deixando o cabeçalho byte a byte igual WHEN a leitura começa THEN no primeiro o sha256 fica idêntico E a proteção de escrita é conferida antes de ler — W-1 exige chmod 444 nos bytes de origem, e hash antes/depois não prova proteção, porque um arquivo em 0666 passa nesse teste quando ninguém escreve durante ele; a leitura recusa começar se _raw não estiver protegido. Código e descrição vêm dos índices 12 e 13; os totais por código que a leitura produz são somados em contexto decimal PRÓPRIO e COMPLETO — precisão derivada, arredondamento, Emax, Emin e traps, todos declarados, porque localcontext() herda do global tudo que não for dito — com Emax=5 a soma do total ancorado levanta Overflow, e com o trap Inexact ativo quantizar um intermediário legítimo de três casas levanta Inexact, transformando execução VÁLIDA em ERRO por alteração externa. O teste força um contexto global adverso nos três eixos e exige exatidão mesmo assim — a proteção escrita para a agregação não alcança a leitura, e uma referência corrompida faria a fronteira recusar um produtor correto com os testes da leitura verdes. No segundo a leitura BLOQUEIA, e o gate NÃO pode ser conferência de cabeçalho — cabeçalho idêntico não distingue as duas — e sim o formato de cada posição, MEDIDO nas 41.572.553 linhas — o índice 12 é sempre só dígitos, largura 2 após strip, alinhado à direita, e o 13 é sempre textual, alinhado à esquerda, sem uma única linha em que os dois sejam indistinguíveis; o teste falha se for satisfeito trocando colunas de nomes diferentes, porque é esta troca, de nomes iguais, que motivou o ADR 0002 e que os cinco controles preservam
- **B-2** — GIVEN um registro cujo campo monetário é ilegível, os valores 'NaN', 'Infinity', '1_000' e '1e3', e os quatro exemplos do ADR 0004 — entre eles 'Pensão por Morte de ' com 20 caracteres brutos e 19 após strip WHEN os registros são contados THEN o primeiro entra em linhas_invalidas com identidade, valor original e posição. Os quatro valores especiais TAMBÉM entram como inválidos, porque legível é o que casa a gramática monetária MEDIDA NA FONTE, e não o que Decimal() aceita. A fonte publica no formato brasileiro com preenchimento à esquerda — '        1.621,00', ponto de milhar e vírgula decimal, escala 2 nas 41.572.553 linhas, zero recusas — de modo que Decimal(bruto) RECUSA toda linha legítima e a normalização é parte da gramática, não um passo implícito — retira o preenchimento, exige o padrão e só então converte. E cada valor convertido é conferido contra a ESCALA CARREGADA do contrato, não contra duas casas fixas, antes de entrar nos mapas de referência — é a verificação que o carregador delega a quem recebe o valor; fixar duas casas recusaria uma fonte futura com escala maior legitimamente declarada, e não conferir deixaria um contrato de escala 1 aceitar '1,23' com a precisão validada para outro domínio. Valor fora da escala contratada é defeito classificado, e valor NEGATIVO também, porque o ADR 0009 derivou a precisão sob soma monotônica — e os dois têm o MESMO destino que o ilegível — tipo VALOR_ILEGIVEL, incrementam linhas_invalidas, ficam fora da soma e fora dos extremos. Um destino só, porque a fronteira confere linhas_invalidas contra defeitos do tipo VALOR_ILEGIVEL, e dar-lhes tipo próprio faria a leitura incrementar inválidos enquanto a fronteira exige zero — dois implementadores cumprindo seus textos e discordando. Uma gramática de ponto decimal recusaria a competência inteira — os quatro passam pelo construtor, e um NaN chegaria vivo aos extremos, onde min levanta InvalidOperation e transformaria defeito de UMA linha em ERRO da execução inteira. E a descrição emite defeito de IDENTIDADE COLAPSADA, sem tornar a linha inválida, quando cobre mais de um código — critério do ADR 0008, medido na competência inteira — 11 descrições cobrem 24 códigos, entre elas 'Pensão por Morte de ' fundindo 01, 03, 23 e 59. A unidade do defeito é a DESCRIÇÃO, não a ocorrência, ele só é emitido ao fim da varredura, porque colapso é propriedade do conjunto, e a contagem observada é conferida contra a CONTAGEM MEDIDA que o contrato carrega — senão a leitura poderia omitir um colapso, o envelope local reproduzir a mesma lista, e a comparação por identidade concordar com cardinalidade, mapas e controles todos corretos — um leitor incremental que emitisse a partir do segundo código deixaria sem registro todas as ocorrências anteriores, e a fronteira concordaria com a lista incompleta por ter a própria leitura como referência. Largura NÃO é critério — as 41.572.553 descrições têm 20 caracteres brutos, então bruto==20 acusaria toda linha, e strip==20 deixaria de fora justamente esse colapso de quatro códigos, cujo strip é 19

## Success Criteria

```bash
# eval_1: Leitura posicional; _raw sem 444 bloqueia; Espécie 12 e 13 trocadas bloqueiam
eval_1() {
  pytest -q tests/test_leitura.py -k "sha256 or w1_protecao or especie_12_13_trocadas"
}

# eval_2: Ilegível vira inválida; NaN também; descrição que colapsa códigos acusa
eval_2() {
  pytest -q tests/test_leitura.py -k "invalida or gramatica_monetaria or identidade_colapsada"
}

# eval_3: A leitura reporta sua duração para a orquestração medir o total
eval_3() {
  pytest -q tests/test_leitura.py -k duracao
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Leitura posicional; _raw sem 444 bloqueia; Espécie 12 e 13 trocadas bloqueiam"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Ilegível vira inválida; NaN também; descrição que colapsa códigos acusa"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "A leitura reporta sua duração para a orquestração medir o total"
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

Remover o leitor e seus testes.

## Observability Hooks

registros lidos e defeitos por tipo

## Anti-Patterns

- Do not escrever no arquivo de origem: destrói a prova de que a origem publicou aquilo; instead tratar _raw/ como somente leitura.
- Do not ler colunas por nome de cabeçalho: Espécie repetida faz perder uma das duas em silêncio; instead ler por posição declarada no contrato.
- Do not corrigir valor malformado durante a leitura: apaga o defeito antes da classificação; instead preservar e contar como linha inválida.

## Do-Not-Touch

- `_raw`

## Open Questions

(none — this task is fully specified)
