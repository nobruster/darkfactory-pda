# Sessão Spark + Delta 3.2.1 + MinIO

> **Purpose**: Subir uma `SparkSession` que lê e grava Delta em `s3a://` no MinIO, com tudo que governa dinheiro e retenção **declarado**, não herdado
> **MCP Validated**: 2026-09-23

## When to Use

- Todo script que grava ou lê camada de medalhão em Delta
- Testes de integração no contêiner `apache/spark:3.5.9-scala2.12-java17-python3`
- Antes de copiar uma sessão de outro repositório: compare com esta

## Implementation

```python
"""Sessão Delta OSS. O que você não declara, você herda — também na JVM."""
import os

from pyspark.sql import SparkSession

DELTA_JARS = "io.delta:delta-spark_2.12:3.2.1,io.delta:delta-storage:3.2.1"

# Chaves cujo valor esta bancada NÃO aceita herdar.
DECLARADAS = {
    # Delta
    "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
    "spark.sql.catalog.spark_catalog":
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    # Regra 5: com false, estouro de decimal vira NULL sem erro
    "spark.sql.ansi.enabled": "true",
    # Evolução de schema só por escrita, depois da guarda aditiva
    "spark.databricks.delta.schema.autoMerge.enabled": "false",
    # Cercas do Delta que existem por padrão — declaradas para não herdar um false
    "spark.databricks.delta.retentionDurationCheck.enabled": "true",
    "spark.databricks.delta.replaceWhere.constraintCheck.enabled": "true",
    # MinIO
    "spark.hadoop.fs.s3a.path.style.access": "true",
    "spark.hadoop.fs.s3a.connection.ssl.enabled": "false",
    "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
    "spark.hadoop.fs.s3a.aws.credentials.provider":
        "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
}


def sessao_delta(nome: str, baixar_jars: bool = True) -> SparkSession:
    b = SparkSession.builder.appName(nome)
    if baixar_jars:   # False quando os jars já estão em /opt/spark/jars
        b = b.config("spark.jars.packages", DELTA_JARS)
    for chave, valor in DECLARADAS.items():
        b = b.config(chave, valor)
    b = (b.config("spark.hadoop.fs.s3a.endpoint", os.environ["S3_ENDPOINT"])
          .config("spark.hadoop.fs.s3a.access.key", os.environ["S3_ACCESS_KEY"])
          .config("spark.hadoop.fs.s3a.secret.key", os.environ["S3_SECRET_KEY"]))
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    conferir_sessao(spark)
    return spark


def conferir_sessao(spark: SparkSession) -> None:
    """getOrCreate() devolve a sessão EXISTENTE se houver — e ignora as
    configs estáticas pedidas. Confira o que ficou, não o que foi pedido."""
    divergentes = {
        k: spark.conf.get(k, None)
        for k, v in DECLARADAS.items()
        if not k.startswith("spark.hadoop.")
        and (spark.conf.get(k, None) or "").lower() != v.lower()
    }
    if divergentes:
        raise RuntimeError(f"sessão Delta divergente do declarado: {divergentes}")
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `spark.jars.packages` | — | baixa `delta-spark` + `delta-storage` do Maven na 1ª sessão |
| `spark.sql.ansi.enabled` | `false` no Spark 3.5 | **declare `true`** |
| `spark.databricks.delta.schema.autoMerge.enabled` | `false` | mantenha `false` |
| `spark.databricks.delta.retentionDurationCheck.enabled` | `true` | nunca `false` |
| `spark.databricks.delta.replaceWhere.constraintCheck.enabled` | `true` | nunca `false` |
| `spark.hadoop.fs.s3a.path.style.access` | `false` | MinIO precisa `true` |
| `spark.hadoop.fs.s3a.connection.ssl.enabled` | `true` | MinIO local sem TLS: `false` |

## Instalação no contêiner

```bash
# Python: só a API; o pyspark 3.5.9 do contêiner fica como está
pip install delta-spark==3.2.1 --no-deps

# JVM, offline (alternativa ao spark.jars.packages): os dois jars em /opt/spark/jars
#   delta-spark_2.12-3.2.1.jar   delta-storage-3.2.1.jar
# e chame sessao_delta(nome, baixar_jars=False)
```

⚠️ **Não use `configure_spark_with_delta_pip`** com `--no-deps`. Em 3.2.1 a
função faz `import importlib_metadata` (dependência declarada do
`delta-spark` para Python) e falha sem ela. Declarar `spark.jars.packages`
direto é equivalente e explícito.

⚠️ `hadoop-aws` precisa casar com o Hadoop do Spark (3.3.4 no Spark 3.5).
Versão diferente dá `NoSuchMethodError` no primeiro acesso a `s3a://`.

⚠️ Um único escritor por tabela: o LogStore padrão de `s3a://` é
single-driver. Ver [transaction-log](../concepts/transaction-log.md).

## Example Usage

```python
spark = sessao_delta("silver-beneficios-2026-01")
try:
    df = spark.read.format("delta").option("versionAsOf", v).load(BRONZE)
    ...
finally:
    spark.stop()
```

## See Also

- [contract-table-bootstrap](contract-table-bootstrap.md)
- [schema-enforcement](../concepts/schema-enforcement.md)
- Desempenho do Spark: agente `spark-specialist` (não há KB `spark/` nesta bancada)
