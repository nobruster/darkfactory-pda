# Pass 1 · Intent — as tech-specs

O BRD diz **por que**; a tech-spec diz **o quê** e **quanto**. Ela ainda não
diz *com o quê* — motor, linguagem e formato são decididos no Pass 3.

## O que roda aqui

```bash
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
converge/bin/cvg intent cvg/docs/tech-spec/<arquivo>.md
```

⚠️ **De dentro do WSL.** Token final estável: `CHECK_TECH_SPEC=PASS | FAIL |
DRAFT_OK | DRAFT_INCOMPLETE`.

## Estado atual do exemplo

[`tech-spec-exemplo-fabrica.md`](tech-spec-exemplo-fabrica.md) está
**propositalmente reprovado**:

```
[ ] 2 unresolved BLOCKER gap(s) — resolve each before the spec can descend
[ ] Sign-off: owner verdict 'canonical' missing
FAIL: 2 required check(s) failed — do not descend to Pass 2
CHECK_TECH_SPEC=FAIL
```

Isto **não é defeito** — é a fábrica funcionando. Os dois blockers são
perguntas que ninguém pode responder no lugar do dono:

| Gap | Pergunta | Bloqueia |
|---|---|---|
| GAP-001 | Qual competência do passado é a primeira âncora, e quem confirma? | R-1 — sem âncora não há o que comparar |
| GAP-002 | Arredondamento meio-para-par ou meio-para-cima? | R-3 — herdar o default da linguagem é como um erro estruturalmente verde entra |

Para destravar: responda cada um, troque `resolution: "open"` pela decisão
real, e mude o veredito para `canonical`.

## ⚠️ Dois detalhes do gate que custam tempo

**1. Sentinela de blocker é a linha inteira, e só em inglês.**

O gate lê `resolution:` e marca como não resolvido apenas quando o valor é
exatamente `open`, `none`, `null`, `n/a`, `tbd`, `pending`, `awaiting…` — ou
está vazio. A regra está em `check-tech-spec.sh:339`.

Consequência verificada nesta máquina: `resolution: "ABERTO — o contrato
nasce NAO_MEDIDO…"` passou como **resolvido**. Duas coisas erradas ao mesmo
tempo — a palavra em português, e o texto depois do sentinela.

```yaml
resolution: "ABERTO — ainda não decidido"     # ❌ passa como resolvido
resolution: "OPEN — ainda não decidido"       # ❌ também passa
resolution: "open"                             # ✅ acusa
note: "o porquê vai aqui, fora do resolution"
```

**Se você escreve em português, o `resolution:` é a exceção**: use o
vocabulário do gate e ponha a explicação em outro campo.

**2. Vazamento de stack é WARN, não FAIL.**

Nomear tecnologia no Pass 1 gera aviso, não reprovação. Os termos ficam em
`references/leak-terms.txt`, casados por limite de palavra (`spark` não
dispara em `sparkline`). O gate mecaniza o provável; **a altitude é
julgamento seu**.

## O que o gate exige

| Item | Regra |
|---|---|
| Seções | as seis obrigatórias, nome exato |
| Problem restated | replantear o problema com número |
| Requirements | falsificáveis, com id `R-n`/`W-n` e prioridade diferenciada |
| Success metrics | `Current → Target` |
| Data named | a fonte nomeada no nível do problema |
| Open assumptions | cada uma com dono |
| Gap register | nenhum blocker sem resolução substantiva |
| Sign-off | `canonical` + data ISO real, ligada ao veredito |

Enquanto escreve, sem autorizar:

```bash
bash converge/skills/brd-docs-to-tech-req/scripts/check-tech-spec.sh \
  --draft cvg/docs/tech-spec/<arquivo>.md
```
