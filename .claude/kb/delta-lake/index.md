# Delta Lake (OSS) Knowledge Base

> **Purpose**: Delta Lake **open-source** 3.2.1 sobre Spark 3.5 + S3A (MinIO) — gravar e ler camadas de medalhão com commit atômico, schema imposto, dinheiro em `DecimalType` e histórico preservado como evidência
> **MCP Validated**: 2026-09-23 (docs do Delta na tag `v3.2.1` do `delta-io/delta`)

⚠️ **Não é Databricks nem DLT/Lakeflow.** Para pipeline declarativo no
Databricks, use `lakeflow-*` em `agents/data-engineering/`. Aqui não há
`expectations`, Unity Catalog, `APPLY CHANGES` nem auto-optimize: só a
biblioteca `delta-spark` sobre um Spark que você sobe.

---

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/transaction-log.md](concepts/transaction-log.md) | `_delta_log`, commit atômico, versão, snapshot, LogStore do S3 |
| [concepts/schema-enforcement.md](concepts/schema-enforcement.md) | Imposição sempre ligada; evolução só aditiva e opt-in; tipo monetário nunca muda |
| [concepts/constraints.md](concepts/constraints.md) | `CHECK` e `NOT NULL` como cerca do domínio dentro da tabela |
| [concepts/time-travel-retention.md](concepts/time-travel-retention.md) | `versionAsOf`, histórico, retenção e por que `VACUUM` destrói evidência |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/session-s3a-minio.md](patterns/session-s3a-minio.md) | Sessão Spark + Delta 3.2.1 + MinIO, com ANSI ligado |
| [patterns/contract-table-bootstrap.md](patterns/contract-table-bootstrap.md) | Criar a tabela a partir do contrato: `DecimalType`, `NOT NULL`, `CHECK`, retenção |
| [patterns/idempotent-partition-overwrite.md](patterns/idempotent-partition-overwrite.md) | Regravar uma competência com `replaceWhere`, atômico e idempotente |
| [patterns/snapshot-lineage.md](patterns/snapshot-lineage.md) | Ler um snapshot resolvido uma vez e registrar a versão lida no `userMetadata` |
| [patterns/write-and-reconcile.md](patterns/write-and-reconcile.md) | Reler a versão commitada e comparar multiconjunto + controles; zero linhas = `NAO_MEDIDO` |
| [patterns/additive-schema-evolution.md](patterns/additive-schema-evolution.md) | Guarda que só deixa `mergeSchema` passar quando a mudança é aditiva |
| [patterns/maintenance-optimize-vacuum.md](patterns/maintenance-optimize-vacuum.md) | `OPTIMIZE`/Z-ORDER como otimização; `VACUUM` só com retenção declarada |

### Specs (Machine-Readable)

| File | Purpose |
|------|---------|
| [specs/delta-oss-env.yaml](specs/delta-oss-env.yaml) | Versões, configurações obrigatórias e opções proibidas desta bancada |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) - Tabelas de consulta rápida

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Commit atômico** | Cada escrita vira um arquivo JSON numerado em `_delta_log/`; ou entra inteira, ou não entra |
| **Snapshot** | Uma versão da tabela. Resolva **uma vez** e leia com `versionAsOf` |
| **Schema enforcement** | O DataFrame precisa casar com a tabela em nome e tipo; senão, exceção |
| **replaceWhere** | Sobrescreve atomicamente só as linhas que casam o predicado |
| **Histórico = evidência** | `DESCRIBE HISTORY` + time travel provam o que foi publicado (Regra 4) |

---

## Doutrina da bancada (resumo)

| Regra | No Delta |
|---|---|
| 5 — dinheiro é Decimal | `DecimalType(p, s)` do contrato, `spark.sql.ansi.enabled=true` |
| 3 — não afrouxe o oráculo | `mergeSchema` não muda tipo; `overwriteSchema` nunca silencioso |
| 4 — preserve o defeito | nada de `VACUUM` abaixo da retenção; `OPTIMIZE` não corrige |
| 9 — ausência não é zero | releitura com zero linhas devolve `NAO_MEDIDO` |

---

## Learning Path

| Level | Files |
|-------|-------|
| **Beginner** | concepts/transaction-log.md, concepts/schema-enforcement.md |
| **Intermediate** | patterns/session-s3a-minio.md, patterns/idempotent-partition-overwrite.md |
| **Advanced** | patterns/snapshot-lineage.md, patterns/write-and-reconcile.md |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| delta-lake-specialist | todos | Gravar, ler, reconferir e manter tabelas Delta OSS |
| medallion-architect | concepts/, patterns/idempotent-partition-overwrite.md | Desenho das camadas bronze/silver/gold |
| spark-specialist | patterns/session-s3a-minio.md | Sessão e desempenho do Spark que escreve |

Skill: [`/delta-lake`](../../skills/delta-lake/SKILL.md).

Custo das gravações (tamanho de arquivo, reconferência mais barata, medição
pelo event log): [`kb/spark-performance`](../spark-performance/index.md) e
[`/spark-perf`](../../skills/spark-perf/SKILL.md).
