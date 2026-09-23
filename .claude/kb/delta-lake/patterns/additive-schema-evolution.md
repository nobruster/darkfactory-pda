# Evolução de schema só aditiva

> **Purpose**: Deixar `mergeSchema` passar apenas quando a mudança é acrescentar coluna nova e anulável — e recusar todo o resto antes da escrita
> **MCP Validated**: 2026-09-23

## When to Use

- O contrato ganhou uma coluna (versão nova do contrato, com ADR)
- Nunca para "fazer a escrita passar" depois de um erro de schema

## Por que uma guarda

O `mergeSchema` do Delta acrescenta colunas, mas também troca `NullType` pelo
tipo que chegar, e em 3.2 existe type widening em preview. A garantia de
que a evolução é **só aditiva** é desta bancada, não da biblioteca. E ligar
`mergeSchema` por reflexo, depois de um erro de schema, é afrouxar o gate
(Regra 3): o erro dizia que o dado não casa com o contrato.

## Implementation

```python
"""Decide se uma escrita pode usar mergeSchema.

Token: EVOLUCAO=NENHUMA|ADITIVA|RECUSADA
"""
from delta.tables import DeltaTable
from pyspark.sql.types import DecimalType, NullType, StructType


def classificar_evolucao(tabela: StructType, novo: StructType,
                         autorizadas: set[str]) -> tuple[str, list[str]]:
    """`autorizadas`: colunas que o contrato novo (e o ADR) acrescentam, NOMEADAS.

    Isenção genérica ("qualquer coluna nova") devolve o furo com outro nome.
    """
    motivos = []
    t = {f.name.lower(): f for f in tabela.fields}
    n = {f.name.lower(): f for f in novo.fields}

    for nome, ft in t.items():
        fn = n.get(nome)
        if fn is None:
            motivos.append(f"{ft.name}: sumiu do DataFrame (viraria null)")
        elif fn.name != ft.name:
            motivos.append(f"{ft.name}: caixa diferente ({fn.name})")
        elif fn.dataType != ft.dataType:
            dinheiro = isinstance(ft.dataType, DecimalType)
            motivos.append(f"{ft.name}: {ft.dataType} → {fn.dataType}"
                           + (" — TIPO MONETÁRIO" if dinheiro else ""))

    novas = [n[k] for k in n.keys() - t.keys()]
    for f in novas:
        if f.name not in autorizadas:
            motivos.append(f"{f.name}: coluna nova não autorizada pelo contrato")
        elif isinstance(f.dataType, NullType):
            motivos.append(f"{f.name}: NullType — declare o tipo com cast")
        elif not f.nullable:
            motivos.append(f"{f.name}: nova e NOT NULL — o histórico não tem valor")

    if motivos:
        return "RECUSADA", motivos
    return ("ADITIVA" if novas else "NENHUMA"), []


def gravar_com_guarda(spark, df, caminho: str, autorizadas: set[str],
                      escrever) -> str:
    tabela = DeltaTable.forPath(spark, caminho).toDF().schema
    estado, motivos = classificar_evolucao(tabela, df.schema, autorizadas)
    for m in motivos:
        print(f"  {m}")
    print(f"EVOLUCAO={estado}")
    if estado == "RECUSADA":
        return estado
    # mergeSchema SÓ quando há o que acrescentar, e SÓ nesta escrita
    escrever(df, merge_schema=(estado == "ADITIVA"))
    return estado
```

## Decisões

| Mudança | Guarda | Caminho certo |
|---|---|---|
| coluna nova, anulável, nomeada no contrato | `ADITIVA` | `mergeSchema` nesta escrita |
| coluna nova não nomeada | `RECUSADA` | é dado que o contrato não previu: investigar |
| tipo mudou (qualquer) | `RECUSADA` | contrato novo + ADR + tabela nova ou migração explícita |
| `DECIMAL(14,2)` → `DECIMAL(16,2)` | `RECUSADA` | idem; em 3.2 nem o type widening cobre decimal |
| coluna sumiu | `RECUSADA` | viraria `null` em silêncio; o `NOT NULL` só pega se declarado |
| renomear | `RECUSADA` | exige column mapping; fora do escopo desta bancada |

⚠️ `overwriteSchema=true` substitui o schema da tabela inteira. Não há
guarda que o torne seguro por reflexo: só com ADR que o autorize, numa
escrita que registre isso no `userMetadata` (`"overwrite_schema_adr": "0012"`).

## Example Usage

```python
def escrever(df, merge_schema: bool):
    w = (df.write.format("delta").mode("overwrite")
         .option("replaceWhere", f"competencia = '{comp}'")
         .option("userMetadata", json.dumps(meta)))
    if merge_schema:
        w = w.option("mergeSchema", "true")
    w.save(SILVER)

gravar_com_guarda(spark, silver_df, SILVER, {"canal_pagamento"}, escrever)
```

## See Also

- [schema-enforcement](../concepts/schema-enforcement.md)
- [contract-table-bootstrap](contract-table-bootstrap.md)
