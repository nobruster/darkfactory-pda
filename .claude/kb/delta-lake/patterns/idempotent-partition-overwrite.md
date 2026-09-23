# Regravar uma competência, idempotente

> **Purpose**: Reprocessar uma competência inteira num commit atômico, sem tocar nas outras, e com o mesmo resultado não importa quantas vezes rode
> **MCP Validated**: 2026-09-23

## When to Use

- Reprocessar uma competência (fonte reenviada, correção de código, re-execução)
- Qualquer gravação de silver/gold particionada por competência
- No lugar de `mode("overwrite")` puro, que apaga **todas** as partições

## Implementation

```python
"""Regrava UMA competência com replaceWhere.

Token: GRAVACAO=OK|RECUSADO|ERRO
"""
import json
import re

from pyspark.sql import functions as F

_COMPETENCIA = re.compile(r"^\d{4}-\d{2}$")


def regravar_competencia(df, caminho: str, competencia: str,
                         linhagem: dict) -> str:
    # O predicado é montado de um valor VALIDADO — nada de string livre em SQL
    if not _COMPETENCIA.match(competencia):
        print(f"  competencia inválida: {competencia!r}")
        return "RECUSADO"

    # Toda linha tem de pertencer à competência. O constraintCheck do Delta
    # também recusaria; conferir antes dá a mensagem certa, e conta.
    fora = df.filter(F.col("competencia") != F.lit(competencia)).count()
    if fora:
        print(f"  {fora} linhas fora da competência {competencia}")
        return "RECUSADO"

    n = df.count()
    if n == 0:                       # Regra 9: gravar vazio apagaria a partição
        print("  zero linhas — regravar apagaria a competência")
        return "RECUSADO"

    (df.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"competencia = '{competencia}'")
        .option("userMetadata", json.dumps(linhagem, sort_keys=True))
        .save(caminho))
    return "OK"
```

## Por que é idempotente

| Execução | Efeito |
|---|---|
| 1ª | versão *N+1*: remove os arquivos da competência, adiciona os novos |
| 2ª, mesmo dado | versão *N+2*: mesmo conteúdo; a *N+1* continua no histórico |
| outras competências | intocadas — os arquivos delas não aparecem em `remove` |
| falha no meio | nenhum commit; a tabela continua na versão *N* |

O **conteúdo** é idempotente; o **histórico** não — cada execução é uma
versão nova. É o que se quer: a re-execução fica registrada.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `replaceWhere` | — | predicado; desde o Delta 1.1 aceita coluna qualquer, não só partição |
| `spark.databricks.delta.replaceWhere.constraintCheck.enabled` | `true` | recusa escrita com linha fora do predicado. **Nunca desligue**: com `false`, a linha fora é gravada e só o que casa é substituído |
| `partitionOverwriteMode=dynamic` | — | alternativa que substitui as partições presentes no DataFrame. **Não use aqui**: a partição apagada é decidida pelo dado, não declarada. Se ambos vierem, `replaceWhere` prevalece |

⚠️ **O `DataFrame` vazio é o caso perigoso.** Um `replaceWhere` com zero
linhas é um commit válido que **apaga a competência** — sem erro nenhum. A
guarda de zero linhas acima não é otimização; é a Regra 9.

⚠️ Com a tabela particionada por `competencia`, o `replaceWhere` nela só
remove arquivos inteiros. Com predicado em coluna não particionada, o Delta
reescreve os arquivos que contêm linhas das duas bandas — funciona, mas
custa mais.

## Example Usage

```python
estado = regravar_competencia(
    silver_df, SILVER, "2026-01",
    linhagem={"run_id": run_id, "camada": "silver",
              "fonte": BRONZE, "fonte_versao": v_bronze},
)
print(f"GRAVACAO={estado}")
# em seguida: write-and-reconcile.md — gravar não é prova de ter gravado certo
```

## Common Mistakes

| Don't | Do |
|---|---|
| `mode("overwrite").save(p)` numa tabela com várias competências | `replaceWhere` com a competência |
| `DELETE` + `append` em dois commits | um `replaceWhere` — um commit só |
| predicado montado de entrada sem validar | regex na competência antes |
| `overwriteSchema=true` junto, "para garantir" | schema é do contrato; ver [schema-enforcement](../concepts/schema-enforcement.md) |

## See Also

- [write-and-reconcile](write-and-reconcile.md)
- [snapshot-lineage](snapshot-lineage.md)
- [transaction-log](../concepts/transaction-log.md)
