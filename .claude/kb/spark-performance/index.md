# Spark Performance Knowledge Base

> **Purpose**: Performance de jobs e pipelines Spark 3.5 + Delta 3.2.1 **medida pelo event log**: skew, spill, shuffle, passes sobre o dado e tamanho de arquivo, com o gate `PERF=` que só aceita ganho quando o resultado é idêntico
> **MCP Validated**: 2026-09-23 (fonte do Spark na tag `v3.5.5` e do Delta na tag `v3.2.1`; event logs reais de `apache/spark:3.5.9`)

⚠️ **Performance nunca troca resultado.** Toda otimização entra só se os
controles em Decimal e o multiconjunto da saída forem idênticos aos da
baseline. Otimização que muda o número é defeito, não ganho (Regras 3 e 5).

A gravação em Delta (commit, `replaceWhere`, reconferência) é do
[`kb/delta-lake`](../delta-lake/index.md). Este domínio cobre o **custo**
dela, sem repetir a doutrina.

---

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/event-log.md](concepts/event-log.md) | Ligar o event log; eventos e campos exatos; agregar por stage; relógio de parede vs `nanoTime` |
| [concepts/skew.md](concepts/skew.md) | Medir por max/mediana de tempo e bytes; o que o AQE parte e o que não parte |
| [concepts/spill.md](concepts/spill.md) | `Memory` vs `Disk Bytes Spilled`; causas; memória unificada; AQE não parte partição grande |
| [concepts/shuffle.md](concepts/shuffle.md) | Quem embaralha; `exceptAll` por dentro; broadcast; passes sobre o dado |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/measure-before-after.md](patterns/measure-before-after.md) | O protocolo: baseline, mesmo ambiente, resultado idêntico, `PERF=` |
| [patterns/single-pass-controls.md](patterns/single-pass-controls.md) | Controles numa `agg` só; `cache` com dono e `unpersist` |
| [patterns/one-pass-reconciliation.md](patterns/one-pass-reconciliation.md) | Os dois `exceptAll` numa agregação: metade do shuffle, mesma prova |
| [patterns/skew-mitigation.md](patterns/skew-mitigation.md) | AQE no join, broadcast, sal determinístico com acumulador Decimal declarado |
| [patterns/shuffle-partition-sizing.md](patterns/shuffle-partition-sizing.md) | Partições iniciais pelo shuffle medido; AQE junta as pequenas |
| [patterns/delta-write-file-sizing.md](patterns/delta-write-file-sizing.md) | `repartition` antes do write, `maxRecordsPerFile`, `operationMetrics`, `OPTIMIZE` |

### Specs (Machine-Readable)

| File | Purpose |
|------|---------|
| [specs/perf-gate.yaml](specs/perf-gate.yaml) | Campos do event log, casos `NAO_MEDIDO`, métricas, pisos, veredito e proibições |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) - Tabelas de consulta rápida

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Event log** | JSON por linha gravado pelo driver; a medição que sobrevive ao job |
| **Stage** | Fronteira de shuffle; a unidade do relatório |
| **Skew** | Uma task muito mais longa que a mediana do stage |
| **Spill** | Partição que não coube na memória de execução e foi ao disco |
| **Baseline** | Medição **e** resultado de referência; é um oráculo (Regra 3) |

---

## Doutrina da bancada (resumo)

| Regra | Em performance |
|---|---|
| 3: não afrouxe o oráculo | baseline não se sobrescreve para o gate passar; reconferência não sai |
| 5: dinheiro é Decimal | otimização que troca tipo do acumulador ou perde centavo é `PIOR` |
| 7: objeção é hipótese | "isto está lento" se mede antes de se consertar |
| 9: ausência não é zero | log ausente, em andamento ou com 0 tasks é `NAO_MEDIDO` |
| 11: escopo | mudança com arquivo novo vai por Task-Spec |

---

## Learning Path

| Level | Files |
|-------|-------|
| **Beginner** | concepts/event-log.md, patterns/measure-before-after.md |
| **Intermediate** | concepts/shuffle.md, patterns/single-pass-controls.md, concepts/spill.md |
| **Advanced** | concepts/skew.md, patterns/one-pass-reconciliation.md, patterns/skew-mitigation.md |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| pipeline-performance-guardian | todos | Medir, decidir e aceitar otimizações com o gate `PERF=` |
| spark-performance-analyzer | concepts/, patterns/shuffle-partition-sizing.md | Diagnóstico de gargalo num job |
| spark-specialist | concepts/shuffle.md | Desenho de job Spark |
| spark-troubleshooter | concepts/spill.md, concepts/event-log.md | Job que falha por memória ou trava |
| delta-lake-specialist | patterns/delta-write-file-sizing.md | Tamanho de arquivo na gravação |

Skill: [`/spark-perf`](../../skills/spark-perf/SKILL.md).
