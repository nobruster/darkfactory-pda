# Transaction Log (`_delta_log`)

> **Purpose**: Entender o que torna uma escrita Delta atômica, o que é uma versão, e o que o S3 garante (e não garante)
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-23

## Overview

Uma tabela Delta é um diretório de Parquet **mais** `_delta_log/`. Cada
escrita bem-sucedida grava um arquivo JSON numerado (`00000000000000000007.json`)
com as ações `add`/`remove` de arquivos e um `commitInfo`. A tabela na
versão *N* é exatamente o conjunto de arquivos que os commits 0..N deixaram
vivos. Parquet sem entrada no log **não faz parte da tabela** — por isso uma
escrita que falha no meio não deixa meia tabela: deixa lixo que ninguém lê.

## The Pattern

```text
s3a://lake/silver/beneficios/
├── _delta_log/
│   ├── 00000000000000000000.json   ← CREATE: schema, propriedades, constraints
│   ├── 00000000000000000001.json   ← WRITE append competencia=2026-01
│   ├── 00000000000000000002.json   ← WRITE overwrite replaceWhere 2026-01
│   └── 00000000000000000010.checkpoint.parquet
└── competencia=2026-01/part-....snappy.parquet
```

```python
from delta.tables import DeltaTable

dt = DeltaTable.forPath(spark, CAMINHO)
ultimo = dt.history(1).select(
    "version", "operation", "operationParameters", "readVersion", "userMetadata"
).first()
# version=2 operation=WRITE operationParameters={mode: Overwrite,
#   predicate: ["(competencia = '2026-01')"]} readVersion=1
```

## Snapshot e isolamento

| Conceito | O que significa |
|---|---|
| Versão | inteiro monotônico; o commit *N+1* só existe se *N* existe |
| Snapshot | a tabela vista numa versão; imutável |
| `readVersion` | a versão que a transação leu antes de commitar (no `commitInfo`) |
| Isolamento | escrita serializável; leitura vê um snapshot, nunca commit parcial |

⚠️ `spark.read.format("delta").load(p)` resolve **a versão mais recente no
momento em que a consulta é analisada**. Dois `load(p)` no mesmo job podem
ver versões diferentes se alguém commitou no meio. Para ler consistente,
resolva a versão uma vez e passe `versionAsOf` — ver
[snapshot-lineage](../patterns/snapshot-lineage.md).

## LogStore no S3 (MinIO)

O commit atômico depende de "gravar o arquivo *N* só se ele não existe". O
S3 (e o MinIO pelo `s3a://`) não oferece essa exclusão mútua entre processos.

| Modo | Quando serve | Configuração |
|---|---|---|
| **Single-driver** (default para `s3a://`) | **um único** driver escreve na tabela | nenhuma; é o LogStore padrão do esquema `s3a` |
| **Multi-cluster** (experimental) | mais de um driver escreve na mesma tabela | `io.delta:delta-storage-s3-dynamodb:3.2.1` + `spark.delta.logStore.s3a.impl=io.delta.storage.S3DynamoDBLogStore` + `spark.io.delta.storage.S3DynamoDBLogStore.ddb.tableName` / `.ddb.region` |

A documentação oficial é taxativa: *"Concurrent writes to the same Delta
table on S3 storage from multiple Spark drivers can lead to data loss."*

Nesta bancada há **um escritor**, então o single-driver é aceitável. Isso é
uma **premissa**, não uma propriedade do sistema: se um segundo job passar a
escrever na mesma tabela, a premissa quebra em silêncio. Registre-a no ADR
da fábrica e, no multi-cluster, **todos** os escritores precisam usar o
mesmo LogStore e a mesma tabela DynamoDB.

Leitores concorrentes são seguros em qualquer modo.

## Quick Reference

| Input | Output | Notes |
|-------|--------|-------|
| `dt.history(1)` | última versão + `commitInfo` | inclui `userMetadata`, `operationMetrics` |
| `DESCRIBE DETAIL delta.\`p\`` | propriedades, nº de arquivos | constraints aparecem como propriedades |
| Parquet sem entrada no log | ignorado | não apague à mão; `VACUUM` decide |

## Common Mistakes

### Wrong

```python
# duas leituras "da mesma tabela" — podem ser versões diferentes
total = spark.read.format("delta").load(p).agg(F.sum("vl")).first()[0]
linhas = spark.read.format("delta").load(p).count()
```

### Correct

```python
v = DeltaTable.forPath(spark, p).history(1).select("version").first()[0]
df = spark.read.format("delta").option("versionAsOf", v).load(p)
```

## Related

- [time-travel-retention](time-travel-retention.md)
- [snapshot-lineage](../patterns/snapshot-lineage.md)
