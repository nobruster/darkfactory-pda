# Tamanho de arquivo na escrita Delta

> **Purpose**: Evitar arquivos pequenos (e gigantes) na gravação de uma competência, medir quantos arquivos saíram, e saber quando compactar depois
> **MCP Validated**: 2026-09-23 (`DeltaOperations.scala`, `DeltaOptions.scala`, `TransactionalWrite.scala` e `DeltaSQLConf.scala` na tag `v3.2.1`)

## When to Use

- A competência gravada tem centenas de arquivos de poucos MB (listagem lenta no S3, leitura lenta)
- Depois de mudar `shuffle.partitions`: **o número de arquivos gravados segue as partições do último stage**

A doutrina de gravação é do [`kb/delta-lake`](../../delta-lake/index.md):
`replaceWhere`, `userMetadata`, reconferência. Aqui entra só o **tamanho**.

## Medir antes de mexer

As métricas de uma escrita `WRITE` no Delta 3.2.1 (`DeltaOperationMetrics.WRITE`):

| Métrica (`operationMetrics`) | Significado |
|---|---|
| `numFiles` | arquivos gravados |
| `numOutputBytes` | bytes gravados |
| `numOutputRows` | linhas gravadas |

Com `replaceWhere`, entram também as métricas da remoção (`numRemovedFiles`
e afins), governadas por
`spark.databricks.delta.replaceWhere.dataColumns.metrics.enabled` (interna,
default `true`). A doc dela avisa que tabela particionada ou sem estatísticas
**não** reporta métricas por linha. Conte arquivos e bytes, não linhas.

```python
from delta.tables import DeltaTable

ultima = (DeltaTable.forPath(spark, SILVER).history(1)
          .select("version", "operation", "operationMetrics").first())
m = ultima["operationMetrics"]
media_mb = int(m["numOutputBytes"]) / max(1, int(m["numFiles"])) / 1048576
print(f"v{ultima['version']} {ultima['operation']}: {m['numFiles']} arquivos, "
      f"{media_mb:.1f} MB em média")

det = DeltaTable.forPath(spark, SILVER).detail().select("numFiles", "sizeInBytes").first()
```

## Implementation

```python
def gravar_competencia_dimensionada(julgado, caminho, competencia, meta,
                                    bytes_competencia_medidos: int,
                                    alvo_mb=128, linhas_por_arquivo=None):
    """repartition antes do write: controla quantos arquivos a competência vira.

    bytes_competencia_medidos vem do numOutputBytes da gravação ANTERIOR da
    mesma competência (history), não de um palpite. Primeira gravação: sem
    repartition, meça, e dimensione na próxima.
    """
    n = max(1, round(bytes_competencia_medidos / (alvo_mb * 1048576)))
    w = (julgado.repartition(n)                 # 1 shuffle a mais, arquivos previsíveis
         .write.format("delta").mode("overwrite")
         .option("replaceWhere", f"competencia = '{competencia}'")
         .option("userMetadata", meta))
    if linhas_por_arquivo:
        w = w.option("maxRecordsPerFile", linhas_por_arquivo)   # teto, não alvo
    w.save(caminho)
```

| Escolha | Efeito | Custo |
|---|---|---|
| `repartition(n)` | exatamente `n` arquivos (por partição de tabela) | um shuffle da competência |
| `coalesce(n)` | `n` arquivos sem shuffle | **reduz o paralelismo do stage inteiro** de cálculo acima dele |
| `repartition("competencia")` | 1 arquivo por competência | uma task grava tudo: skew proposital |
| `maxRecordsPerFile` | parte arquivos acima de N linhas | não junta os pequenos |

A opção `maxRecordsPerFile` **por escrita** é repassada pelo Delta 3.2.1 ao
gravador (`TransactionalWrite` filtra e mantém só ela e `compression`). A
leitura da conf de sessão `spark.sql.files.maxRecordsPerFile` (default `0`,
sem limite) pelo caminho do Delta é **hipótese não conferida**. Use a opção.

⚠️ **`repartition` antes do write muda a ordem das linhas nos arquivos, não
o conteúdo.** A reconferência por multiconjunto é indiferente à ordem, e é por
isso que ela é a prova, não um `diff` de arquivos.

## Compactar depois: `OPTIMIZE`

Para uma competência já gravada em muitos arquivos, use o `OPTIMIZE` com
reconferência de conteúdo de
[`maintenance-optimize-vacuum`](../../delta-lake/patterns/maintenance-optimize-vacuum.md).
As métricas dele (`DeltaOperationMetrics.OPTIMIZE`) trazem `numAddedFiles`,
`numRemovedFiles`, `minFileSize`, `p50FileSize` e `maxFileSize`. Registre-as
na evidência.

| Conf (Delta 3.2.1) | Default | Nota |
|---|---|---|
| `spark.databricks.delta.optimize.maxFileSize` | 1 GB | alvo do `OPTIMIZE`; interna |
| `spark.databricks.delta.optimize.minFileSize` | 1 GB | arquivos menores que isto são candidatos |
| `spark.databricks.delta.optimizeWrite.enabled` | (não definida) | existe no OSS 3.2.1; comportamento **não medido** nesta bancada |
| `spark.databricks.delta.autoCompact.enabled` | (não definida) | idem; ligar muda o que cada commit faz. Só com ADR |

⚠️ **`OPTIMIZE` sim; `VACUUM` nunca como otimização.** Os arquivos antigos que
o `OPTIMIZE` marca como removidos continuam no disco e sustentam o time travel,
que é evidência (Regra 4). Liberar espaço é decisão de retenção, com ADR, e não
de performance.

## Common Mistakes

| Don't | Do |
|---|---|
| `coalesce(1)` para "um arquivo bonito" | um núcleo processa a competência inteira |
| `VACUUM` depois do `OPTIMIZE` para "terminar a limpeza" | nunca como otimização (ver acima) |
| `overwriteSchema` para regravar "mais rápido" | proibido sem ADR; troca o contrato em silêncio |
| medir arquivos contando `ls` no bucket | `operationMetrics` da versão, ou `detail()` |

## See Also

- [maintenance-optimize-vacuum](../../delta-lake/patterns/maintenance-optimize-vacuum.md)
- [shuffle-partition-sizing](shuffle-partition-sizing.md)
