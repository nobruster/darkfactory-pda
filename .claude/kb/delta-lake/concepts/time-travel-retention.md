# Time Travel e Retenção

> **Purpose**: Ler versões passadas, e entender o que as apaga — porque o histórico da tabela é a prova do que foi publicado
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-23

## Overview

Time travel lê a tabela como ela estava numa versão. Para isso a doc exige:
*"you must retain **both** the log and the data files for that version."*
Dois mecanismos independentes apagam um ou outro, e nenhum deles pede
licença a quem precisa da evidência:

| O que apaga | O quê | Controlado por | Default |
|---|---|---|---|
| **`VACUUM`** | Parquet não referenciados pela versão atual, removidos há mais que a retenção | `delta.deletedFileRetentionDuration` | `interval 7 days` |
| **Limpeza do log** (automática, após checkpoint) | entradas JSON do `_delta_log` | `delta.logRetentionDuration` | `interval 30 days` |

⚠️ **O `VACUUM` com retenção padrão já destrói time travel.** Depois dele,
versões cujos arquivos foram removidos há mais de 7 dias não são mais
legíveis. "Não rodar `VACUUM` abaixo do padrão" é o piso, não a proteção.
E a limpeza do log roda **sem `VACUUM` nenhum**: com o default, o histórico
de 31 dias atrás some sozinho.

## The Pattern

```python
# Ler uma versão fixa
df_v = spark.read.format("delta").option("versionAsOf", 7).load(CAMINHO)

# Histórico = o que foi publicado, quando, por qual operação, lendo qual versão
(DeltaTable.forPath(spark, CAMINHO).history()
    .select("version", "timestamp", "operation", "operationParameters",
            "readVersion", "userMetadata", "operationMetrics")
    .orderBy("version"))

# Retenção declarada pela política de evidência da fábrica (valor vem de ADR)
spark.sql(f"""
  ALTER TABLE delta.`{CAMINHO}` SET TBLPROPERTIES (
    'delta.logRetentionDuration'         = 'interval 3650 days',
    'delta.deletedFileRetentionDuration' = 'interval 3650 days'
  )
""")
```

## Histórico como evidência (Regra 4)

O BRD do PDA nomeou o `mode("overwrite")` do legado como defeito: *"não há
como responder meses depois o que foi publicado"*. No Delta, a regravação
de uma competência com `replaceWhere` **não** destrói a anterior — a versão
antiga continua legível enquanto log e arquivos existirem. É isso que a
política de retenção precisa garantir.

| Pergunta de auditoria | Como responder |
|---|---|
| O que a gold publicou em 2026-02-05? | `history()` → versão daquela data → `versionAsOf` |
| Qual versão da silver alimentou esse total? | `userMetadata` do commit da gold ([snapshot-lineage](../patterns/snapshot-lineage.md)) |
| A competência foi regravada? Por quê? | `operationParameters.predicate` + `userMetadata` |

## Versão vs timestamp

| Opção | Use |
|---|---|
| `versionAsOf` | **sempre** que a leitura precisa ser reprodutível |
| `timestampAsOf` | só em investigação humana; o timestamp é do arquivo de log e resolve para a versão vigente naquele instante |

## Restaurar

`DeltaTable.restoreToVersion(n)` cria um commit **novo** que volta o
conteúdo — o histórico intermediário continua lá. Não é correção de dado:
se a versão atual está errada, o trabalho é investigar e classificar, e o
restore só entra com decisão registrada.

## Quick Reference

| Input | Output | Notes |
|-------|--------|-------|
| `versionAsOf` de versão já limpa | erro de arquivo/versão inexistente | a evidência se perdeu |
| `VACUUM` sem argumento | usa `deletedFileRetentionDuration` | ainda apaga histórico > 7 dias |
| `VACUUM ... RETAIN 0 HOURS` | bloqueado pelo `retentionDurationCheck` | **nunca** desligue a checagem |

## Common Mistakes

### Wrong

```python
spark.conf.set("spark.databricks.delta.retentionDurationCheck.enabled", "false")
DeltaTable.forPath(spark, p).vacuum(0)   # "liberar espaço"
```

### Correct

```python
# Sem VACUUM em tabela-evidência. Se o espaço for problema, isso é decisão
# de negócio registrada em ADR, com retenção declarada nas propriedades.
DeltaTable.forPath(spark, p).optimize().executeCompaction()   # não muda dado
```

## Related

- [transaction-log](transaction-log.md)
- [maintenance-optimize-vacuum](../patterns/maintenance-optimize-vacuum.md)
