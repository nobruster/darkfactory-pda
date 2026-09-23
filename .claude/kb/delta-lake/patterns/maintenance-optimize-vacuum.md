# Manutenção: OPTIMIZE e VACUUM

> **Purpose**: Compactar arquivos pequenos sem mudar o dado, e tratar `VACUUM` como destruição de evidência que só acontece por decisão registrada
> **MCP Validated**: 2026-09-23

## When to Use

- Muitos arquivos pequenos numa competência (leitura lenta, listagem cara no S3)
- **Nunca** para "consertar" uma tabela: `OPTIMIZE` não muda linha nenhuma, e se mudasse seria defeito

## Implementation

```python
"""OPTIMIZE com prova de que o conteúdo não mudou.

Token: OPTIMIZE=OK|DIVERGE|ERRO
"""
from delta.tables import DeltaTable
from pyspark.sql import functions as F


def otimizar(spark, caminho: str, competencia: str,
             zorder: list[str] | None = None) -> str:
    dt = DeltaTable.forPath(spark, caminho)
    antes = dt.history(1).select("version").first()["version"]

    b = dt.optimize().where(f"competencia = '{competencia}'")   # partição validada antes
    metricas = (b.executeZOrderBy(*zorder) if zorder else b.executeCompaction())
    metricas.show(truncate=False)

    depois = dt.history(1).select("version", "operation").first()
    if depois["version"] == antes:
        print("  nada a compactar")
        return "OK"

    ler = lambda v: (spark.read.format("delta").option("versionAsOf", v)
                     .load(caminho).filter(F.col("competencia") == competencia))
    a, d = ler(antes), ler(depois["version"])
    if a.exceptAll(d).count() or d.exceptAll(a).count():
        print(f"  conteúdo mudou entre v{antes} e v{depois['version']}")
        return "DIVERGE"
    return "OK"
```

## OPTIMIZE

| Aspecto | Comportamento |
|---|---|
| Commit | nova versão, operação `OPTIMIZE`, `dataChange=false` |
| Conteúdo | as mesmas linhas, em menos arquivos |
| Arquivos antigos | continuam no disco (marcados `remove`) — time travel intacto |
| Z-ORDER | reordena para *data skipping*; não use coluna de partição |
| API | `optimize().executeCompaction()` / `.executeZOrderBy(cols)`; SQL `OPTIMIZE delta.\`p\` [WHERE ...] [ZORDER BY (...)]` |

A reconferência acima parece redundante — e é isso que ela prova. Uma
manutenção que muda conteúdo é defeito, e só se sabe medindo.

## VACUUM

`VACUUM` apaga **fisicamente** os Parquet que nenhuma versão recente
referencia. É o que torna versões antigas ilegíveis.

| Regra | Por quê |
|---|---|
| Nunca abaixo da retenção padrão (7 dias) | leitores e escritores em curso perdem arquivos; a doc exige desligar `retentionDurationCheck` para isso — **não desligue** |
| Em tabela-evidência, nem na retenção padrão | a padrão já apaga time travel > 7 dias; a retenção vem da política de evidência (ADR) |
| `DRY RUN` primeiro, sempre | lista o que seria apagado; guarde a lista na evidência da execução |
| Nunca para "limpar" dado ruim | o dado ruim está na versão atual ou não está; `VACUUM` só apaga o passado |

```sql
-- Só com ADR que fixe a retenção, e depois do DRY RUN arquivado
VACUUM delta.`s3a://lake/silver/beneficios` DRY RUN;
```

```python
dt.vacuum()        # usa delta.deletedFileRetentionDuration da tabela
dt.vacuum(100)     # horas — abaixo da retenção da TABELA (168 h por padrão) é
                   # recusado pelo retentionDurationCheck (VacuumCommand, 3.2.1)
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `delta.deletedFileRetentionDuration` | `interval 7 days` | o que o `VACUUM` pode apagar |
| `delta.logRetentionDuration` | `interval 30 days` | histórico do log; limpo em checkpoint, **sem** `VACUUM` |
| `spark.databricks.delta.retentionDurationCheck.enabled` | `true` | recusa retenção menor que a configurada |

## Example Usage

```python
estado = otimizar(spark, SILVER, "2026-01")
print(f"OPTIMIZE={estado}")
```

## See Also

- [time-travel-retention](../concepts/time-travel-retention.md)
- [write-and-reconcile](write-and-reconcile.md)
