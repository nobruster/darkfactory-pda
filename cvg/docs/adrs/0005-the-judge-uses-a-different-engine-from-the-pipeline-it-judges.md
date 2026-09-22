---
adr: "0005"
status: superseded
date: 2026-09-21
ground: brownfield
converge_pass: 2
spec_ref: "R-1, R-5"
supersedes: ""
superseded_by: "0006"
deciders: "Bruno Nunes"
---

# 0005 — the judge uses a different engine from the pipeline it judges

## Context

O carregamento usa **Spark + MinIO** — é o que o script atual faz, é onde o
dado precisa chegar (lago, Parquet, Delta), e é o que escala quando 24
competências precisam ser reprocessadas.

A pergunta que restava: o **juiz** também usa Spark?

Se usar, o juiz herda os modos de falha do motor que julga. Um defeito de
particionamento, de `coalesce`, de inferência de tipo ou da própria leitura
distribuída apareceria **dos dois lados** — no dado publicado e na
conferência — e os dois concordariam. O gate ficaria verde porque ambos
erraram igual.

É a mesma razão pela qual o Pass 4 do Converge exige um adversário de
**família diferente**: um revisor que compartilha os pontos cegos do autor
confirma o erro em vez de acusá-lo.

## Decision

**Spark grava. Python puro confere.**

| Camada | Motor | Por quê |
|---|---|---|
| Leitura, transformação, escrita no lago | Spark + MinIO | é o destino do dado e escala para reprocessamento |
| Medição da âncora | Python puro, `Decimal`, sequencial | mede a fonte, não o produto |
| Juízo (comparação e classificação) | Python puro | não compartilha defeito com quem julga |

O juiz **não importa PySpark** e não lê Parquet. Ele lê o CSV de `_raw/` e o
agregado que o pipeline declara, e compara.

## Rejected reading

**Spark em tudo**, inclusive na conferência. É mais simples de operar — um
motor só, um cluster só, o `spark-defaults.conf` já configurado — e
paralelizaria a conferência junto com o resto.

Descartado porque a conferência passaria a medir o que o Spark produziu, não
o que a fonte publicou. O caso concreto desta fonte: `Espécie` aparece duas
vezes no cabeçalho (ADR 0002). Se a leitura do Spark descartar uma das duas —
que é o comportamento padrão de várias bibliotecas — uma conferência também
em Spark leria o mesmo dado mutilado e confirmaria o total. **Nada acusaria.**

Também descartado: **Python puro em tudo**, sem Spark. A medição da âncora
levou 64s e o pipeline completo 73s (measured), então o volume caberia. Mas o
dado precisa chegar ao lago em Parquet, e reprocessar 24 competências em
sequência não escala.

## Evidence

Medido nesta máquina, em Python puro sobre os 10,88 GB:

```sh
# conversão Decimal + soma + agrupamento por código, 10M linhas
python3 -c "... csv.reader ... Decimal ... por_especie[cod] += v ..."
```

observed output:

```
10,000,000 linhas em 17s  (0.6M linhas/s)
espécies distintas: 56
extrapolado para 41.572.553: 73s
```

A âncora completa, medida antes, levou **64s** para as 41.572.553 linhas.

O ambiente atual:

```
memória: 15 GB
MinIO em localhost:9000 e minio1:9000 — sem resposta
pyspark — ausente
```

⚠️ **A infra não existe nesta máquina.** Montá-la faz parte do escopo, e
entra como tarefa no plano do Pass 3.

## Consequences

- O juiz é uma tarefa **sem dependência de Spark**. Seus testes rodam sem
  cluster, o que também os torna rápidos e determinísticos.
- A âncora continua sendo medida por `scripts/medir_ancora.py`, fora do
  pipeline (ADR 0001). Esta decisão estende o mesmo princípio à comparação.
- O pipeline Spark declara seu agregado num formato que o juiz lê — um
  contrato de saída, não um Parquet que o juiz precise interpretar.
- ⚠️ **Subir Spark + MinIO é trabalho no plano**, não pré-requisito
  silencioso. Enquanto não existir, o juiz e a âncora funcionam; o
  carregamento não.
- Re-verify when: o volume por competência crescer a ponto de a conferência
  sequencial estourar o limite de R-9, ou a fonte passar a publicar em
  formato que exija leitura distribuída.
