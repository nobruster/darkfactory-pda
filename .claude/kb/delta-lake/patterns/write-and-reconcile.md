# Gravar e reconferir o que foi gravado

> **Purpose**: Depois do commit, reler a versão commitada e provar que ela contém exatamente as linhas julgadas — multiconjunto e controles, não só contagem
> **MCP Validated**: 2026-09-23

## When to Use

- Toda gravação de silver e gold, sem exceção
- Antes de publicar qualquer veredito que cite o lago
- Quando "a escrita não deu erro" estiver sendo usada como prova

## Implementation

```python
"""Relê a versão commitada e compara com o que foi julgado.

Token: RECONFERENCIA=CONFERE|DIVERGE|NAO_MEDIDO|ERRO
"""
from pyspark.sql import functions as F

COLUNAS = ["competencia", "especie_codigo", "especie_descricao", "vl_liquido"]


def controles(df, valor: str = "vl_liquido") -> dict:
    """A MESMA função mede o julgado e o relido — senão a comparação não prova nada."""
    a = df.agg(
        F.count(F.lit(1)).alias("linhas"),
        F.sum(F.when(F.col(valor).isNull(), 1).otherwise(0)).alias("nulos"),
        F.sum(valor).alias("soma"),
        F.min(valor).alias("minimo"),
        F.max(valor).alias("maximo"),
    ).first()
    return {k: (None if a[k] is None else str(a[k])) for k in a.asDict()}


def reconferir(spark, julgado, caminho: str, versao: int,
               competencia: str) -> str:
    relido = (spark.read.format("delta").option("versionAsOf", versao)
              .load(caminho)
              .filter(F.col("competencia") == competencia)
              .select(*COLUNAS))
    julgado = julgado.select(*COLUNAS)

    # Nome e tipo. NÃO a nulabilidade: a tabela declara NOT NULL e o
    # DataFrame julgado quase sempre vem nullable=True — compará-la
    # acusaria divergência em toda gravação correta.
    tipos_j = [(f.name, f.dataType) for f in julgado.schema.fields]
    tipos_r = [(f.name, f.dataType) for f in relido.schema.fields]
    if tipos_j != tipos_r:
        print(f"  schema: julgado {julgado.schema.simpleString()}")
        print(f"          relido  {relido.schema.simpleString()}")
        return "DIVERGE"

    c_j, c_r = controles(julgado), controles(relido)

    # Regra 9: ler zero linhas não é conferir. Nem do lado julgado.
    if int(c_j["linhas"]) == 0 or int(c_r["linhas"]) == 0:
        print(f"  linhas: julgado={c_j['linhas']} relido={c_r['linhas']}")
        return "NAO_MEDIDO"

    # Multiconjunto: exceptAll preserva duplicatas. subtract() não.
    so_julgado = julgado.exceptAll(relido).count()
    so_relido = relido.exceptAll(julgado).count()

    divergencias = {k: (c_j[k], c_r[k]) for k in c_j if c_j[k] != c_r[k]}
    for k, (a, b) in divergencias.items():
        print(f"  {k}: julgado={a} relido={b}")
    print(f"  só no julgado: {so_julgado}   só no lago: {so_relido}")

    if so_julgado or so_relido or divergencias:
        return "DIVERGE"
    return "CONFERE"
```

## Por que cada peça

| Peça | O que pega que as outras não pegam |
|---|---|
| `schema` igual | cast implícito, precisão diferente, coluna trocada de lugar |
| `exceptAll` julgado → lago | linha que não foi gravada |
| `exceptAll` lago → julgado | linha que apareceu (duplicada, de outra competência, de outra execução) |
| `exceptAll` e não `subtract` | `subtract` é conjunto: uma linha duplicada passaria |
| controles (soma, min, max, nulos) | redundantes com o multiconjunto **se** ele estiver certo — e são o que o veredito publica |
| filtro por `competencia` | medir a tabela inteira mede a união das partições (Regra 11) |
| `versionAsOf` do **seu** commit | reler a "última" pode ler o commit de outro |

⚠️ `str(Decimal)` nos controles: a comparação é exata, sem float no meio. Se
um lado vier `DecimalType(24,2)` e o outro `(14,2)`, o `str` coincide e o
`schema` acusa — por isso a checagem de schema vem antes.

⚠️ `exceptAll` custa um shuffle da competência inteira, duas vezes. Em
dezenas de milhões de linhas é minutos, não horas; faça `cache()` do
julgado **antes** de gravar, para não recalcular a fonte.

## Example Usage

```python
julgado = silver_df.cache()
julgado.count()                                   # materializa antes da escrita
meta = linhagem("silver", BRONZE, v_bronze, competencia=comp)
if regravar_competencia(julgado, SILVER, comp, meta) != "OK":
    print("RECONFERENCIA=ERRO"); raise SystemExit(1)
v = versao_do_meu_commit(spark, SILVER, meta)
estado = reconferir(spark, julgado, SILVER, v, comp)
print(f"RECONFERENCIA={estado}")
raise SystemExit(0 if estado == "CONFERE" else 1)
```

## Common Mistakes

| Don't | Do |
|---|---|
| `assert df.count() == lago.count()` | multiconjunto + controles |
| reler com `load(p)` sem versão | `versionAsOf` do commit encontrado pelo `run_id` |
| `NAO_MEDIDO` tratado como sucesso no chamador | sair com código ≠ 0 |
| reconferir contra a fonte **re-lida** depois da escrita | contra o DataFrame julgado em cache — é ele que o gate aprovou |

## See Also

- [snapshot-lineage](snapshot-lineage.md)
- [idempotent-partition-overwrite](idempotent-partition-overwrite.md)
- [one-pass-reconciliation](../../spark-performance/patterns/one-pass-reconciliation.md): os dois `exceptAll` numa agregação só, com a mesma prova e metade do shuffle
- AGENTS.md, Regras 9 e 11
