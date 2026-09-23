# Mitigar skew sem mudar o resultado

> **Purpose**: Tratar skew medido: deixar o AQE agir no join, salgar a agregação quando não há parcial, e provar que o total em Decimal não mudou
> **MCP Validated**: 2026-09-23 (`SQLConf.scala` v3.5.5)

## When to Use

- O relatório do `/spark-perf` mostra `SKEW` num stage que **pesa** no tempo total
- Não use por suspeita: sem `skew_tempo` alto e `skew_bytes` alto, não é skew de dado

## Passo 1: é join? Deixe o AQE trabalhar

```python
spark.conf.get("spark.sql.adaptive.enabled")                      # 'true'
spark.conf.get("spark.sql.adaptive.skewJoin.enabled")             # 'true'
```

O AQE parte a partição enviesada de um join sort-merge ou shuffled hash
quando ela é > `skewedPartitionFactor` (5.0) × mediana **e** >
`skewedPartitionThresholdInBytes` (256MB). Abaixo de 256 MB, ele não age. Baixar
o piso é uma otimização como qualquer outra: mede-se.

Se um lado é pequeno (dimensão), **broadcast** elimina o shuffle e o skew
junto:

```python
fato.join(F.broadcast(especies), "especie_codigo")
```

## Passo 2: é agregação sem parcial? Salgue em duas fases

`sum`, `count`, `min` e `max` já agregam no mapa, e o skew raramente dói. O
salting serve para `collect_list`, `countDistinct` em alta cardinalidade e UDAF.

```python
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

N_SAL = 16                                            # medido, não chutado
TIPO_ACUM = DecimalType(24, 2)                        # do contrato (ADR), não inferido

CHAVE_LINHA = ["nb", "competencia", "especie"]        # colunas que identificam a linha
fase1 = (df.withColumn("_sal", F.pmod(F.xxhash64(*CHAVE_LINHA), F.lit(N_SAL)))  # 0..N-1
           .groupBy("especie", "_sal")
           .agg(F.sum("vl").cast(TIPO_ACUM).alias("parcial")))
fase2 = (fase1.groupBy("especie")
              .agg(F.sum("parcial").cast(TIPO_ACUM).alias("vl_total")))
```

| Peça | Por quê |
|---|---|
| sal por **hash** da linha (`pmod`: `xxhash64` pode ser negativo), não `rand()` | `rand()` torna o plano não determinístico: retry de task muda a partição de destino |
| `cast(TIPO_ACUM)` nas duas fases | `sum` de `decimal(24,2)` promove para `decimal(34,2)`; o tipo do total **mudaria** em relação ao job antigo |
| mesmo `TIPO_ACUM` do job sem sal | o schema da saída não muda; a reconferência compara nome **e** tipo |

A soma de Decimal em duas fases é **exata** (sem arredondamento no meio)
enquanto o acumulador não estoura. Com `spark.sql.ansi.enabled=true`, estouro
levanta exceção em vez de virar `NULL` (Regra 5). O `cast` para um tipo
**menor** que o necessário é exatamente o estouro que o ANSI pega.

## Passo 3: provar

```text
/spark-perf comparar  →  controles idênticos, multiconjunto 0/0, PERF=MELHOR
```

O `skew_tempo` do stage deve cair **e** o tempo de executor total não pode
subir. Salting acrescenta um shuffle; em dado pequeno, ele custa mais do que
economiza.

## Quando NÃO salgar

| Situação | Faça |
|---|---|
| skew abaixo de 2 % do tempo do job | nada |
| agregação com parcial (`sum`/`count`) | procure o skew noutro stage |
| a chave pesada é **defeito da fonte** (código nulo, `"0000"`) | classifique (Regra 4); não dilua o defeito com sal |
| dados de 132 MB em `local[*]` | meça: a sobrecarga do segundo shuffle pode dominar |

## Example Usage

```bash
python3 .claude/skills/spark-perf/medir_eventlog.py comparar \
  /app/trabalho/eventlog/<run_com_sal> --resultado resultado.json \
  --baseline perf/baseline-silver.json
# PERF=MELHOR|IGUAL → a mudança pode entrar; PIOR|NAO_MEDIDO → reverter
```

## See Also

- [skew](../concepts/skew.md)
- [measure-before-after](measure-before-after.md)
