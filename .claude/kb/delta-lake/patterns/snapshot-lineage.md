# Snapshot resolvido uma vez + linhagem no commit

> **Purpose**: A camada consumidora lê uma versão fixa da camada anterior e grava, no próprio commit, qual versão leu
> **MCP Validated**: 2026-09-23

## When to Use

- Silver lendo bronze, gold lendo silver
- Qualquer job que lê a mesma tabela mais de uma vez (controles + transformação)
- Quando alguém vai perguntar, meses depois, "esse total veio de qual dado?"

## Implementation

```python
"""Resolve o snapshot, lê por versionAsOf, e grava a linhagem no userMetadata.

Token: LINHAGEM=OK|DIVERGE|ERRO
"""
import json
import uuid

from delta.tables import DeltaTable


def resolver_versao(spark, caminho: str) -> int:
    """UMA chamada por job. Todo o resto usa o número devolvido."""
    linha = DeltaTable.forPath(spark, caminho).history(1).select("version").first()
    if linha is None:
        raise RuntimeError(f"{caminho}: tabela sem histórico")
    return int(linha["version"])


def ler_snapshot(spark, caminho: str, versao: int):
    return spark.read.format("delta").option("versionAsOf", versao).load(caminho)


def linhagem(camada: str, fonte: str, fonte_versao: int, **extra) -> dict:
    return {"run_id": str(uuid.uuid4()), "camada": camada,
            "fonte": fonte, "fonte_versao": fonte_versao, **extra}


def versao_do_meu_commit(spark, caminho: str, meta: dict) -> int:
    """Acha o commit pelo run_id, em vez de supor que é o último.

    Com um único escritor o último É o seu — mas conferir custa uma linha e
    transforma a premissa em fato medido. Não achar é ERRO, não sucesso.
    """
    hist = (DeltaTable.forPath(spark, caminho).history(20)
            .select("version", "userMetadata").collect())
    for h in hist:
        try:
            um = json.loads(h["userMetadata"] or "{}")
        except json.JSONDecodeError:
            continue                  # commit de outra origem; não é o nosso
        if isinstance(um, dict) and um.get("run_id") == meta["run_id"]:
            return int(h["version"])
    raise RuntimeError(f"commit com run_id={meta['run_id']} não encontrado")
```

## Fluxo silver → gold

```python
from pyspark.sql import functions as F

v_silver = resolver_versao(spark, SILVER)                 # 1 vez
silver = ler_snapshot(spark, SILVER, v_silver).filter(
    F.col("competencia") == competencia).cache()

meta = linhagem("gold", SILVER, v_silver, competencia=competencia,
                contrato_sha256=sha_contrato)
gold = agregar(silver)                                     # controles e agregação
regravar_competencia(gold, GOLD, competencia, meta)        # userMetadata = meta
v_gold = versao_do_meu_commit(spark, GOLD, meta)
print(f"  gold v{v_gold} ← silver v{v_silver}")
```

## O que fica registrado

| Campo do `history()` | Conteúdo |
|---|---|
| `version` | a versão que a gold publicou |
| `readVersion` | a versão **da gold** que o commit leu (não é a silver) |
| `userMetadata` | `{"run_id", "camada", "fonte", "fonte_versao", ...}` — **a silver** |
| `operationParameters.predicate` | a competência regravada |
| `operationMetrics` | `numOutputRows`, `numAddedFiles`, `numRemovedFiles` |

⚠️ `readVersion` **não** é linhagem entre tabelas — é a versão da própria
tabela de destino. A linhagem entre camadas só existe se você a gravar no
`userMetadata`.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `.option("userMetadata", s)` | — | por escrita; tem precedência sobre a config de sessão |
| `spark.databricks.delta.commitInfo.userMetadata` | — | por sessão. **Evite**: vaza para todo commit seguinte da sessão |
| `versionAsOf` | última | inteiro; reprodutível |

## Common Mistakes

| Don't | Do |
|---|---|
| `load(SILVER)` para controles e de novo para agregar | uma versão, `cache()` do recorte |
| supor que `history(1)` depois da escrita é o seu commit | procurar pelo `run_id` |
| linhagem num JSON de evidência separado, só | no commit — o JSON pode se perder; o log vai junto com a tabela |
| `timestampAsOf` em pipeline | `versionAsOf` |

## See Also

- [transaction-log](../concepts/transaction-log.md)
- [idempotent-partition-overwrite](idempotent-partition-overwrite.md)
- [write-and-reconcile](write-and-reconcile.md)
