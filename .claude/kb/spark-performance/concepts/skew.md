# Skew: quando uma task carrega o stage

> **Purpose**: Reconhecer skew pela distribuição das tasks de um stage, e saber quando o AQE resolve sozinho e quando não resolve
> **Confidence**: 0.90
> **MCP Validated**: 2026-09-23 (`SQLConf.scala` na tag `v3.5.5`)

## Overview

Um stage só termina quando a última task termina. Com skew, uma chave (ou
poucas) concentra o dado numa partição, e uma task demora 10 ou 50 vezes a
mediana enquanto os outros núcleos ficam ociosos. O sintoma é o stage longo
com uma CPU ocupada e o resto parado.

## Como medir

Por stage, a partir do event log ([event-log](event-log.md)):

```text
skew_tempo = max(Executor Run Time) / mediana(Executor Run Time)
skew_bytes = max(entrada + shuffle lido) / mediana(entrada + shuffle lido)
```

| Leitura | Significado |
|---|---|
| `skew_tempo` alto **e** `skew_bytes` alto | skew de dado: uma chave pesa mais |
| `skew_tempo` alto, `skew_bytes` ≈ 1 | skew de custo (linha cara, GC, spill numa task) ou máquina lenta |
| menos de 4 tasks | razão não significa nada; o verificador devolve `-` |
| mediana 0 | razão indefinida; não force um número |

O limite do verificador (`--skew 5.0`) espelha o
`skewedPartitionFactor` do AQE. É **heurística**: calibre-o no seu ambiente,
medindo a mesma execução duas vezes.

## O que o AQE faz (Spark 3.5)

| Chave | Default | Efeito |
|---|---|---|
| `spark.sql.adaptive.enabled` | `true` | liga o AQE |
| `spark.sql.adaptive.skewJoin.enabled` | `true` | parte partições enviesadas **de join** (sort-merge e shuffled hash) |
| `spark.sql.adaptive.skewJoin.skewedPartitionFactor` | `5.0` | é enviesada se > fator × mediana... |
| `spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes` | `256MB` | ...**e** maior que este piso |
| `spark.sql.adaptive.optimizeSkewsInRebalancePartitions.enabled` | `true` | parte partições enviesadas de `REBALANCE` |

⚠️ **O `skewJoin` não alcança agregação.** Um `groupBy` enviesado não é
partido pelo AQE. O que salva a maioria dos casos é a **agregação parcial**
(`sum`, `count`, `min` e `max` agregam no lado do mapa antes do shuffle, e a
chave pesada chega como uma linha por partição de origem). Funções sem
agregação parcial eficiente (`collect_list`, `countDistinct` em cardinalidade
alta, UDAF) sofrem o skew inteiro.

⚠️ **Partição enviesada abaixo de 256 MB não é tratada**, mesmo com fator 50.
Num job de 132 MB em Delta, nenhuma partição de shuffle chega lá: o AQE não
vai agir, e só a medição mostra se o skew custa algo.

## Quando o skew não importa

Se o stage enviesado leva 2 % do tempo do job, consertá-lo não muda nada.
Ordene os stages por `Executor Run Time` e comece pelo topo.

## Common Mistakes

### Wrong

```python
df.repartition(400).groupBy("especie").agg(F.sum("vl"))   # repartition não parte uma chave
```

### Correct

```text
1. medir: o stage do groupBy tem skew_tempo alto E pesa no total?
2. a agregação tem parcial (sum/count)? então o skew está noutro lugar: medir de novo
3. é join? confirmar que o AQE está ligado e a partição > 256MB; senão, salting
```

## Related

- [skew-mitigation](../patterns/skew-mitigation.md)
- [shuffle](shuffle.md)
