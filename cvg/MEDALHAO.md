# Medalhão — estado da descida

Bronze, Silver e Gold sobre a partição já publicada no lago.
Atualizado em 22/09/2026.

## Por que pela cadeia

O produtor Spark e o gravador do lago eu escrevi **por fora**: sem costura,
sem objeção de adversário, sem selo, sem escopo declarado. Dezesseis arquivos
entraram assim, e nada reprovou — foi disso que nasceu a
[Regra 11](../../darkfactory-template/AGENTS.md) e o
`scripts/verificar_procedencia.py`.

O medalhão desce pela cadeia. É o que a regra passou a exigir.

## Posição

| Passe | Gate | Veredito |
|---|---|---|
| 3 · Decompose | `seamwise map` | 🟢 3 costuras inseridas, schema OK |
| 4 · Consensus | `cvg review` + agentes | 🟡 **em curso** |
| 5 · Tasking | `taskspec gate --stamp` | ⬜ |
| 7 · Bind | `cvg bind` | ⬜ |
| 8 · Loop | `cvg loop` | ⬜ |

## As três costuras

| Costura | Recusa quando |
|---|---|
| `SEAM-BRONZE` | a partição não reproduz os **dois** controles da âncora |
| `SEAM-SILVER` | a soma muda entre camadas, ou um defeito fica sem classificação |
| `SEAM-GOLD` | o agregado não reconcilia com a âncora ao centavo |

Cada uma com `behavior=2`, `evals=3`, `anti_patterns=3` — exatos, como o
schema exige — e 2 caminhos sob `effort: S`, cujo limite é 2.

### O que cada uma carrega de lição medida

**Bronze** proíbe, em `anti_patterns`, *somar todas as partições e comparar o
total com a âncora*. Foi exatamente o erro que me fez reportar contaminação
onde a partição real batia exato:

```
41.622.553   a união das duas partições     ← o que eu medi
41.572.553   a partição real = a âncora     ← o que eu deveria ter medido
```

Agregado sem `GROUP BY` na coluna de partição não mede partição nenhuma.

**Silver** aplica a [Regra 4](../../darkfactory-template/AGENTS.md) onde ela é
mais tentadora: os 11 colapsos que cobrem 24 códigos. Deduplicar
"resolveria" — e destruiria a prova de que a origem publica assim. A chave é o
**código** (ADR 0004): agrupar por descrição fundiria os 24, o total
continuaria batendo, e os mapas por código sairiam errados sem nada acusar.

**Gold** arredonda uma vez no total (ADR 0004), HALF_EVEN lido do contrato
(ADR 0001), precisão declarada (ADR 0006). Reconcilia recalculando das linhas
publicadas, nunca herdando de Bronze — senão provaria a conta de outra camada.

## O que os gates reprovaram, e estavam certos

| Gate | Acusou | Era |
|---|---|---|
| `seamwise map` | `duplicate_id: LANE-MEDALHAO` | dei a mesma lane às três; a convenção é uma por costura |
| `checar_yaml.py` | `": "` dentro de escalar | três ocorrências; vira mapa e o `map` falha |

Ambos corrigidos. O segundo é a armadilha que o `AGENTS.md` documenta.

## ⚠️ O `NEXT=READY` que era verde pelo motivo errado

Depois de inserir as costuras, o motor respondeu `NEXT=READY`. Não era sobre
elas:

| | |
|---|---|
| receita | `2026-09-22 19:14` |
| `task-plan.json` | `2026-09-21 23:39` — **20 horas antes** |
| medalhão no plano | **0 ocorrências** |

O plano tem 7 unidades, todas de ontem. Despachar o adversário ali faria ele
atacar as sete antigas enquanto as três novas passavam sem exame — o
*"verde pelo motivo errado"* que o `AGENTS.md` já registra para `map` × `plan`.

**Antes de despachar o adversário, confira a data do `task-plan.json` contra a
da receita.** O `[+]` do conductor não é veredito, e `NEXT=READY` também não.

## O `map` e o `create_path_already_exists`

O `map` confere `creates_paths` contra a árvore de trabalho
(`seamwise/src/seamwise/engine/recipe.py:474`). As 7 tarefas originais
declaram arquivos que o Pass 8 **já construiu**, então sempre tropeçam.

Medido, não suposto:

| Árvore | Veredito |
|---|---|
| atual, receita **antes** da minha edição | `AMBIGUOUS` — já reprovava |
| atual, receita com o medalhão | `AMBIGUOUS` — mesmas queixas |
| espelho sem `src/pda` e `tests/` | `AMBIGUOUS` — **1 só** queixa, a do contrato |

Em **nenhuma** das rodadas alguma queixa citou `bronze`, `silver`, `gold` ou
`medalhao`. Conferido duas vezes, com `grep` explícito.

A queixa que sobra é de `T-20260921-contrato-ancora`, que declara
`contracts/competencia-202601.yaml` em `creates_paths` — e esse arquivo
precisa existir como evidência. É uma tensão da tarefa original, anterior ao
medalhão.

## O que os quatro agentes acharam

Despachados em paralelo (Regra 8). **Dezenove achados**, cada um medido antes
de virar correção (Regra 7). Os que mudaram o plano:

| # | Achado | Veredito |
|---|---|---|
| C2 | citei ADR **superseded**, e da numeração do *template* | confirmado, corrigido |
| C1 | `negativ` aparecia **0×** — derrubei o domínio não-negativo | confirmado, corrigido |
| E1 | *"nomeadas na saída"* afirma isolação sem medi-la | confirmado, corrigido |
| E4 | `eval_3` dizia cobrir B-2 com `-k` que só tocava B-1 | confirmado, corrigido |
| — | três tokens passariam com implementação errada | confirmado, corrigido |
| **🔴** | **nenhum ambiente roda o eval de Bronze** | confirmado, declarado |
| **🔴** | **minha própria correção recusaria o dado correto** | confirmado, desfeito |
| — | `src/medalhao/` fora das cercas | **refutado** |
| ⬜ | Gold produz e ninguém consome | **em aberto** |

### O gate que eu escrevi e recusaria o dado correto

Vinte minutos depois de commitar a correção C3, o quarto agente mirou nela:

```
gravar_lago.py:87-90 projeta TRÊS colunas — especie_codigo,
especie_descricao, vl_liquido — mais a de partição.
NENHUMA é procedência. O hash vai para /tmp/prova-lago.json,
FORA do lago.
```

Como eu tinha escrito, Bronze devolveria `NAO_MEDIDO` na partição **correta**,
a que bate ao centavo. É o **quinto** *"gate que recusaria o arquivo correto"*
desta fábrica — e eu o escrevi enquanto corrigia outra coisa, apertando o
oráculo contra um número que não medi.

⚠️ **A Regra 9 tem duas faces, e a segunda é mais fácil de cair.** Afrouxar o
oráculo é manobra que a gente reconhece; **apertá-lo contra o que não mediu**
parece rigor.

### A pinça da infraestrutura

| | pytest | leitor de Parquet |
|---|---|---|
| host | (fora do PATH) | **nenhum** — sem pyspark, pyarrow, pandas, duckdb, java |
| `pda-spark` | **não tem** | pyspark 3.5.9 ✅ |

Os três evals de Bronze são `pytest`. Não existe hoje ambiente onde eles rodem
contra o lago. `required_tools` dizia `[git, bash, python3, pytest]` — falso
para uma camada que lê `s3a://`. Agora declara `docker` e `pyspark`, e montar
o ambiente virou **parte da tarefa**, não pressuposto dela.

### O achado refutado

`src/medalhao/` fora das cercas **não é defeito** — e a refutação veio do
próprio agente que o levantou. `src/` é a **superfície de construção**: tem de
ser gravável, senão nenhuma tarefa do Pass 8 escreve lá. A cerca é teto do que
ninguém toca (oráculo, ADRs, medidores); quem estreita `src/` é o
`creates_paths`. Não mexi nas cercas.

## ⬜ Em aberto — o medalhão não reencontra o juízo

`SEAM-GOLD` produz `gold reconciliado` e **ninguém consome**. `SEAM-JUIZO`
continua consumindo `[envelope do produtor, contrato validado]`; nada olha
para Gold.

As dez costuras formam **dois ramos paralelos** que partem de `contrato
validado` e nunca se reencontram. O `steel_thread` enfileira as dez em
sequência, o que *parece* cadeia única — mas ordem não cria dependência de
dado. Gold pode reconciliar e o veredito da fábrica sair sem jamais tê-lo
visto.

É a mesma classe da `OBJ-C1`, que criou a `SEAM-FRONTEIRA` justamente porque
*"dava para concluir a cadeia sem nunca conectar o produtor que será
julgado"*. Precisa ser medido antes de decidir como ligar.

## O adversário cross-family — o que os agentes não alcançaram

| Rodada | Objeções | O que trouxe |
|---|---|---|
| 1 | 5 (4 high, 1 medium) | nenhuma repetia achado de agente |
| 2 | 6 (1 critical, 4 high, 1 medium) | **contraexemplo executado** |
| 3 | em curso | contra o texto já corrigido duas vezes |

### Os dois contraexemplos que derrubaram o que eu achava rigoroso

**Redistribuição compensada** — Gold citava `total_por_codigo` zero vezes:

```
{'01': 10.00, '03': 20.00}   soma 30.00
{'01': 11.00, '03': 19.00}   soma 30.00
```

Soma igual, chaves iguais, **mapas diferentes**. Um valor no código errado
passava por soma e cardinalidade. A `SEAM-FRONTEIRA` já sabia disso — *"com um
mapa só, deslocar valores entre códigos seria aprovado por comparação consigo
mesmo"* — e o medalhão tinha perdido a lição.

**Float convertido** — eu escrevi *"comparação entre Decimal e Decimal"*
achando que bastava:

```
Decimal(str(1.25)) = 1.25   finito, não negativo, escala 2
```

Passa em **todas** as verificações de domínio que escrevi, e a entrada era
`DOUBLE`. A R-4 manda **recusar** float, não convertê-lo: converter apaga a
evidência da entrada proibida. A recusa tem de ser do **tipo do esquema**,
antes de ler valor algum.

### E os cinco controles, não dois

A tech-spec diz `R-5 (must)`: os **cinco** comparados individualmente. Eu
escrevi *"os DOIS controles precisam bater"* — dois é mais que um, mas é menos
que cinco. `min_vl_liquido`, `max_vl_liquido` e `linhas_invalidas` não eram
olhados por ninguém, e uma alteração compensada entre duas linhas empurra o
máximo acima de 183.725,76 sem mexer em contagem nem soma.

### ⚠️ O padrão das rodadas: corrijo uma coisa e crio a seguinte

A marca `PROCEDENCIA_NAO_VINCULADA` que criei na rodada 1 virou o **C1
critical** da rodada 2 — porque eu mandei propagá-la sem declarar quem a
consome. Cada camada cumpriria o próprio eval e a marca se perderia na
transformação.

É por isso que o Pass 4 **não fecha por zerar objeções**. Fecha por decisão, e
cada rodada é uma chance de ver o que a anterior não via.

## O que falta

- [ ] Fechar o Pass 4 — decidir **sem editar** (editar move os hashes)
- [ ] **Ligar Gold ao juízo** — ou registrar por que são ramos separados
- [ ] Pass 5 — selar as três folhas
- [ ] Pass 7, Pass 8
- [ ] Declarar no contrato o mapa código→descrição dos 11 colapsos aprovados —
      hoje ele tem as cardinalidades e **não** o referencial, e sem ele Silver
      devolve `NAO_MEDIDO`. `scripts/medir_colapso.py` já sabe medi-lo; falta
      alguém aprovar com data.
- [ ] Tarefa própria para o lago carregar a procedência (toca `gravar_lago.py`,
      que está sem Task-Spec — Regra 11)
