# Spill: quando a partição não cabe na memória de execução

> **Purpose**: Ler `Memory Bytes Spilled` e `Disk Bytes Spilled`, entender de onde o spill vem e por que "mais memória" costuma ser a resposta errada
> **Confidence**: 0.90
> **MCP Validated**: 2026-09-23 (`docs/web-ui.md`, `docs/monitoring.md`, `config/package.scala` e `SQLConf.scala` na tag `v3.5.5`; spill medido em `apache/spark:3.5.9`)

## Overview

Sort, agregação por hash e join precisam segurar a partição inteira na
memória de execução. Quando ela não cabe, o operador **derrama** para o disco,
serializado, e relê depois. O resultado continua correto; o job fica mais
lento, e o disco local enche.

## As duas métricas

| Campo (event log) | O que mede (doc da Web UI) |
|---|---|
| `Memory Bytes Spilled` | tamanho **desserializado** do dado derramado, como estava em memória |
| `Disk Bytes Spilled` | tamanho **serializado** do mesmo dado, gravado em disco |

É o mesmo dado contado de dois jeitos, então **não some os dois**. O
`Disk Bytes Spilled` é o que custa I/O; o de memória costuma ser maior.
Qualquer `Disk Bytes Spilled > 0` é sinal, e o gate de referência trata spill
em disco que **aparece** (0 → > 0) como `PIOR`.

## Medido

O mesmo job (3 milhões de linhas, `orderBy` + `groupBy` + `exceptAll`), em
`local[2]` com 1 CPU e 1 GB de driver:

| Configuração | Spill memória / disco | Shuffle R/W |
|---|---|---|
| defaults (AQE ligado, 200 partições iniciais) | 0 / 0 MB | 270 / 270 MB |
| AQE desligado, `shuffle.partitions=2` | **272 / 212 MB** | 263 / 263 MB |

O shuffle quase não muda. O que mudou foi o **tamanho de cada partição**.

## Causas, em ordem de frequência

| Causa | Como aparece | Resposta |
|---|---|---|
| poucas partições de shuffle para o volume | spill em todas as tasks do stage | mais partições (ver [shuffle-partition-sizing](../patterns/shuffle-partition-sizing.md)) |
| skew | spill em **uma** task | [skew-mitigation](../patterns/skew-mitigation.md) |
| agregação larga (muitas colunas ou chaves, `collect_list`) | spill no stage do `groupBy` | reduzir colunas **antes** do shuffle |
| `cache()` ocupando memória unificada | spill aparece depois do `cache` | `unpersist()` quando o cache deixa de servir |
| linhas largas (strings longas, colunas não usadas) | bytes por registro alto | `select` só do que o stage precisa |

## Memória unificada (3.5)

| Chave | Default | Papel |
|---|---|---|
| `spark.memory.fraction` | `0.6` | fração do heap (menos 300 MB) para execução + armazenamento |
| `spark.memory.storageFraction` | `0.5` | parte dessa fração **protegida** do despejo para o cache |

Execução pode tomar memória do armazenamento, mas não abaixo do
`storageFraction`. Um `cache()` grande que ninguém libera reduz a memória de
sort e agregação do resto do job.

⚠️ **AQE não parte uma partição grande de agregação.** Ele só **junta**
partições pequenas (coalesce) e só parte skew de join. Se as 200 partições
iniciais são grandes demais, o AQE não conserta: o número inicial precisa
subir.

## Quando é o ambiente

Em `local[*]`, driver e executor são a mesma JVM. `spark.driver.memory` só
vale se passado **antes** da JVM subir (`spark-submit --driver-memory` ou
`spark-defaults.conf`). Setar no `builder.config` de um `getOrCreate` já
rodando não tem efeito. Confira o valor efetivo no `EnvironmentUpdate` do log.

## Common Mistakes

### Wrong

```python
.config("spark.driver.memory", "8g")    # dentro do script, depois da JVM subir
```

### Correct

```text
1. medir: o spill está em todas as tasks (partições) ou numa (skew)?
2. todas → subir o número inicial de partições; o AQE junta as pequenas depois
3. medir de novo: spill em disco foi a 0 E o resultado é idêntico
```

## Related

- [event-log](event-log.md) · [shuffle](shuffle.md)
- [shuffle-partition-sizing](../patterns/shuffle-partition-sizing.md)
