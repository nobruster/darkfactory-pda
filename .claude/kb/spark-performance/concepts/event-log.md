# Event log: a medição que sobra depois que o job acaba

> **Purpose**: O que o Spark 3.5 grava no event log, com os nomes exatos dos campos, e por que ele é a fonte da medição, não a Spark UI nem o relógio do script
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-23 (`JsonProtocol.scala`, `config/package.scala`, `EventLogFileWriters.scala` e `Executor.scala` na tag `v3.5.5`; conferido contra logs reais de `apache/spark:3.5.9`)

## Overview

A Spark UI morre com o driver, e um `time.time()` no script mede a fila, o
download de jar e o `getOrCreate` junto. O **event log** é um arquivo com um
evento JSON por linha, gravado pelo driver e legível depois. É dele que se
tira o tempo de cada stage, o shuffle, o spill e a distribuição das tasks.

## Ligar

| Chave | Default (3.5) | Nesta bancada |
|---|---|---|
| `spark.eventLog.enabled` | `false` | `true` |
| `spark.eventLog.dir` | `file:///tmp/spark-events` | um diretório **por execução**: `/app/trabalho/eventlog/<run_id>` |
| `spark.eventLog.compress` | `false` | `false`: o leitor de referência é stdlib; `zstd` exige biblioteca |
| `spark.eventLog.compression.codec` | `zstd` | irrelevante com `compress=false` |
| `spark.eventLog.rolling.enabled` | `false` | `false` (se `true`: diretório `eventlog_v2_<appId>/events_<n>_<appId>`) |
| `spark.eventLog.logStageExecutorMetrics` | `false` | opcional: picos de memória por stage |

O diretório precisa **existir** antes do `getOrCreate`, porque o Spark não o
cria. O arquivo de um app se chama `<appId>` (em `local[*]`, `local-<ms>`), e
enquanto o app roda o nome termina em `.inprogress`. Sem `spark.stop()`, esse
sufixo fica.

## Eventos que importam

| `"Event"` | Campos usados |
|---|---|
| `SparkListenerLogStart` | `"Spark Version"` |
| `SparkListenerApplicationStart` / `End` | `"App Name"`, `"App ID"`, `"Timestamp"` |
| `SparkListenerEnvironmentUpdate` | `"Spark Properties"` (confs efetivas da sessão) |
| `SparkListenerStageCompleted` | `"Stage Info"`: `"Stage ID"`, `"Stage Attempt ID"`, `"Stage Name"`, `"Number of Tasks"`, `"Submission Time"`, `"Completion Time"`, `"Failure Reason"` |
| `SparkListenerTaskEnd` | `"Stage ID"`, `"Stage Attempt ID"`, `"Task End Reason"."Reason"`, `"Task Info"`, `"Task Metrics"` |

`"Task Metrics"` de um `SparkListenerTaskEnd` (pode faltar em task que
falhou). Trecho **real** de um log do 3.5.9 (`orderBy` com
`shuffle.partitions=2`, AQE desligado), com campos omitidos:

```json
{"Executor Run Time": 6188, "Executor CPU Time": 2125398160, "JVM GC Time": 38,
 "Peak Execution Memory": 327155280,
 "Memory Bytes Spilled": 142606064, "Disk Bytes Spilled": 110952879,
 "Shuffle Read Metrics": {"Remote Bytes Read": 0, "Local Bytes Read": 105171706,
   "Total Records Read": 1468641, "Fetch Wait Time": 0},
 "Shuffle Write Metrics": {"Shuffle Bytes Written": 16327374,
   "Shuffle Write Time": 13918556, "Shuffle Records Written": 1468641},
 "Input Metrics":  {"Bytes Read": 0, "Records Read": 0},
 "Output Metrics": {"Bytes Written": 0, "Records Written": 0}}
```

| Campo | Unidade |
|---|---|
| `Executor Run Time`, `JVM GC Time` | ms |
| `Executor CPU Time`, `Shuffle Write Time` | **ns** |
| `Memory Bytes Spilled` | bytes do dado **desserializado** em memória que foi derramado |
| `Disk Bytes Spilled` | bytes **serializados** gravados em disco |
| shuffle lido | `Remote Bytes Read` + `Local Bytes Read` (em `local[*]`, só local) |

## Agregar por stage

A chave é `(Stage ID, Stage Attempt ID)`. Uma nova tentativa vira outra linha.
Por stage: número de tasks, soma e distribuição de `Executor Run Time`, soma de
shuffle lido e escrito, soma de spill e `Stage Name` (é o *callsite*, por
exemplo `count at job.py:42`, que aponta a linha do script). A implementação de
referência está em [`skills/spark-perf/medir_eventlog.py`](../../../skills/spark-perf/medir_eventlog.py).

## Relógio de parede não é relógio de medição

`Executor Run Time` vem de `System.nanoTime()` (monotônico, `Executor.scala`).
`"Timestamp"`, `"Submission Time"`, `"Completion Time"` e `"Finish Time"` vêm
do relógio de parede, que **salta**.

Medido num contêiner sob WSL2: um `JobEnd` seguido de um `JobStart` 34 s "no
passado", e um stage de 1,7 s de executor que aparece com 35,6 s de parede num
app de 24,3 s. Por isso:

| Métrica | Confiável para gate? |
|---|---|
| soma de `Executor Run Time` | sim (monotônico) |
| parede do app (`End - Start`) | só se os timestamps não retrocedem |
| parede do stage | só como indício |

⚠️ O `ApplicationStart` carrega o `startTime` do `SparkContext` e é gravado
**depois** do `BlockManagerAdded`. Isso produz cerca de 1,1 s de retrocesso em
todo log do 3.5.9. É estrutural, não é salto de relógio. O verificador de
referência deu falso positivo por isso até ser corrigido.

## Common Mistakes

### Wrong

```python
t0 = time.time(); job(); print(time.time() - t0)   # mede fila, JVM, jars e relógio
```

### Correct

```python
.config("spark.eventLog.enabled", "true")
.config("spark.eventLog.dir", f"file:///app/trabalho/eventlog/{run_id}")
.config("spark.eventLog.compress", "false")
# ... e spark.stop() no fim, senão o log fica .inprogress
```

## Related

- [measure-before-after](../patterns/measure-before-after.md)
- [skew](skew.md) · [spill](spill.md) · [shuffle](shuffle.md)
