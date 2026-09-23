# Controles numa passada, cache com dono

> **Purpose**: Medir todos os controles com uma ação só, e fazer cache só do que é relido, liberando-o quando deixa de servir
> **MCP Validated**: 2026-09-23

## When to Use

- O job chama `count()`, `sum`, `min` e `max` em ações separadas
- O mesmo `Stage Name` aparece várias vezes no relatório do `/spark-perf`
- O DataFrame julgado é usado para controles, gravação **e** reconferência

## Implementation

```python
"""Controles em uma ação. Mesma função para o julgado e o relido (write-and-reconcile)."""
from pyspark.sql import functions as F


def controles(df, valor: str = "vl_liquido") -> dict:
    a = df.agg(
        F.count(F.lit(1)).alias("linhas"),
        F.sum(F.when(F.col(valor).isNull(), 1).otherwise(0)).alias("nulos"),
        F.sum(valor).alias("soma"),
        F.min(valor).alias("minimo"),
        F.max(valor).alias("maximo"),
    ).first()                                     # UM job, UM passe
    return {k: (None if a[k] is None else str(a[k])) for k in a.asDict()}


def pipeline_competencia(fonte, regras, gravar, reconferir):
    julgado = regras(fonte).cache()
    try:
        ctl = controles(julgado)                  # materializa o cache nesta ação
        if int(ctl["linhas"]) == 0:
            return "NAO_MEDIDO", ctl              # Regra 9
        v = gravar(julgado)
        return reconferir(julgado, v), ctl
    finally:
        julgado.unpersist()                       # o cache tem dono e fim
```

## Por que cada peça

| Peça | O que evita |
|---|---|
| uma `agg` com 5 expressões | 5 leituras da fonte (5 jobs) |
| `cache()` **antes** da primeira ação | a gravação e a reconferência recomputarem as regras da fonte |
| o `controles()` como ação que materializa | um `count()` extra só para "aquecer" o cache |
| `unpersist()` no `finally` | o cache ocupar a memória unificada do stage seguinte e causar spill |
| `str()` do resultado | float no meio da comparação (Regra 5) |

## Cache: quando sim, quando não

| Situação | Cache? |
|---|---|
| DataFrame usado por 2+ ações | sim |
| usado por uma ação só | não: é custo sem retorno |
| fonte Parquet/Delta lida uma vez e filtrada | não: a leitura com *pushdown* é barata |
| resultado de regras caras (joins, janelas) reusado | sim |
| cache maior que a memória de armazenamento | `persist(StorageLevel.MEMORY_AND_DISK)`, e **medir**: pode ser pior que recomputar |

⚠️ **Cache não muda o resultado, e mudar o resultado é defeito.** Se os
controles mudarem ao ligar ou desligar o cache, há não-determinismo nas regras
(`rand()`, `monotonically_increasing_id()`, `first()` sem ordem,
`dropDuplicates` sem chave total). Isso é `MODERN_DEFECT` a classificar, não
uma questão de performance.

⚠️ **A sessão Spark e a comparação Decimal:** uma `sum` sobre
`DecimalType(14,2)` devolve `DecimalType(24,2)`. Os controles comparam por
`str`, que coincide entre as duas precisões. A checagem de **schema** é que
pega a diferença de tipo, e ela vem antes (ver `write-and-reconcile`).

## Example Usage

```python
estado, ctl = pipeline_competencia(bronze_2026_01, aplicar_regras,
                                   gravar_silver, reconferir_silver)
print(json.dumps({"controles": ctl}))
print(f"RECONFERENCIA={estado}")
```

## Medir o ganho

No relatório do `/spark-perf`, antes e depois:

| Sinal | Antes | Depois |
|---|---|---|
| stages com o mesmo `Stage Name` de leitura | N | 1 |
| `Input Bytes` total | N × fonte | ≈ 1 × fonte |
| `PERF=` | — | `MELHOR`, com os controles idênticos |

## See Also

- [shuffle](../concepts/shuffle.md) (passes sobre o dado)
- [write-and-reconcile](../../delta-lake/patterns/write-and-reconcile.md)
