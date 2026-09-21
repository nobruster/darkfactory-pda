# Estado da descida — fábrica do PDA

Benefícios emitidos do INSS, competência 2026-01.
Atualizado em 21/09/2026.

## Posição

| Passe | Gate | Veredito |
|---|---|---|
| 0 · Capture | `cvg capture` | 🟢 `CHECK_BRD=PASS` |
| 1 · Intent | `cvg intent` | 🟢 `CHECK_TECH_SPEC=PASS` |
| 2 · Structure | `cvg structure` | 🟢 `CHECK_ADR=OK` — 5 ADRs |
| 3 · Decompose | `seamwise` | ⬜ próximo |
| 4 · Consensus | `cvg review` | ⬜ 🛑 barreira |
| 5 · Tasking | `taskspec gate --stamp` | ⬜ |
| 7 · Bind | `cvg bind` | ⬜ |
| 8 · Loop | `cvg loop` | ⬜ |

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

## Os 5 ADRs

| # | Decisão |
|---|---|
| [0000](docs/adrs/0000-context.md) | terreno brownfield; o script atual é evidência, não especificação |
| [0001](docs/adrs/0001-the-2026-01-anchor-is-41572553-rows-summing-78521752562-12.md) | a âncora de 2026-01, medida na origem |
| [0002](docs/adrs/0002-especie-appears-twice-so-columns-are-read-by-position.md) | leitura posicional, nunca por nome |
| [0003](docs/adrs/0003-money-rounds-half-to-even-at-two-decimals.md) | precisão declarada → arredonda no total → meio-para-par |
| [0004](docs/adrs/0004-column-13-is-a-truncated-description-not-a-second-code.md) | a chave é o código; agrupar por descrição é proibido |

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
