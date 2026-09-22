---
adr: "0004"
status: superseded
date: 2026-09-21
ground: brownfield
converge_pass: 2
spec_ref: "R-2"
supersedes: ""
superseded_by: "0008"
deciders: "Bruno Nunes"
---

# 0004 — column 13 is a truncated description, not a second code

## Context

O [ADR 0002](0002-especie-appears-twice-so-columns-are-read-by-position.md)
fixou que as duas colunas `Espécie` são lidas por posição, e deixou aberto
**o que cada uma é**.

Medido: a coluna 12 carrega o **código** (`01`, `02`, …, todos numéricos); a
coluna 13 carrega a **descrição** (`Pensão por Morte de`, nenhum numérico).

E a descrição está **truncada em 20 caracteres** — o que a torna perigosa de
um jeito que não aparece no total.

## Decision

A coluna 13 é renomeada **`descricao_especie`** e tratada como rótulo
humano, nunca como chave.

Todo agrupamento, junção e contagem por espécie usa **o código** (coluna 12).
Agrupar por `descricao_especie` é proibido.

## Rejected reading

**Tratar as duas colunas como o mesmo fato**, usando a descrição por ser mais
legível em relatórios.

Descartado por medição: em 3 milhões de linhas, **51 códigos distintos
colapsam em 40 descrições**. Nove descrições cobrem mais de um código, e a
pior delas cobre quatro:

```
'Pensão por Morte de'   <-  códigos 01, 03, 23, 59
'Pensão por Morte Aci'  <-  códigos 02, 93
'Aposentadoria por In'  <-  códigos 04, 83
```

Agrupar por descrição somaria **quatro espécies distintas numa linha só** — e
o total continuaria correto. Nada acusaria: a soma fecha, a contagem fecha, e
o relatório sai com quatro políticas públicas fundidas.

É o modo de falha que esta fábrica existe para impedir: verde pelo motivo
errado.

## Evidence

```sh
python3 -c "
import csv
from collections import defaultdict
por_desc = defaultdict(set)
with open('_raw/D.SDA.PDA.003.EMI.202601.csv', encoding='latin-1', newline='') as f:
    r = csv.reader(f, delimiter=';'); next(r)
    for i, linha in enumerate(r):
        por_desc[linha[13].strip()].add(linha[12].strip())
        if i >= 3_000_000: break
col = {d: c for d, c in por_desc.items() if len(c) > 1}
print('descricoes cobrindo mais de um codigo:', len(col))
print('codigos:', len({c for cs in por_desc.values() for c in cs}),
      '-> descricoes:', len(por_desc))
"
```

observed output:

```
descricoes cobrindo mais de um codigo: 9
codigos: 51 -> descricoes: 40
```

Comprimento máximo da descrição: **20 caracteres**, exatos — truncamento, não
abreviação.

## Consequences

- O contrato nomeia a coluna 12 como `especie` (chave) e a 13 como
  `descricao_especie` (rótulo).
- Um teste **exige** que agrupar por `descricao_especie` produza contagem
  diferente de agrupar por `especie`, e falha se alguém reintroduzir o
  agrupamento por nome. O teste não precisa saber *como* o erro foi cometido.
- ⚠️ **O truncamento é defeito da origem, não da fábrica.** Classificado como
  `CONFIRMED_SOURCE_DEFECT` — preservado e registrado, nunca corrigido. A
  descrição completa, se for necessária, vem de um dicionário à parte.
- Re-verify when: a fonte publicar descrições com mais de 20 caracteres, ou o
  número de códigos distintos mudar.
