---
adr: "0000"
status: accepted
date: 2026-09-21
ground: brownfield
converge_pass: 2
spec_ref: "R-1, R-2"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0000 — Context: the ground we stand on

## Terrain

**Brownfield.** Existe um carregamento rodando hoje
(`docs/legado/01-LANDING-MACICAPDA.py`): baixa o ZIP da fonte pública, lê o
CSV com Spark e grava Parquet no MinIO. Ele funciona — e publica sem
conferência alguma.

Os ADRs desta pasta registram o que **já é verdade** sobre esse terreno, não
o que queremos construir.

## Given surface

Medido nesta máquina, não presumido:

- **A fonte** — `D.SDA.PDA.003.EMI.202601.CSV.ZIP`, 575.423.625 bytes,
  publicada em 25/02/2026 pelo Portal de Dados Abertos. Congelada em `_raw/`,
  `chmod 444`, sha256 em `_raw/CHECKSUMS.txt`.
- **O CSV** — 10,88 GB extraídos, 14 colunas, separador `;`, encoding
  latin-1. `Espécie` aparece **duas vezes** ([ADR 0002](0002-especie-appears-twice-so-columns-are-read-by-position.md)).
- **A âncora** — 41.572.553 linhas somando 78.521.752.562,12, medida em 64s
  por `scripts/medir_ancora.py`, independente do pipeline
  ([ADR 0001](0001-the-2026-01-anchor-is-41572553-rows-summing-78521752562-12.md)).
- **O carregamento atual** — Spark 3 + MinIO, grava Parquet com
  `mode("overwrite")`. Preservado como evidência do que existe, **não como
  especificação**.
- **As ferramentas** — `converge`, `task-spec 3.8.1`, `seamwise`, e o juiz de
  exemplo em `fabrica/`. `DOCTOR_HOST=OK`.

## Build surface

O que os passes seguintes ainda precisam construir:

- Leitura posicional da competência, preservando os bytes originais
- Agregação monetária exata, com regra de arredondamento declarada
- Juízo que compara o agregado contra a âncora e classifica toda diferença
- Pacote de evidência por execução

Decidido no Pass 3, não aqui: se o motor será Spark, Polars ou leitura
sequencial; onde o resultado é gravado.

## Spec

[`../tech-spec/`](../tech-spec/) — **ainda não escrita.** O BRD está em
[`../brd/brd-pda-beneficios.md`](../brd/brd-pda-beneficios.md), com sign-off
`canonical` de 2026-09-21.

## Three defects already known

O script atual carrega três defeitos que este projeto **não** herda:

| Defeito | Por quê importa |
|---|---|
| `mode("overwrite")` | destrói a execução anterior; impossível responder depois o que foi publicado |
| leitura por nome com `Espécie` duplicada | perde uma das duas em silêncio |
| credenciais em texto puro no código | não há como rotacionar sem reeditar |

⚠️ **A fábrica classifica, nunca corrige.** Estes são defeitos do carregamento
atual, não da fonte — e o carregamento continua rodando enquanto isto é
construído ao lado.
