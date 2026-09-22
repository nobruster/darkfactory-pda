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

## O que falta

- [ ] Pass 4 — adversário cross-family **e** os quatro agentes (Regra 8)
- [ ] Regenerar o `task-plan.json` para que inclua as três costuras
- [ ] Pass 5 — selar as três folhas
- [ ] Pass 7, Pass 8
- [ ] `src/medalhao/` nas **duas** cercas, antes de o Pass 8 escrever lá
