---
name: spark-perf
description: Medir performance de um job ou do pipeline Spark/Delta inteiro pelo event log (tempo por stage, shuffle lido/escrito, spill em memória/disco, razão de skew) e decidir se uma mudança é ganho com o gate PERF=MELHOR|IGUAL|PIOR|NAO_MEDIDO contra uma baseline gravada. Use antes e depois de qualquer otimização, ao ver um job lento, spill, skew ou shuffle grande, ou para detectar regressão de performance. Só aceita ganho com resultado idêntico (controles em Decimal + multiconjunto).
version: 1.0.0
user-invocable: true
argument-hint: "[relatorio|baseline|comparar] [eventlog-dir] [job]"
---

## MANDATORY PREPARATION

1. Leia `AGENTS.md`: as Regras 3, 5, 7, 9 e 11 governam tudo abaixo.
2. Carregue `.claude/kb/spark-performance/quick-reference.md` e
   `.claude/kb/spark-performance/specs/perf-gate.yaml`.
3. Confirme que o job **já grava corretamente**: `RECONFERENCIA=CONFERE` do
   `/delta-lake`. Performance de um job errado não se mede, se conserta
   primeiro.

Para julgamento além deste procedimento, chame o agente
`pipeline-performance-guardian`.

---

Este procedimento mede pelo **event log** do Spark e decide com o script de
referência [`medir_eventlog.py`](medir_eventlog.py) (Python puro, sem
pyspark). Toda ação termina com um token estável na última linha, e com
código de saída ≠ 0 em qualquer estado que não seja sucesso.

**Performance nunca troca resultado.** O gate compara controles e
multiconjunto **antes** de olhar o tempo; resultado diferente é `PIOR`.

## Passo 0: Instrumentar o job (todas as ações)

Na sessão do job (ver `kb/spark-performance/patterns/measure-before-after.md`):

| Chave | Valor |
|---|---|
| `spark.eventLog.enabled` | `true` |
| `spark.eventLog.dir` | `file:///app/trabalho/eventlog/<run_id>`: **um diretório por execução**, criado antes |
| `spark.eventLog.compress` | `false` |
| `spark.app.name` | único por job do pipeline |

E `spark.stop()` no fim. O pipeline inteiro (vários `spark-submit`) grava no
**mesmo** `<run_id>`: o script agrega os apps e compara app a app.

O job grava também um **arquivo de resultado** (JSON) com os controles da
saída, em string, pela mesma função `controles()` do `/delta-lake`:

```json
{"controles": {"linhas": "41572553", "nulos": "0", "soma": "78521752562.12",
               "minimo": "0.01", "maximo": "99999.99"},
 "multiconjunto": {"so_baseline": 0, "so_atual": 0}}
```

`multiconjunto` é a diferença entre a saída **desta** execução e a saída da
**baseline** (versão Delta lida por `versionAsOf`), nos dois sentidos, por
`exceptAll` ou pela passada única equivalente
(`patterns/one-pass-reconciliation.md`). Na gravação da baseline, ele não é
exigido.

⚠️ **Ambiente exclusivo.** Não meça com outro job, loop ou teste rodando no
mesmo contêiner. Se não houver janela, use um contêiner separado com a
**mesma imagem** e limites de CPU e memória declarados, e compare só com
baseline medida no mesmo arranjo.

## `relatorio <eventlog-dir>`

```bash
python3 .claude/skills/spark-perf/medir_eventlog.py relatorio /app/trabalho/eventlog/<run_id>
```

Uma linha por stage: tasks, parede, `Executor Run Time`, `max/med` (skew de
tempo), `skB` (skew de bytes), entrada, shuffle R/W, spill memória/disco, e
os sinais `SKEW`, `SPILL`, `GC`, `FALHA` e `RELOGIO`. O `Stage Name` aponta a
linha do script (`count at job.py:42`). Termina em `MEDICAO=OK|NAO_MEDIDO`.

Leia o relatório nesta ordem:

1. **Stages ordenados por `run_ms`**: o topo é onde vale mexer.
2. **Mesmo `Stage Name` repetido**: ação a mais ou falta de cache
   (`patterns/single-pass-controls.md`).
3. **`SPILL`**: em todas as tasks, partições (`shuffle-partition-sizing.md`);
   em uma só, skew.
4. **`SKEW`** com `skB` alto: skew de dado (`skew-mitigation.md`).
5. **Dois stages grandes da reconferência**: `one-pass-reconciliation.md`.
6. **`RELOGIO`**: o relógio de parede saltou; confie só no `run_ms`.

## `baseline <eventlog-dir> <job>`

```bash
python3 .claude/skills/spark-perf/medir_eventlog.py baseline /app/trabalho/eventlog/<run_id> \
  --resultado <resultado.json> --gravar perf/baseline-<job>.json
```

1. Rode a execução de referência **duas vezes** e compare uma com a outra
   (`comparar`). Se der `PIOR` entre duas execuções iguais, a tolerância é
   pequena para o ambiente: registre o ruído e ajuste `--tolerancia` **antes**
   de qualquer otimização, nunca depois de uma reprovar.
2. Grave a baseline. Se o arquivo já existe, o script devolve
   `BASELINE=RECUSADA`. `--substituir` é decisão deliberada: uma mudança
   aceita, registrada, e nunca para um `PIOR` passar (Regra 3).

## `comparar <eventlog-dir> <job>`

```bash
python3 .claude/skills/spark-perf/medir_eventlog.py comparar /app/trabalho/eventlog/<run_id> \
  --resultado <resultado.json> --baseline perf/baseline-<job>.json [--tolerancia 0.10]
```

O gate decide nesta ordem:

| # | Checagem | Falha → |
|---|---|---|
| 1 | log existe, terminou, não comprimido, sem linha ilegível, > 0 tasks | `NAO_MEDIDO` |
| 2 | resultado com controles em string e multiconjunto | `NAO_MEDIDO` |
| 3 | controles idênticos e multiconjunto 0/0 | `PIOR` |
| 4 | mesmos apps, mesmo Spark, mesmo `master` e memória | `NAO_MEDIDO` |
| 5 | parede (se o relógio foi consistente), executor, shuffle, spill: alguma pior > tolerância, no total **ou** num app | `PIOR` |
| 6 | alguma melhor > tolerância, nenhuma pior | `MELHOR` |
| — | senão | `IGUAL` |

As mudanças em `spark.sql.*` entre as execuções são listadas, porque são a
otimização. Mudanças de `master` ou de memória invalidam a comparação.

## Depois do veredito

| Veredito | Ação |
|---|---|
| `MELHOR` | a mudança pode entrar, **pelo caminho do repositório**: arquivo novo ou fora do `creates_paths` vai por Task-Spec (Regra 11). Rebaseline com `--substituir` depois de aceita |
| `IGUAL` | só entra se simplifica o código; não há ganho a declarar |
| `PIOR` por resultado | **defeito**: reverter e investigar; nunca ajustar a baseline |
| `PIOR` por métrica | reverter; a hipótese de otimização foi refutada (Regra 7) |
| `NAO_MEDIDO` | não há ganho a declarar; conserte a medição e rode de novo |

## Verificador

```bash
python3 -m pytest .claude/skills/spark-perf/ -v
```

Os testes injetam cada defeito (log ausente, `.inprogress`, comprimido,
corrompido, zero tasks, float no resultado, centavo a menos, linha trocada,
baseline sobrescrita, spill novo, ganho num app escondendo perda noutro,
ambiente diferente, salto de relógio) e provam que o script **acusa**.

## NEVER

- Declarar ganho sem `PERF=MELHOR` impresso pelo gate.
- Remover a reconferência (`exceptAll`/multiconjunto) ou os controles para ganhar tempo.
- Trocar `exceptAll` por `subtract`, `count`, amostra ou hash.
- `VACUUM`, `overwriteSchema`, `ansi.enabled=false` ou `DoubleType` como otimização.
- Substituir a baseline porque o gate deu `PIOR`.
- Escrever `so_baseline: 0` à mão sem ter rodado a diferença.
- Medir com outro job no mesmo contêiner, ou comparar ambientes diferentes.
- Tratar `NAO_MEDIDO` como `IGUAL` no chamador.

## Output

Formato do resumo (números ilustrativos, não medidos):

```text
AÇÃO:        comparar silver 2026-01
EVENTLOG:    /app/trabalho/eventlog/r-20260923-02  (1 app, 57 stages, spark 3.5.9)
RESULTADO:   idêntico (controles e multiconjunto 0/0)
CONF:        spark.sql.shuffle.partitions 200 -> 32
MÉTRICAS:    executor 412.0 s -> 298.4 s (-27.6%)  spill disco 1.2 GB -> 0
PERF=MELHOR
```
