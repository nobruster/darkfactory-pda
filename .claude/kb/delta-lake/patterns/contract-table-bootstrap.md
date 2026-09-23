# Criar a tabela a partir do contrato

> **Purpose**: A tabela nasce com o schema, as constraints e a retenção que o contrato declara — antes da primeira linha, e não inferidos dela
> **MCP Validated**: 2026-09-23

## When to Use

- Primeira gravação de uma camada (bronze, silver ou gold)
- Ao subir uma fábrica nova, junto com o contrato
- Nunca como "correção" de uma tabela existente: mudança de schema é ADR novo

## Implementation

```python
"""Cria (se não existe) e CONFERE (se existe) uma tabela Delta contra o contrato.

Token: TABELA=CRIADA|CONFERE|DIVERGE|ERRO
"""
from delta.tables import DeltaTable
from pyspark.sql.types import DecimalType, StringType, StructField, StructType


def schema_do_contrato(c) -> StructType:
    """O tipo monetário vem do contrato. Nada aqui é inferido."""
    return StructType([
        StructField("competencia", StringType(), nullable=False),
        StructField("especie_codigo", StringType(), nullable=False),
        StructField("especie_descricao", StringType(), nullable=True),
        StructField("vl_liquido",
                    DecimalType(c.politica_decimal.precisao,
                                c.politica_decimal.escala),
                    nullable=False),
    ])


CHECKS = {
    # nome -> expressão. Cada uma é hipótese de domínio MEDIDA (ver constraints.md)
    "vl_liquido_nao_negativo": "vl_liquido >= 0",
    "competencia_formato": "competencia RLIKE '^[0-9]{4}-[0-9]{2}$'",
}

PROPRIEDADES = {
    # valores vêm da política de evidência da fábrica (ADR), não daqui
    "delta.logRetentionDuration": "interval 3650 days",
    "delta.deletedFileRetentionDuration": "interval 3650 days",
}


def garantir_tabela(spark, caminho: str, schema: StructType) -> str:
    if not DeltaTable.isDeltaTable(spark, caminho):
        b = DeltaTable.createIfNotExists(spark).location(caminho)
        for f in schema.fields:
            b = b.addColumn(f.name, f.dataType, nullable=f.nullable)
        b = b.partitionedBy("competencia")
        for k, v in PROPRIEDADES.items():
            b = b.property(k, v)
        b.execute()
        for nome, expr in CHECKS.items():
            spark.sql(f"ALTER TABLE delta.`{caminho}` "
                      f"ADD CONSTRAINT {nome} CHECK ({expr})")
        return "CRIADA" if conferir(spark, caminho, schema) == [] else "DIVERGE"
    return "CONFERE" if conferir(spark, caminho, schema) == [] else "DIVERGE"


def conferir(spark, caminho: str, schema: StructType) -> list[str]:
    """Compara nome, tipo e nulabilidade campo a campo, e as constraints."""
    real = DeltaTable.forPath(spark, caminho).toDF().schema
    erros = []
    esperado = {f.name: f for f in schema.fields}
    obtido = {f.name: f for f in real.fields}
    for nome in esperado.keys() | obtido.keys():
        e, o = esperado.get(nome), obtido.get(nome)
        if e is None or o is None:
            erros.append(f"{nome}: presente só em "
                         f"{'tabela' if e is None else 'contrato'}")
        elif e.dataType != o.dataType or e.nullable != o.nullable:
            erros.append(f"{nome}: contrato {e.dataType}/{e.nullable} "
                         f"≠ tabela {o.dataType}/{o.nullable}")
    props = {r["key"]: r["value"] for r in
             spark.sql(f"SHOW TBLPROPERTIES delta.`{caminho}`").collect()}
    for nome, expr in CHECKS.items():
        if f"delta.constraints.{nome.lower()}" not in props:
            erros.append(f"CHECK {nome} ausente")
    for k, v in PROPRIEDADES.items():
        if props.get(k) != v:
            erros.append(f"{k}: {props.get(k)!r} ≠ {v!r}")
    for e in erros:
        print(f"  {e}")
    return erros
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `addColumn(..., nullable=False)` | `nullable=True` | `NOT NULL` só se declara na criação — declare lá |
| `partitionedBy("competencia")` | sem partição | a unidade de regravação da fábrica |
| `delta.logRetentionDuration` | `interval 30 days` | quanto histórico sobrevive |
| `delta.deletedFileRetentionDuration` | `interval 7 days` | o que `VACUUM` pode apagar |

## Por camada

| Camada | Schema | Constraints | Observação |
|---|---|---|---|
| bronze | colunas da fonte como **string**, + metadados de ingestão (`_arquivo`, `_sha256`, `_ingerido_em`) | `NOT NULL` só nos metadados | preserva o defeito como veio |
| silver | tipos do contrato, `DecimalType` monetário | `NOT NULL` + `CHECK` medidos | o que não passa é classificado antes |
| gold | agregado com o tipo do **acumulador** declarado (ex.: `DECIMAL(24,2)`) | `NOT NULL` nas chaves e totais | lê silver por `versionAsOf` |

## Example Usage

```python
estado = garantir_tabela(spark, SILVER, schema_do_contrato(contrato))
print(f"TABELA={estado}")
if estado == "DIVERGE":
    raise SystemExit(1)   # investigar: não é para ajustar o contrato à tabela
```

## See Also

- [constraints](../concepts/constraints.md)
- [schema-enforcement](../concepts/schema-enforcement.md)
- [time-travel-retention](../concepts/time-travel-retention.md)
