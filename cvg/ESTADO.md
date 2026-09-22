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
| 4 · Consensus | `cvg review` | 🟢 `CHECK_CONSENSUS=OK` — 86 objeções |
| 5 · Tasking | `taskspec gate --stamp` | 🟢 `TIER=1` ×7 — HMAC v3 |
| 7 · Bind | `cvg bind` | 🟢 `CHECK_RUNTIME_CONTRACT=PASS` ×7 |
| 8 · Loop | `cvg loop` | 🟡 em curso — `contrato-ancora` primeiro |

⚠️ **O Pass 4 fecha por decisão, não por zerar objeções.** O gate exige que o
texto revisado seja o texto selado — corrigir depois da review move os hashes
e pede nova review. A saída é rodar uma review e **decidir sem editar**:
`--fix` para o já corrigido, `--accept --owner <nome> --risk <por quê>` para o
resto. O que fechou o gate foi esta linha:

```
ok  provenance verified: every current plan is the one attacked (14 files)
```

⚠️ **O `pytest` mora em `~/.local/bin`.** Só um shell de *login* o põe no
PATH, e o `taskspec` roda os evals em subprocesso sem login — o selo foi
recusado três vezes por `pytest: command not found`, que não era defeito da
spec. `scripts/checar_deps.py` acusa isso antes: `DEPS=MISSING`.

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
export PATH="$HOME/.local/bin:$PATH"          # sem isto, pytest some
export PATH="$PWD/.bin:$PATH"                 # o seamwise que o compose usa
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
export TASKSPEC_SIGNING_KEY_FILE="$PWD/.git/info/taskspec-signing-key"
converge/bin/cvg doctor host     # precisa dizer DOCTOR_HOST=OK
converge/bin/cvg next --guided
```

⚠️ **O `[+]` do conductor não é veredito.** Depois do Pass 4 fechar, o
`cvg next` continuava dizendo `NEXT_PASS=4` — ele confere que o arquivo
existe, quem decide é o gate. O gate disse `CHECK_CONSENSUS=OK`.

### Os cinco verificadores desta fábrica

Todos testados contra defeito injetado — verificador que nunca reprovou não
é verificador:

| Script | Token | Pega |
|---|---|---|
| `verificar_cercas.py` | `CERCAS` | as duas cercas divergindo, e cerca que casa com zero arquivo |
| `checar_w1.py` | `W1` | modo do arquivo **e do diretório**, e checksum não declarado |
| `checar_evidencia.py` | `EVIDENCIA` | sha256 da receita fora de dia com o disco |
| `checar_yaml.py` | `YAML_RECEITA` | o `": "` que vira mapa, antes do `map` reprovar |
| `checar_deps.py` | `DEPS` | ferramenta, import ou identidade git faltando |

⚠️ Antes de qualquer `cvg loop`, rode o pré-voo — três dos quatro bloqueios
do Pass 8 no template foram ambientais:

```bash
python3 fabrica/ponte/checar_deps.py cvg/tasks/T-*.md
```

## O que ainda não foi provado

⚠️ **O pipeline ainda não existe.** Os 10 ADRs, a tech-spec e as 7 Task-Specs
seladas descrevem o que a fábrica deve fazer. O Pass 8 é quem escreve, e está
em curso — começando pela `contrato-ancora`, que não depende de ninguém.

⚠️ **A âncora cobre uma competência só.** 2026-01 está medida; qualquer
outra nasce `NAO_MEDIDO` até alguém medir — faixa medida numa competência
não vira regra para outra.

⚠️ **Nenhum gate compara competências vizinhas** (ADR 0001). Um salto na
média passa sem que nada acuse. Está em `out_of_scope` como limite conhecido,
não resolvido em silêncio.

⚠️ **O produtor Spark não é deste plano** (ADR 0006). O juízo é exercido
contra envelope declarado, e isso **não** substitui julgar uma execução de
produtor real — dizer o contrário seria verde pelo motivo errado.

### O que já foi provado, e como

| | Prova |
|---|---|
| a âncora | 41.572.553 linhas, `78.521.752.562,12` — re-medida com script endurecido, e conferida contra o `darkfactory-inss` campo a campo |
| a gramática | formato brasileiro, 41.572.553 aceitos, **0** recusados, escala 2 |
| os códigos | 65, não os 51 da amostra — o `'60'` aparece 1.395 vezes em 41,5 milhões |
| os colapsos | 11 descrições cobrem 24 códigos |
| a precisão | 11 inteiros + 3 de escala = 14, sob soma monotônica (0 negativos) |
| o layout | 14 campos em toda linha; índice 12 só dígitos, 13 sempre textual |
| W-1 | diretório 555, três arquivos 444, **dois** checksums conferidos |
