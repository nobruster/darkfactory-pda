# Medir antes e depois, com o resultado idêntico

> **Purpose**: O protocolo que transforma "ficou mais rápido" em evidência: baseline gravada, mesmo ambiente, event log, e resultado provado igual antes de olhar o tempo
> **MCP Validated**: 2026-09-23

## When to Use

- Antes de qualquer mudança feita "por performance" num job ou no pipeline
- Para decidir se uma otimização entra (`PERF=MELHOR|IGUAL`) ou sai (`PIOR|NAO_MEDIDO`)
- Para detectar regressão: toda mudança de código ou de configuração num job monitorado

## Doutrina

| Regra | Por quê |
|---|---|
| **Resultado primeiro, tempo depois** | um job 3× mais rápido que perde um centavo é um defeito (Regras 3 e 5) |
| **Mesmo ambiente, sem carga concorrente** | outro job no mesmo contêiner mede a fila, não o seu código |
| **Sem medição não há ganho** | log ausente, vazio ou em andamento é `NAO_MEDIDO`, nunca `IGUAL` (Regra 9) |
| **A baseline é um oráculo** | substituí-la é decisão deliberada, nunca para o gate passar (Regra 3) |
| **Calibre o ruído** | rode a baseline duas vezes; se o gate acusar `PIOR` entre elas, a tolerância é pequena para o ambiente |

## Implementation

### 1. Sessão que grava o event log

```python
import os
from pyspark.sql import SparkSession

def sessao_medida(nome_app: str, run_id: str, base="/app/trabalho/eventlog"):
    destino = os.path.join(base, run_id)
    os.makedirs(destino, exist_ok=True)          # o Spark não cria o diretório
    return (SparkSession.builder.appName(nome_app)            # nome ÚNICO por job
            .config("spark.eventLog.enabled", "true")
            .config("spark.eventLog.dir", f"file://{destino}")
            .config("spark.eventLog.compress", "false")
            # ... as confs obrigatórias de kb/delta-lake/patterns/session-s3a-minio.md
            .getOrCreate())
```

⚠️ `getOrCreate` reaproveita uma sessão viva, e as confs de event log de uma
sessão já criada **não mudam**. Confirme no relatório que o app apareceu.

⚠️ Termine com `spark.stop()`. Sem isso, o arquivo fica `.inprogress` e a
medição é `NAO_MEDIDO`.

### 2. Arquivo de resultado (o job grava, o gate lê)

Os controles vêm da **mesma** função `controles()` de
[`write-and-reconcile`](../../delta-lake/patterns/write-and-reconcile.md), em
string. O multiconjunto compara a saída **desta** execução com a saída da
**baseline** (a versão Delta que a baseline publicou, lida por `versionAsOf`):

```json
{"controles": {"linhas": "41572553", "nulos": "0", "soma": "78521752562.12",
               "minimo": "0.01", "maximo": "99999.99"},
 "multiconjunto": {"so_baseline": 0, "so_atual": 0}}
```

Float em qualquer controle é recusado (`NAO_MEDIDO`). Dinheiro trafega como
string.

### 3. Gravar a baseline (uma vez, deliberadamente)

```bash
python3 .claude/skills/spark-perf/medir_eventlog.py baseline \
  /app/trabalho/eventlog/<run_base> --resultado resultado-base.json \
  --gravar perf/baseline-<job>.json
# BASELINE=GRAVADA   (já existe → BASELINE=RECUSADA, a menos que --substituir)
```

### 4. Mudar uma coisa, rodar, comparar

```bash
python3 .claude/skills/spark-perf/medir_eventlog.py comparar \
  /app/trabalho/eventlog/<run_novo> --resultado resultado-novo.json \
  --baseline perf/baseline-<job>.json --tolerancia 0.10
# última linha: PERF=MELHOR|IGUAL|PIOR|NAO_MEDIDO
```

Uma mudança por vez. Duas mudanças medidas juntas não dizem qual ajudou e
qual atrapalhou.

## O que o gate decide

| Ordem | Checagem | Falha → |
|---|---|---|
| 1 | log existe, terminou, não comprimido, sem linha ilegível, > 0 tasks | `NAO_MEDIDO` |
| 2 | resultado com controles (string) e multiconjunto | `NAO_MEDIDO` |
| 3 | controles iguais **e** `so_baseline = so_atual = 0` | `PIOR` (defeito) |
| 4 | mesmos apps, mesma versão do Spark, mesmo `master`/memória | `NAO_MEDIDO` |
| 5 | alguma métrica piorou > tolerância (total **ou** por app) | `PIOR` |
| 6 | alguma melhorou > tolerância, nenhuma piorou | `MELHOR` |
| — | senão | `IGUAL` |

Métricas: tempo de parede (só se o relógio foi consistente), tempo de
executor, shuffle lido+escrito, spill em disco e spill em memória, cada uma
com um piso absoluto de ruído. Mudanças em `spark.sql.*` entre as duas
execuções são **listadas**, não bloqueiam: elas são a otimização.

## Medido

Três execuções reais (`apache/spark:3.5.9`, `local[2]`, 1 CPU):

| Comparação | Resultado |
|---|---|
| baseline × baseline repetida | `PERF=IGUAL` |
| AQE desligado + `shuffle.partitions=2` | `PERF=PIOR` (spill disco 0 → 212 MB) |
| baseline regravada sem `--substituir` | `BASELINE=RECUSADA` |

E duas das três execuções tiveram o **relógio de parede retrocedendo** 29 a
34 s (WSL2). O gate tirou a parede do veredito e decidiu pelo tempo de
executor. Sem essa checagem, a parede de um stage teria sido publicada como
35,6 s num app de 24,3 s.

## Common Mistakes

| Don't | Do |
|---|---|
| medir com o loop do motor rodando no mesmo contêiner | janela exclusiva, ou contêiner separado com a mesma imagem e limites |
| comparar com a baseline de outra máquina | baseline por ambiente; o gate recusa `master`/memória diferentes |
| `--substituir` porque deu `PIOR` | investigar; rebaseline só com a mudança aceita e registrada |
| aceitar `MELHOR` sem o multiconjunto | o gate já recusa, não contorne escrevendo `0` à mão |

## See Also

- [event-log](../concepts/event-log.md)
- skill [`/spark-perf`](../../../skills/spark-perf/SKILL.md)
