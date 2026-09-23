---
name: delta-lake
description: Gravar e ler camadas de medalhão (bronze, silver, gold) em Delta Lake open-source 3.2.1 sobre Spark 3.5 + S3A/MinIO, com prova. Use quando for escrever ou ler uma competência em Delta, regravar uma partição, evoluir schema, consultar o que foi publicado numa versão, ou rodar OPTIMIZE/VACUUM. Não serve para Databricks/DLT (use os agentes lakeflow-*).
version: 1.0.0
user-invocable: true
argument-hint: "[gravar|ler|reconferir|evoluir|historico|manter] [camada] [competencia]"
---

## MANDATORY PREPARATION

1. Leia `AGENTS.md` — Regras 2, 3, 4, 5, 9 e 11 governam tudo abaixo.
2. Carregue `.claude/kb/delta-lake/quick-reference.md` e
   `.claude/kb/delta-lake/specs/delta-oss-env.yaml`.
3. Localize o **contrato** da fábrica. Se ele é `NAO_MEDIDO`, pare: sem
   âncora não se grava silver nem gold (Regra 2). Não gere a âncora.

Para julgamento além deste procedimento, chame o agente
`delta-lake-specialist`.

---

Este procedimento grava e lê Delta **com prova**. Toda ação termina com um
token estável na última linha e código de saída ≠ 0 em qualquer estado que
não seja sucesso. "A escrita não deu erro" nunca é o resultado.

## Passo 0 — Sessão (todas as ações)

Use a sessão de `kb/delta-lake/patterns/session-s3a-minio.md`. Confira na
sessão **real** (o `getOrCreate` reaproveita sessão existente):

| Chave | Valor exigido |
|---|---|
| `spark.sql.extensions` | `io.delta.sql.DeltaSparkSessionExtension` |
| `spark.sql.catalog.spark_catalog` | `org.apache.spark.sql.delta.catalog.DeltaCatalog` |
| `spark.sql.ansi.enabled` | `true` |
| `spark.databricks.delta.schema.autoMerge.enabled` | `false` |
| `spark.databricks.delta.retentionDurationCheck.enabled` | `true` |
| `spark.databricks.delta.replaceWhere.constraintCheck.enabled` | `true` |

Divergência → `SESSAO=DIVERGE`, pare.

Dependências: `delta-spark==3.2.1 --no-deps` no Python e os jars
`io.delta:delta-spark_2.12:3.2.1` + `io.delta:delta-storage:3.2.1`.
**Não** use `configure_spark_with_delta_pip` (quebra com `--no-deps`).

## `gravar <camada> <competencia>`

1. **Validar a competência** com `^\d{4}-\d{2}$`. Ela vira predicado SQL.
2. **Tabela contra o contrato** — `contract-table-bootstrap.md`:
   `TABELA=CRIADA|CONFERE`. `DIVERGE` → pare e investigue; nunca ajuste o
   contrato à tabela (Regra 3).
3. **Ler a camada anterior por snapshot** — `snapshot-lineage.md`: resolver
   a versão **uma vez**, ler com `versionAsOf`, filtrar pela competência.
   Na bronze, a fonte é o arquivo bruto: registre o `sha256` dele.
4. **Montar o DataFrame julgado** com `cast` explícito para o tipo do
   contrato (`DecimalType(p, s)`), sem `inferSchema`. Linhas que o contrato
   recusa são **classificadas** (Regra 4), contadas e reportadas — não
   filtradas em silêncio. `cache()` e materialize.
5. **Recusar zero linhas.** Um `replaceWhere` vazio é um commit válido que
   apaga a competência. `GRAVACAO=RECUSADO`.
6. **Gravar** — `idempotent-partition-overwrite.md`:
   `mode("overwrite")` + `replaceWhere("competencia = '<c>'")` +
   `userMetadata` com `run_id`, `camada`, `fonte`, `fonte_versao`.
   Sem `mergeSchema`, sem `overwriteSchema`.
7. **Achar o próprio commit** pelo `run_id` no `history()`.
8. **Reconferir** — `write-and-reconcile.md`. Última linha:
   `RECONFERENCIA=CONFERE|DIVERGE|NAO_MEDIDO|ERRO`.

## `ler <camada> [competencia]`

1. Resolver a versão uma vez; ler com `versionAsOf`; filtrar pela
   competência. Nunca dois `load(p)` sem versão no mesmo job.
2. Reportar a versão lida junto com qualquer número que sair dali.
3. Zero linhas lidas → `LEITURA=NAO_MEDIDO`, não um total zero (Regra 9).

## `reconferir <camada> <competencia> [versao]`

Relê a versão (default: a última) e compara com o DataFrame julgado ou com
os controles registrados na evidência daquela execução. Mesmo algoritmo de
`write-and-reconcile.md`: schema (nome + tipo), `exceptAll` nos dois
sentidos, controles (linhas, nulos, soma, mínimo, máximo) em `Decimal`.

## `evoluir <camada> <colunas>`

1. Exigir o ADR / versão do contrato que nomeia as colunas novas.
2. Rodar `classificar_evolucao` de `additive-schema-evolution.md`.
3. `ADITIVA` → `mergeSchema` **só nesta escrita**. `RECUSADA` → pare.
4. Mudança de tipo — e em especial de tipo monetário — é sempre `RECUSADA`.

## `historico <camada> [data]`

`history()` com `version`, `timestamp`, `operation`,
`operationParameters`, `readVersion`, `userMetadata`, `operationMetrics`.
Para "o que foi publicado em *data*": achar a versão vigente e reler com
`versionAsOf`. Se a versão já não é legível, reporte **evidência perdida**
e a retenção da tabela — não reconstrua.

## `manter <camada> [competencia]`

1. `OPTIMIZE` (compactação ou Z-ORDER em coluna não particionada) com a
   reconferência de conteúdo de `maintenance-optimize-vacuum.md`:
   `OPTIMIZE=OK|DIVERGE`.
2. `VACUUM`: **não execute** a partir desta skill. Rode `DRY RUN`, arquive a
   lista e devolva ao usuário com a retenção da tabela e o ADR exigido. Nunca
   desligue `retentionDurationCheck`, nunca retenção abaixo da da tabela.

## NEVER

- Float/`DoubleType`/`inferSchema` em campo monetário.
- `spark.sql.ansi.enabled=false`.
- `mode("overwrite")` sem `replaceWhere` numa tabela com várias competências.
- `mergeSchema` como resposta a erro de schema; `autoMerge` na sessão.
- `overwriteSchema`, `DROP CONSTRAINT`, `restoreToVersion` ou `VACUUM` sem ADR.
- Filtrar linhas para um `CHECK` passar.
- Reportar sucesso sem reler a versão commitada.
- Tratar zero linhas lidas como medição.
- Seguir `docs.delta.io/latest` (4.x) — a referência é a tag `v3.2.1`.
- Um segundo escritor na mesma tabela S3 sem o LogStore do DynamoDB.

## Output

```text
AÇÃO:        gravar silver 2026-01
SESSÃO:      OK (ansi=true, autoMerge=false)
FONTE:       s3a://lake/bronze/beneficios @ v12
TABELA:      CONFERE
GRAVAÇÃO:    OK → s3a://lake/silver/beneficios @ v7  (run_id=…)
CONTROLES:   linhas=41572553 nulos=0 soma=78521752562.12
MULTICONJ.:  só julgado=0  só lago=0
RECONFERENCIA=CONFERE
```
