# Spark Performance Quick Reference

> Fast lookup tables. For code examples, see linked files.

## Ligar a medição

| Chave | Valor |
|-------|-------|
| `spark.eventLog.enabled` | `true` (default `false`) |
| `spark.eventLog.dir` | `file:///app/trabalho/eventlog/<run_id>` (criar antes) |
| `spark.eventLog.compress` | `false` (default `false`; codec default `zstd`) |
| `spark.app.name` | único por job do pipeline |
| fim do script | `spark.stop()`, senão `.inprogress` |

## Campos do `SparkListenerTaskEnd."Task Metrics"`

| Quero | Campo | Unidade |
|-------|-------|---------|
| tempo da task | `Executor Run Time` | ms (monotônico) |
| CPU | `Executor CPU Time` | ns |
| GC | `JVM GC Time` | ms |
| spill | `Memory Bytes Spilled` / `Disk Bytes Spilled` | bytes (não some os dois) |
| shuffle lido | `Shuffle Read Metrics.Remote Bytes Read` + `.Local Bytes Read` | bytes |
| shuffle escrito | `Shuffle Write Metrics.Shuffle Bytes Written` | bytes |
| entrada / saída | `Input Metrics.Bytes Read` / `Output Metrics.Bytes Written` | bytes |

## Defaults do Spark 3.5 que importam

| Chave | Default |
|-------|---------|
| `spark.sql.shuffle.partitions` | `200` |
| `spark.sql.adaptive.enabled` | `true` |
| `spark.sql.adaptive.coalescePartitions.enabled` | `true` |
| `spark.sql.adaptive.advisoryPartitionSizeInBytes` | `64MB` |
| `spark.sql.adaptive.coalescePartitions.parallelismFirst` | `true` (doc recomenda `false`) |
| `spark.sql.adaptive.skewJoin.enabled` | `true` (só join) |
| `...skewJoin.skewedPartitionFactor` / `...ThresholdInBytes` | `5.0` / `256MB` |
| `spark.sql.autoBroadcastJoinThreshold` | `10MB` |
| `spark.sql.files.maxPartitionBytes` | `128MB` |
| `spark.memory.fraction` / `storageFraction` | `0.6` / `0.5` |

## Sintoma → causa → padrão

| Sintoma no relatório | Causa provável | Veja |
|----------------------|----------------|------|
| `SKEW` num stage de join | chave pesada | [skew-mitigation](patterns/skew-mitigation.md) |
| `SKEW` num `groupBy` com `sum` | raramente é o `groupBy` | [skew](concepts/skew.md) |
| `SPILL` em todas as tasks | partições grandes demais | [shuffle-partition-sizing](patterns/shuffle-partition-sizing.md) |
| `SPILL` numa task | skew | [skew-mitigation](patterns/skew-mitigation.md) |
| mesmo `Stage Name` repetido | ação a mais ou falta de cache | [single-pass-controls](patterns/single-pass-controls.md) |
| dois stages grandes por `exceptAll` | reconferência em 2 passes | [one-pass-reconciliation](patterns/one-pass-reconciliation.md) |
| `numFiles` alto e MB/arquivo baixo | escrita espalhada | [delta-write-file-sizing](patterns/delta-write-file-sizing.md) |
| `RELOGIO` | relógio de parede saltou | [event-log](concepts/event-log.md) |

## Tokens

| Token | Valores |
|-------|---------|
| `MEDICAO` | `OK`, `NAO_MEDIDO` |
| `BASELINE` | `GRAVADA`, `RECUSADA`, `NAO_MEDIDO` |
| `PERF` | `MELHOR`, `IGUAL`, `PIOR`, `NAO_MEDIDO` |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| `time.time()` em volta do job | event log, `Executor Run Time` |
| medir com outro job no contêiner | janela exclusiva ou contêiner isolado |
| aceitar ganho sem conferir o resultado | controles + multiconjunto antes do tempo |
| `count()`, `sum`, `min`, `max` em ações separadas | uma `agg` |
| tirar a reconferência "porque é cara" | passada única, mesma prova |
| `VACUUM`/`overwriteSchema` para acelerar | nunca como otimização |
| `rand()` como sal | `pmod(xxhash64(...), N)` |

## Related Documentation

| Topic | Path |
|-------|------|
| Getting Started | `concepts/event-log.md` |
| Full Index | `index.md` |
| Gate | `specs/perf-gate.yaml` |
