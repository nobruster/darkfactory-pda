# Delta Lake (OSS) Quick Reference

> Fast lookup tables. For code examples, see linked files.

## Versões desta bancada (medidas)

| Peça | Versão |
|------|--------|
| Contêiner | `apache/spark:3.5.9-scala2.12-java17-python3` (Python 3.10) |
| Delta (JVM) | `io.delta:delta-spark_2.12:3.2.1` + `io.delta:delta-storage:3.2.1` |
| Delta (Python) | `pip install delta-spark==3.2.1 --no-deps` |
| S3A | `hadoop-aws` 3.3.4 (casa com o Hadoop do Spark 3.5) |

## Configuração obrigatória da sessão

| Chave | Valor |
|-------|-------|
| `spark.sql.extensions` | `io.delta.sql.DeltaSparkSessionExtension` |
| `spark.sql.catalog.spark_catalog` | `org.apache.spark.sql.delta.catalog.DeltaCatalog` |
| `spark.sql.ansi.enabled` | `true` — com `false`, estouro de decimal vira `NULL` calado |
| `spark.databricks.delta.schema.autoMerge.enabled` | `false` (default; declare mesmo assim) |
| `spark.databricks.delta.retentionDurationCheck.enabled` | `true` (default; nunca desligue) |
| `spark.databricks.delta.replaceWhere.constraintCheck.enabled` | `true` (default; nunca desligue) |

## Operações

| Quero | Faça |
|-------|------|
| Regravar uma competência | `mode("overwrite").option("replaceWhere", "competencia = '2026-01'")` |
| Acrescentar | `mode("append")` — sem `mergeSchema` |
| Ler versão fixa | `.option("versionAsOf", v).load(path)` |
| Versão atual | `DeltaTable.forPath(spark, p).history(1).select("version")` |
| Registrar linhagem | `.option("userMetadata", json.dumps({...}))` |
| Ver histórico | `DeltaTable.forPath(spark, p).history()` ou `DESCRIBE HISTORY delta.\`p\`` |
| Regra de domínio | `ALTER TABLE delta.\`p\` ADD CONSTRAINT nome CHECK (vl >= 0)` |
| Compactar | `DeltaTable.forPath(spark, p).optimize().executeCompaction()` |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| Reprocessar uma competência | `replaceWhere` (não `overwrite` puro) |
| Coluna nova no contrato | `mergeSchema` **depois** da guarda aditiva |
| Tipo de coluna mudou | recuse; é mudança de contrato, ADR novo |
| Mais de um escritor no mesmo S3 | LogStore do DynamoDB (`delta-storage-s3-dynamodb`) |
| Tabela lenta por arquivos pequenos | `OPTIMIZE` — não muda dado |
| Liberar espaço | só com retenção declarada em propriedade e ADR |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| `inferSchema` / `DoubleType` para dinheiro | `DecimalType(p, s)` do contrato |
| `mode("overwrite")` numa tabela particionada | `replaceWhere` com o predicado da competência |
| `overwriteSchema=true` "para passar" | investigar a divergência |
| Ler `load(path)` duas vezes no mesmo job | resolver a versão uma vez e usar `versionAsOf` |
| Conferir só `count()` | `exceptAll` nos dois sentidos + controles |
| `VACUUM ... RETAIN 0 HOURS` | nunca; histórico é evidência |
| `configure_spark_with_delta_pip` com `--no-deps` | `spark.jars.packages` explícito (a função importa `importlib_metadata`) |
| SQL `INSERT INTO` em camada monetária | `DataFrameWriter` + `cast` explícito |

## Related Documentation

| Topic | Path |
|-------|------|
| Getting Started | `concepts/transaction-log.md` |
| Full Index | `index.md` |
| Spec da bancada | `specs/delta-oss-env.yaml` |
