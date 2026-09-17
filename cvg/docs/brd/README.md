# Pass 0 · Capture — os BRDs

Aqui entra o pedido de negócio, na voz do dono, **antes** de existir stack,
código ou tarefa. É o insumo do Pass 1.

## O que roda aqui

```bash
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
converge/bin/cvg capture cvg/docs/brd/<arquivo>.md
```

⚠️ **De dentro do WSL** — o motor é bash de Linux e precisa de `shellcheck`.

O gate termina sempre com um token estável: `CHECK_BRD=PASS | FAIL |
DRAFT_OK | DRAFT_INCOMPLETE | NOGO_OK | NOGO_INVALID`.

## O gate foi provado nesta máquina

Aprovar é fácil; o que importa é **acusar**. Verificado em 17/09/2026:

| Caso | Veredito |
|---|---|
| BRD canônico completo | `CHECK_BRD=PASS` |
| sem tag de procedência nos números | `CHECK_BRD=FAIL` |
| escopo dizendo "none"/"n/a" | `CHECK_BRD=FAIL` |
| pergunta aberta sem dono | `CHECK_BRD=FAIL` |
| número `(guessed)` sem pergunta aberta | `CHECK_BRD=FAIL` |
| exemplo escondido em bloco de código | `CHECK_BRD=FAIL` |
| **veredito `pending` em vez de `canonical`** | **`CHECK_BRD=FAIL`** |

A última linha é a **Barreira A**: sem o dono escrever `canonical`, o Pass 1
não consome o brief. `draft` e `pending` nunca autorizam handoff.

## O que o gate exige

| Item | Regra |
|---|---|
| Seções | nome exato do template (`## Problem`, não `## Problematic`) |
| Problem | ao menos um número |
| Goals | ao menos uma linha em forma de KPI |
| Scope | In **e** Out com entradas reais — "none" não conta |
| Números | tag `(measured)` · `(estimated)` · `(guessed)` na mesma linha |
| `(guessed)` | tem de estar ligado a uma pergunta aberta |
| Open questions | toda pergunta com dono nomeado |
| Sign-off | veredito com `canonical` + data ISO real (`2026-02-31` é recusada) |

Exemplo em bloco de código não satisfaz **nem viola** check nenhum — o gate
remove as cercas antes de avaliar.

## Escrevendo um BRD

Comece por [`brd-exemplo-fabrica.md`](brd-exemplo-fabrica.md) (este passa) ou
pelo template em
[`../../../converge/skills/idea-to-brd/references/brd-template.md`](../../../converge/skills/idea-to-brd/references/brd-template.md).

Enquanto escreve, valide sem autorizar:

```bash
bash converge/skills/idea-to-brd/scripts/check-brd.sh --draft cvg/docs/brd/<arquivo>.md
```

`--draft` roda os mesmos checks estruturais, rebaixa procedência e sign-off a
avisos, e **nunca autoriza handoff**, por mais completo que o brief esteja.

## A outra saída honesta

Decidir **não fazer** também é resultado, e tem registro próprio em
`cvg/docs/no-go/`:

```bash
bash converge/skills/idea-to-brd/scripts/check-brd.sh --no-go cvg/docs/no-go/<arquivo>.md
```

Exige marcador de no-go, data ISO real, o porquê de não construir, o que
reabriria a decisão, e o dono da chamada.
