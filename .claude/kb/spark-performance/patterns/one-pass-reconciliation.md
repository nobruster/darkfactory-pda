# Reconferência de uma passada: os dois `exceptAll` numa agregação só

> **Purpose**: Deixar a reconferência de multiconjunto mais barata **sem tirá-la nem mudar o que ela prova**: um shuffle das duas entradas em vez de dois
> **MCP Validated**: 2026-09-23 (`RewriteExceptAll` em `Optimizer.scala` v3.5.5; equivalência medida em `apache/spark:3.5.9`)

## When to Use

- A reconferência (`exceptAll` nos dois sentidos) domina o tempo do job, **medido** pelo `/spark-perf`
- Nunca para substituir a reconferência por `count()` ou só por controles. Isso é tirá-la, e é proibido.

## A base: é o que o Spark já faz

`a.exceptAll(b)` é reescrito pelo otimizador (`RewriteExceptAll`) como união
com `+1` para `a` e `-1` para `b`, `sum` agrupado por **todas** as colunas, e
filtro `sum > 0`. O par `a−b` e `b−a` faz essa agregação **duas vezes**. O
saldo com sinal já contém os dois sentidos: positivo é "só em `a`", negativo é
"só em `b`".

## Implementation

```python
"""Multiconjunto nos dois sentidos com UMA agregação.

Equivale a (a.exceptAll(b).count(), b.exceptAll(a).count()), inclusive com
duplicatas e nulos (groupBy agrupa nulo com nulo, como o exceptAll).
"""
from pyspark.sql import functions as F

_SINAL = "__sinal_reconf"


def diferenca_multiconjunto(a, b) -> tuple[int, int]:
    if [(f.name, f.dataType) for f in a.schema] != [(f.name, f.dataType) for f in b.schema]:
        # union e exceptAll ALARGAM tipos em silêncio (decimal(14,2) vs (24,2)).
        raise ValueError("schemas diferentes: compare o schema antes")   # write-and-reconcile
    if _SINAL in a.columns:
        raise ValueError(f"coluna reservada {_SINAL} já existe")
    cols = a.columns
    u = (a.select(*cols, F.lit(1).alias(_SINAL))
         .unionByName(b.select(*cols, F.lit(-1).alias(_SINAL))))
    saldo = (u.groupBy(*cols).agg(F.sum(_SINAL).alias("saldo"))
             .filter(F.col("saldo") != 0))
    r = saldo.agg(
        F.coalesce(F.sum(F.when(F.col("saldo") > 0, F.col("saldo"))), F.lit(0)).alias("so_a"),
        F.coalesce(F.sum(F.when(F.col("saldo") < 0, -F.col("saldo"))), F.lit(0)).alias("so_b"),
    ).first()
    return int(r["so_a"]), int(r["so_b"])
```

Uso em `write-and-reconcile`, no lugar das duas linhas `exceptAll(...).count()`:

```python
so_julgado, so_relido = diferenca_multiconjunto(julgado, relido)
```

## Prova de equivalência (medida, 3.5.9)

| Caso | 2 × `exceptAll` | passada única |
|---|---|---|
| iguais, com duplicata e linha toda nula | (0, 0) | (0, 0) |
| duplicata a mais de um lado | (1, 0) | (1, 0) |
| chave nula trocada por valor | (1, 1) | (1, 1) |
| um centavo diferente | (1, 1) | (1, 1) |
| 3 cópias contra 1 + 2 linhas novas | (2, 2) | (2, 2) |

`Exchange` no plano físico: 4 para o par de `exceptAll(...).count()`, 2 para a
passada única. As duas entradas são embaralhadas **uma** vez, não duas.

## Antes de adotar numa fábrica

1. **Mantenha o teste de equivalência** (os cinco casos acima) como teste da
   fábrica. Uma reconferência nova que nunca foi comparada com a antiga não é
   reconferência (Regra 8: *verificador que nunca reprovou não é verificador*).
2. **Injete o defeito**: troque um centavo e duplique uma linha. A função tem
   de acusar os dois.
3. **Meça**: `PERF=MELHOR` no `/spark-perf`, com os controles idênticos.
4. Se a troca muda um arquivo do `creates_paths`, é uma Task-Spec (Regra 11).

## O que NÃO é otimização da reconferência

| Proposta | Por que não |
|---|---|
| comparar só `count()` | duplicata e troca passam |
| só os controles (soma, min, max) | duas trocas que se compensam passam |
| `subtract` em vez de `exceptAll` | é conjunto: duplicata passa |
| amostrar | prova a amostra, não a competência |
| hash da competência inteira (`sum(xxhash64(...))`) | colisão e compensação possíveis; é indício, não prova; pode **somar-se** à reconferência, nunca substituí-la |
| pular a reconferência "quando os controles batem" | os controles batem exatamente nos casos que ela existe para pegar |

## See Also

- [shuffle](../concepts/shuffle.md) (`exceptAll` por dentro)
- [write-and-reconcile](../../delta-lake/patterns/write-and-reconcile.md)
