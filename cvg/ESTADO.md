# Estado da descida — fábrica do PDA

Benefícios emitidos do INSS, competência 2026-01.
Atualizado em 21/09/2026.

## Posição

| Passe | Gate | Veredito |
|---|---|---|
| 0 · Capture | `cvg capture` | 🟢 `CHECK_BRD=PASS` |
| 1 · Intent | `cvg intent` | 🟢 `CHECK_TECH_SPEC=PASS` |
| 2 · Structure | `cvg structure` | 🟢 `CHECK_ADR=OK` — 10 ADRs, 4 superseded |
| 3 · Decompose | `seamwise` | 🟢 `TASK_GRAPH=READY` — 7 costuras |
| 4 · Consensus | `cvg review` | 🟡 **em curso** — 14 rodadas |
| 5 · Tasking | `taskspec gate --stamp` | ⬜ 🛑 Barreira D |
| 7 · Bind | `cvg bind` | ⬜ |
| 8 · Loop | `cvg loop` | ⬜ |

⚠️ **O Pass 4 fecha por decisão, não por zerar objeções.** O gate exige que o
texto revisado seja o texto selado — corrigir depois da review move os hashes
e pede nova review. A saída é rodar uma review e **decidir sem editar**:
`--fix` para o já corrigido, `--accept --owner <nome> --risk <por quê>` para o
resto.

### O que as rodadas acharam

Quatro gates que **recusariam o arquivo correto**, cada um por um número que
foi declarado sem medir:

| Estava escrito | A fonte diz |
|---|---|
| 51 códigos | **65** |
| precisão 13 | **14** |
| gramática de ponto decimal | **vírgula** — `'        1.621,00'` |
| truncamento = 20 caracteres brutos | **todas** as linhas têm 20 |

E um defeito no mundo, não no texto: o CSV estava `0644`, violando W-1
(`chmod 444`), com o teste de hash antes/depois passando assim mesmo.

⚠️ **Despache os agentes junto com o adversário.** Ele lê o plano; não abre o
dado nem confere `ls -l`. Ver Regra 8 no `AGENTS.md` do template.

## A âncora — medida, não declarada

```
count_linhas      41.572.553
sum_vl_liquido    78.521.752.562,12
min / max         0,00 / 183.725,76
linhas_invalidas  0
segundos          64
```

Medida por [`scripts/medir_ancora.py`](../scripts/medir_ancora.py), que varre
os 10,88 GB linha a linha com `Decimal` em `prec=40` — **sem Spark, sem
Parquet, sem importar nada de `src/`**.

### Validação cruzada independente

O `darkfactory-inss`, projeto separado, mediu a mesma competência com outro
código e registrou os mesmos três valores: contagem, total e sha256 do ZIP.

**Duas medições independentes chegando ao mesmo número é o que distingue uma
âncora de um palpite.**

## Os defeitos já encontrados na fonte

Medidos aqui, não herdados:

| Defeito | Evidência |
|---|---|
| `Espécie` duplicada (posições 12 e 13) | cabeçalho de 14 colunas |
| Descrição truncada em 20 caracteres | **51 códigos → 40 descrições** |
| `'Pensão por Morte de'` cobre 4 códigos | 01, 03, 23, 59 |

Agrupar por descrição somaria quatro espécies numa linha só — **e o total
continuaria batendo**. É o modo de falha que esta fábrica existe para
impedir.

## Os 10 ADRs

Seis vigentes. Quatro superseded — e **revisão de ADR se faz com ADR novo**,
nunca editando o antigo: o motivo da mudança é a parte que importa.

| # | Decisão |
|---|---|
| [0000](docs/adrs/0000-context.md) | terreno brownfield; o script atual é evidência, não especificação |
| [0001](docs/adrs/0001-the-2026-01-anchor-is-41572553-rows-summing-78521752562-12.md) | a âncora de 2026-01, medida na origem e validada contra o `darkfactory-inss` |
| [0002](docs/adrs/0002-especie-appears-twice-so-columns-are-read-by-position.md) | leitura posicional, nunca por nome |
| [0006](docs/adrs/0006-the-judge-ships-before-the-spark-producer-that-it-will-judge.md) | juízo e produtor Spark são entregáveis separáveis |
| [0008](docs/adrs/0008-the-description-defect-is-collapsed-identity-not-field-width.md) | o defeito da descrição é identidade colapsada, não largura |
| [0009](docs/adrs/0009-the-derived-precision-assumes-a-monotonic-sum-with-no-negative-values.md) | a precisão derivada assume soma monotônica; negativo é defeito |

| superseded | por | porque |
|---|---|---|
| 0003 | 0007 → 0009 | a conta dos dígitos estava errada; 11 inteiros, não 12 |
| 0004 | 0008 | o critério de largura marcaria **toda** linha |
| 0005 | 0006 | prendia a infra Spark ao mesmo plano |
| 0007 | 0009 | a fórmula tinha premissa tácita de não-negatividade |

## O que o script atual faz de errado

Preservado em [`../docs/legado/`](../docs/legado/) como evidência:

| | Por quê importa |
|---|---|
| `mode("overwrite")` | destrói a execução anterior; impossível auditar depois |
| renomeia a `Espécie` duplicada | resolve o conflito de nome, não decide qual coluna importa |
| credenciais em texto puro | não há como rotacionar sem reeditar o código |

⚠️ **A fábrica classifica, nunca corrige.** O carregamento atual segue
rodando enquanto isto é construído ao lado.

## Para retomar

**De dentro do WSL:**

```bash
export PATH="$HOME/.local/bin:$PATH"
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
converge/bin/cvg doctor host     # precisa dizer DOCTOR_HOST=OK
converge/bin/cvg next --guided
```

⚠️ Antes de qualquer `cvg loop`, rode o pré-voo — três dos quatro bloqueios
do Pass 8 no template foram ambientais:

```bash
python3 fabrica/ponte/checar_deps.py cvg/tasks/T-*.md
```

## O que ainda não foi provado

⚠️ **Nenhuma linha de pipeline existe.** Os 5 ADRs e a tech-spec descrevem o
que a fábrica deve fazer; o código que faz ainda não foi escrito. O Pass 3
decide a stack, e o Pass 8 escreve.

⚠️ **A âncora cobre uma competência só.** 2026-01 está medida; qualquer
outra nasce `NAO_MEDIDO` até alguém medir — faixa medida numa competência
não vira regra para outra.
