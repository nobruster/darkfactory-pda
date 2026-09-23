# Shuffle: o custo que cada operação larga cobra

> **Purpose**: Saber quais operações embaralham, quantas vezes, e ler o shuffle por stage no event log
> **Confidence**: 0.90
> **MCP Validated**: 2026-09-23 (`Optimizer.scala` e `SQLConf.scala` na tag `v3.5.5`; `Exchange` contado no plano físico do 3.5.9)

## Overview

Shuffle é a fronteira entre stages: cada task grava sua saída particionada
pela chave (`Shuffle Bytes Written`), e o stage seguinte busca os pedaços
(`Remote/Local Bytes Read`). Custa serialização, disco e rede. No plano
físico, cada shuffle é um nó `Exchange`.

## Quem embaralha

| Operação | Shuffle | Observação |
|---|---|---|
| `filter`, `select`, `withColumn`, `cast` | não | estreitas, ficam no mesmo stage |
| `groupBy(k).agg(...)` | 1 | com agregação parcial antes: embaralha já reduzido |
| `agg(...)` sem chave (total) | 1, pequeno | parcial por partição, depois 1 partição |
| `count()` | 1, pequeno | é uma `agg` global, e é **uma ação**: relê a fonte |
| `distinct()` / `dropDuplicates()` | 1 | agregação por todas as colunas |
| `orderBy` | 1 + job de amostragem | particionamento por faixa |
| `join` sort-merge | 2 (um por lado) | o default acima do limite de broadcast |
| `join` broadcast | 0 | lado pequeno vai inteiro para cada task |
| `exceptAll` | 1 **por chamada** | reescrito como união ±1 + agregação por todas as colunas |
| `repartition(n)` / `repartition(col)` | 1 | `coalesce(n)` não embaralha |

## `exceptAll` por dentro

O otimizador (`RewriteExceptAll`) troca `a.exceptAll(b)` por:

```text
Union( a + coluna vcol=+1 , b + coluna vcol=-1 )
  → Aggregate(todas as colunas, sum(vcol))  → filtro sum > 0 → replica as linhas
```

É uma agregação **por todas as colunas das duas entradas**. Reconferir nos dois
sentidos com dois `exceptAll` embaralha as duas entradas **duas vezes**. A
mesma agregação feita uma vez dá os dois sentidos: ver
[one-pass-reconciliation](../patterns/one-pass-reconciliation.md).

Contado no plano físico (3.5.9): `exceptAll(...).count()` gera 2 `Exchange`,
o par gera 4, e a passada única gera 2.

## Broadcast

| Chave | Default (3.5) |
|---|---|
| `spark.sql.autoBroadcastJoinThreshold` | `10MB` |
| `spark.sql.adaptive.autoBroadcastJoinThreshold` | (cai no anterior) — o AQE converte em broadcast com o tamanho **medido** |

Dimensão pequena (tabela de espécies, códigos) com fato grande: broadcast
elimina o shuffle do fato. Force com `F.broadcast(dim)` só se medir que o
otimizador não escolheu, e nunca com uma "dimensão" que cresce com o fato.

## Passes sobre o dado

Cada **ação** (`count`, `first`, `collect`, `write`, `toPandas`) dispara um
job que, sem cache, **relê a fonte desde o início**. Quatro controles como
quatro ações são quatro leituras de 41 milhões de linhas:

```python
df.count(); df.agg(F.sum("vl")).first(); df.agg(F.min("vl")).first(); ...   # 4 passes
df.agg(F.count(F.lit(1)), F.sum("vl"), F.min("vl"), F.max("vl")).first()     # 1 pass
```

Ver [single-pass-controls](../patterns/single-pass-controls.md).

## Ler no event log

| Por stage | Leitura |
|---|---|
| `shW` alto, `shR` 0 | stage de mapa: grava para o próximo |
| `shR` alto | stage de redução: consome o anterior |
| `shW` ≈ entrada | nada foi reduzido antes do shuffle (sem parcial, ou colunas demais) |
| mesmo `Stage Name` várias vezes | a mesma linha do script recomputa: falta cache ou sobra ação |

## Common Mistakes

### Wrong

```python
julgado = fonte.transform(regras)          # sem cache
controles(julgado); gravar(julgado); reconferir(julgado)   # 3 recomputações da fonte
```

### Correct

```python
julgado = fonte.transform(regras).cache(); julgado.count()   # materializa 1 vez
controles(julgado); gravar(julgado); reconferir(julgado)
julgado.unpersist()                                          # devolve a memória
```

## Related

- [event-log](event-log.md) · [spill](spill.md) · [skew](skew.md)
- [one-pass-reconciliation](../patterns/one-pass-reconciliation.md)
