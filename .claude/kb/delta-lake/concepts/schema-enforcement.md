# Schema Enforcement e Evolution

> **Purpose**: Imposição de schema sempre ligada; evolução só aditiva, opt-in e conferida; tipo monetário nunca muda por escrita
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-23

## Overview

Numa escrita pelo `DataFrameWriter`, o Delta **impõe** o schema da tabela:
toda coluna do DataFrame precisa existir na tabela, os tipos precisam casar,
e nomes não podem diferir só por caixa. Qualquer divergência levanta
exceção. É o gate mais barato da fábrica, e está ligado por padrão — o
trabalho é **não desligá-lo**.

Regras da doc (3.2.1, *Schema validation*):

1. *"All DataFrame columns must exist in the target table."* Coluna da tabela
   ausente no DataFrame vira `null` — e o `NOT NULL` é o que acusa isso.
2. *"DataFrame column data types must match the column data types in the
   target table. If they don't match, an exception is raised."*
3. *"DataFrame column names cannot differ only by case."*

## The Pattern

```python
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

TIPO_VALOR = DecimalType(contrato.precisao, contrato.escala)   # do contrato

saida = df.select(
    F.col("competencia").cast("string"),
    F.col("especie_codigo").cast("string"),
    F.col("vl_liquido").cast(TIPO_VALOR),      # cast EXPLÍCITO ao tipo do contrato
)
(saida.write.format("delta")
    .mode("overwrite")
    .option("replaceWhere", f"competencia = '{competencia}'")
    .save(CAMINHO))                             # sem mergeSchema, sem overwriteSchema
```

## As três alavancas, e a política desta bancada

| Alavanca | O que faz | Política |
|---|---|---|
| `mergeSchema=true` (por escrita) | acrescenta colunas novas do DataFrame | **opt-in**, só depois da [guarda aditiva](../patterns/additive-schema-evolution.md) |
| `spark.databricks.delta.schema.autoMerge.enabled` | liga `mergeSchema` para a sessão inteira | **sempre `false`** — opt-in por sessão não é opt-in |
| `overwriteSchema=true` | substitui o schema da tabela | **nunca silencioso**: só com ADR que o autorize, e a escrita registra isso no `userMetadata` |

⚠️ **`mergeSchema` não é só "adicionar coluna".** A doc registra que uma
coluna `NullType` na tabela é trocada pelo tipo que chegar, e a partir da
3.2 existe **type widening** (preview, `delta.enableTypeWidening`) que
aplica alargamentos automáticos em `INSERT`/`MERGE`. Em 3.2 o alargamento
cobre só `byte → short → int`; alargar **decimal** só chegou no 4.0. Mesmo
assim: a garantia "só aditiva" é **nossa**, imposta pela guarda antes da
escrita, não uma propriedade do `mergeSchema`. Não ligue
`delta.enableTypeWidening` em tabela desta bancada.

## Dinheiro

| Situação | Resultado |
|---|---|
| DataFrame `DecimalType(24,2)` → coluna `DECIMAL(14,2)` | exceção de schema (tipos precisam casar) |
| DataFrame `DoubleType` → coluna `DECIMAL(14,2)` | exceção de schema |
| `cast(DecimalType(14,2))` de valor que não cabe, ANSI **ligado** | exceção `NUMERIC_VALUE_OUT_OF_RANGE` |
| o mesmo `cast`, ANSI **desligado** | **`NULL`, sem erro** |
| `sum()` de `DECIMAL(14,2)` | `DECIMAL(24,2)` (p+10, teto 38) |

O último item é por que a gold declara o tipo do **acumulador** no contrato
em vez de herdar o do `sum()`. E o penúltimo é o quarto modo de falha da
Regra 5: `spark.sql.ansi.enabled=true` é obrigatório na sessão.

⚠️ Com ANSI ligado, `cast` de **string malformada** para decimal também
levanta. Validar o formato antes (regex → `NULL` explícito → contar os
`NULL`) mantém o descarte medido, em vez de uma exceção no meio do job ou,
com ANSI desligado, um `NULL` silencioso.

⚠️ SQL `INSERT INTO` segue a política de atribuição do Spark e pode
**converter** o tipo implicitamente. Para camada monetária, escreva pelo
`DataFrameWriter` com `cast` explícito — o erro de tipo precisa aparecer.

## Quick Reference

| Input | Output | Notes |
|-------|--------|-------|
| coluna extra no DataFrame, sem `mergeSchema` | exceção | correto: o contrato não a previa |
| coluna extra, com `mergeSchema` | coluna nova, `null` no histórico | só após a guarda |
| tipo diferente | exceção | mudança de contrato → ADR novo |

## Common Mistakes

### Wrong

```python
df = spark.read.option("inferSchema", "true").csv(p)          # vl vira double
df.write.format("delta").option("mergeSchema", "true").mode("append").save(t)
```

### Correct

```python
df = spark.read.schema(SCHEMA_DO_CONTRATO).csv(p)             # tudo string
df = df.withColumn("vl", para_decimal(F.col("vl"), p_, s_))    # formato validado
df.write.format("delta").mode("append").save(t)                # imposição ligada
```

## Related

- [constraints](constraints.md)
- [additive-schema-evolution](../patterns/additive-schema-evolution.md)
- [contract-table-bootstrap](../patterns/contract-table-bootstrap.md)
