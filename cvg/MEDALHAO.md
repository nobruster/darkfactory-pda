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
| 3 · Decompose | `seamwise map` | 🟢 `SEAM_MAP=READY` — 3 costuras |
| 4 · Consensus | `cvg review --check` | 🟢 `CHECK_CONSENSUS=OK` — 10 rodadas, 51 objeções |
| 5 · Tasking | `taskspec gate --stamp` | 🟢 `TIER=1` ×3, HMAC v3 |
| 7 · Bind | `cvg bind --check` | 🟢 `CHECK_RUNTIME_CONTRACT=PASS` ×3 |
| 8 · Loop | `cvg loop` | 🟡 Bronze em curso |

### O que o Pass 7 impôs ao Pass 8

Lido do `execution-profile.yaml`, não da tela:

| | |
|---|---|
| `net.egress` / `vcs.push` | **False** — não sai para a rede, não publica |
| `external_writes` | `deny` |
| `fs.write` deny_scope | `_raw`, `contracts`, `cvg/docs/adrs` — o oráculo |
| `authority.epoch` | inclui o **hash da folha** |
| `revoke_on` | `settle`, `block`, `budget_exhausted`, `epoch_change` |

A autoridade é ligada a um epoch que carrega o hash da folha. **Mudar a folha
revoga a autoridade** — o mesmo princípio que bloqueou o Pass 5 quando editei
o `pda-recipe.yaml`, agora aplicado à execução.

### ⚠️ O `RED` do gate-only é esperado, e provar isso importa

```
bash: infra/medalhao-evals.sh: No such file or directory
RED — The task's own eval exited non-zero. Do NOT open a PR.
```

Medido antes de despachar: o eval invoca `infra/medalhao-evals.sh`, e a própria
tarefa **declara criá-lo** em `creates_paths`. Antes de construir, ele não
existe — e o gate reprova, como deve. *"fails are expected for unbuilt work."*

A distinção não é acadêmica: se fosse defeito de desenho, o loop bateria no
mesmo muro cinco vezes e sairia `EXHAUSTED`. O guard é explícito — **"Do not
hack the eval"**, e um eval que passasse antes da obra não provaria nada.

## 🛑 Pass 8 · Bronze — `result: blocked`, e o defeito é do plano

```
ITER=2  STRIKES=1  ELAPSED_PRIOR=601
[engine timed out after 600s — the attempt was killed]
```

A tentativa 1 gastou **os 600s inteiros e escreveu ZERO arquivos**. Não é
lentidão do agente. Medido:

| O que a tarefa exige | O que o contrato de runtime permite |
|---|---|
| `infra/medalhao-evals.sh` instala `pytest` no contêiner | `net.egress: False` |
| — | `policy.network: deny` |

**O contrato de runtime proíbe o que a tarefa exige.** Instalar qualquer coisa
precisa de rede, e o Pass 7 — corretamente — negou rede a um agente que escreve
código. Nenhuma das 5 tentativas poderia ter sucesso.

E o escopo é grande demais para 600s de qualquer jeito: um leitor Parquet em
Spark, uma suíte pytest e um orquestrador de contêiner, com um `then` de
**1.110 palavras** só no B-1.

### De onde veio o defeito

Da **minha correção da rodada 3**. O adversário disse que "montar o ambiente é
parte da tarefa" não tinha caminho declarado; eu subi `effort` S→M e acrescentei
`infra/medalhao-evals.sh` ao `creates_paths`.

Resolvi o `path_policy` e **não perguntei se o trabalho cabia no orçamento, nem
se o contrato permitiria fazê-lo.** É a mesma classe dos outros: corrigi a junta
apontada sem olhar o que ela implicava duas camadas adiante.

### O que o motor fez certo

| | |
|---|---|
| worktree isolada | a árvore principal ficou **intacta** |
| `result: blocked` no receipt | não fingiu sucesso |
| `path_policy: not-run` | honesto — nada foi escrito, nada foi avaliado |
| brief-002 | trouxe o erro da tentativa 1 e proibiu repetir |

⚠️ **Parei o loop na tentativa 2 em vez de deixar queimar as 5.** O detector de
estagnação teria parado em 3 falhas idênticas, mas eu já sabia que as 5 eram
impossíveis — esperar seria gastar motor para confirmar o que a medição já
mostrava.

### O que precisa mudar, e em que passe

A correção **não é** afrouxar o contrato de runtime (isso é a Regra 3 pelo
avesso) nem editar o eval (o guard proíbe, e com razão). É reconhecer que
**preparar o ambiente não é tarefa de agente sem rede**:

- o ambiente de eval vira **pré-requisito do host**, como `docker` e `pytest`
  já são — montado uma vez, fora do loop
- `infra/medalhao-evals.sh` passa a **usar** o ambiente, não a construí-lo
- e aí Bronze volta a caber: um módulo e seus testes

Isso é mudança de **Pass 3** (o plano), que obriga a re-selar no Pass 5 — e é
exatamente o que a Regra 10 manda fazer em vez de ampliar a cerca.

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

## O adversário cross-family — dez rodadas

| | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 |
|---|---|---|---|---|---|---|---|---|---|
| objeções | 5 | 6 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| **classes novas** | **5** | **6** | **5** | **5** | **3** | **1** | **1** | **2** | **2** |
| `high` | 4 | 4 | 4 | 3 | 3 | 4 | 4 | 3 | 3 |
| `critical` | 0 | **1** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**46 objeções.** A linha que decide é *classes novas*: caiu de 5–6 para 1–2, e
as repetições convergiram em duas famílias que **não são do plano resolver**.

### ⚠️ O padrão que custou cinco rodadas para eu enxergar

```
R2  mando Gold comparar o mapa    → R3: Silver não o produz
R3  mando Silver produzir          → R4: Bronze não o produz
R3  crio infra/medalhao-evals.sh   → R4: nenhum eval o chama
R2  ponho pyspark em required_tools → R5: impasse de bootstrap
R8  declaro localcontext(Context()) → R9: herda do DefaultContext
```

Cada correção minha virava o achado da rodada seguinte. **Eu estava tapando a
junta que o adversário apontava, em vez de declarar o contrato na origem.**

A R5 foi o ponto de virada: o mapa chegou em **Bronze**, que é a origem, e
parou de subir. Da R6 em diante o adversário passou a ramificar das minhas
próprias correções, não a encontrar camadas novas.

### Os contraexemplos executados que derrubaram o que eu achava rigoroso

| O que eu escrevi | O que o contraexemplo mostrou |
|---|---|
| *"os DOIS controles precisam bater"* | a R-5 exige os **cinco**; `max` acima do ancorado passa |
| *"comparação entre Decimal e Decimal"* | `Decimal(str(1.25))` é finito, não negativo, escala 2 — e a entrada era float |
| soma + cardinalidade provam o agregado | `{'01':10,'03':20}` e `{'01':11,'03':19}` têm as duas iguais |
| contagem de linhas idêntica | duas linhas do **mesmo código** trocando valores passam |
| `localcontext()` com `prec` e `rounding` | copia o global, **traps inclusive** |
| `localcontext(Context(prec, rounding))` | `Context()` herda de `DefaultContext`, também mutável |

As duas últimas são a mesma lição, e ela generalizou para a
[Regra 5](../../darkfactory-template/AGENTS.md) da bancada:
**o que você não declara, você herda.**

### ⚠️ Regra 7 aplicada a mim, duas vezes

Na R8 o adversário deu contraexemplo executado para as traps. Eu escrevi a
solução, publiquei no template — e **não executei contraexemplo contra a
solução**. A R9 a refutou.

Antes disso, eu tinha reportado contaminação no lago que não existia: medi a
união das partições e culpei a parte. Objeção minha também é hipótese.

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
