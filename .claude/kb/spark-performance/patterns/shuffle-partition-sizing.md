# Dimensionar partições de shuffle contra o spill

> **Purpose**: Escolher o número inicial de partições de shuffle pelo volume medido, deixar o AQE juntar as pequenas, e provar que o spill caiu
> **MCP Validated**: 2026-09-23 (`SQLConf.scala` v3.5.5; spill medido em `apache/spark:3.5.9`)

## When to Use

- `SPILL` em **todas** as tasks de um stage de shuffle (se for em uma só, é [skew](../concepts/skew.md))
- Muitas tasks minúsculas (ms cada) depois de um shuffle, com o AQE desligado

## As chaves (3.5)

| Chave | Default | Papel |
|---|---|---|
| `spark.sql.shuffle.partitions` | `200` | partições do shuffle; com AQE, o número **inicial** |
| `spark.sql.adaptive.coalescePartitions.initialPartitionNum` | (cai no anterior) | número inicial só para o AQE |
| `spark.sql.adaptive.coalescePartitions.enabled` | `true` | junta partições pequenas contíguas depois do shuffle |
| `spark.sql.adaptive.advisoryPartitionSizeInBytes` | `64MB` | tamanho-alvo ao juntar |
| `spark.sql.adaptive.coalescePartitions.parallelismFirst` | `true` | **ignora** o alvo de 64MB e junta pelo paralelismo do cluster |
| `spark.sql.adaptive.coalescePartitions.minPartitionSize` | `1MB` | piso ao juntar com `parallelismFirst` |
| `spark.sql.files.maxPartitionBytes` | `128MB` | tamanho das partições de **leitura** de arquivo |

⚠️ **O AQE só junta, nunca parte** (fora do skew de join). Se as partições
iniciais já são grandes demais para a memória, ele não conserta. O remédio é
subir o número inicial e deixar o AQE juntar as sobras.

⚠️ `parallelismFirst=true` é o default, e a doc do 3.5 **recomenda `false`**
para respeitar o `advisoryPartitionSizeInBytes`. Em `local[*]`, o paralelismo
é o número de núcleos, e `true` tende a gerar partições menores que 64 MB.
Mude só medindo.

## Implementation

```python
def particoes_iniciais(bytes_shuffle_medido: int,
                       alvo=64 * 1024 * 1024, piso=None, teto=4000) -> int:
    """Número inicial a partir do shuffle MEDIDO (event log), não do tamanho em disco.

    Parquet/Delta comprimido cresce várias vezes ao ser desserializado: os
    132 MB em Delta não dizem o tamanho do shuffle. Leia o shW do stage.
    """
    import math, os
    piso = piso or (os.cpu_count() or 1) * 2
    return max(piso, min(teto, math.ceil(bytes_shuffle_medido / alvo)))
```

```python
spark.conf.set("spark.sql.shuffle.partitions", str(particoes_iniciais(shW_do_stage)))
# AQE ligado: ele junta o que sobrar pequeno
```

## Por que cada peça

| Peça | Por quê |
|---|---|
| partir do `Shuffle Bytes Written` medido | tamanho em disco engana: a compressão do Parquet esconde o volume real |
| alvo de 64 MB | é o `advisoryPartitionSizeInBytes`; o AQE e você miram no mesmo número |
| piso de 2 × núcleos | manter todos os núcleos ocupados |
| teto | milhares de partições minúsculas custam agendamento e arquivos |
| `spark.conf.set` no job, não na sessão global | a mudança fica no script versionado e aparece no `EnvironmentUpdate` do log |

## Medido

Mesmo job, 3 milhões de linhas, `local[2]`:

| Configuração | Spill disco | Veredito |
|---|---|---|
| AQE ligado, 200 iniciais (default) | 0 | baseline |
| AQE desligado, 2 partições | 212 MB | `PERF=PIOR` |

O caminho inverso (sair de 2 para um número dimensionado) é o conserto: o
spill some e o resultado continua idêntico.

## Example Usage

```text
1. /spark-perf relatorio  → stage 7: SPILL em 4/4 tasks, shW 263 MB
2. particoes_iniciais(263 MB) = max(2×núcleos, 5)
3. rodar com a conf nova → /spark-perf comparar → PERF=MELHOR, controles idênticos
```

## Common Mistakes

| Don't | Do |
|---|---|
| `shuffle.partitions=2000` "por garantia" | dimensionar pelo shuffle medido |
| `repartition(n)` antes de um `groupBy` | ele acrescenta um shuffle; o `groupBy` embaralha de novo |
| desligar o AQE para "ter controle" | medir com e sem; o default é ligado por um motivo |
| subir a memória antes de olhar as partições | memória mascara, e em `local[*]` só vale no `spark-submit` |

## See Also

- [spill](../concepts/spill.md) · [shuffle](../concepts/shuffle.md)
- [delta-write-file-sizing](delta-write-file-sizing.md)
