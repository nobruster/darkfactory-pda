---
adr: "0008"
status: accepted
date: 2026-09-21
ground: brownfield
converge_pass: 2
spec_ref: "R-3, R-6"
supersedes: "0004"
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0008 — the description defect is collapsed identity, not field width

## Context

O ADR 0004 registrou que a coluna 13 é descrição truncada, não um segundo
código, e que 51 códigos colapsam em 40 descrições. O fato está certo. O
**critério de detecção** que dele se derivou, não.

O plano do Pass 3 chegou a declarar dois critérios de largura, em rodadas
diferentes do Pass 4, e a medição derruba os dois:

- **`len(bruto) == 20`** — todas as 41.572.553 descrições têm exatamente 20
  caracteres brutos. O campo é de largura fixa. A regra marcaria **toda
  linha** como defeituosa, o que não classifica nada.
- **`len(strip()) == 20`** — pega 10 dos 11 colapsos, e deixa de fora
  justamente o pior: `'Pensão por Morte de '`, com `strip` de 19, que sozinho
  funde quatro códigos.

Largura é propriedade do layout, não do defeito.

## Decision

**O defeito é a descrição cobrir mais de um código.**

Na competência 2026-01, 11 descrições cobrem 24 códigos distintos. Uma
descrição que identifica mais de uma espécie perdeu a informação que a
distingue — é isso que impede agrupar por ela, e é isso que a fábrica
classifica.

O código sobrevive ao colapso; a descrição não. Essa assimetria é o motivo
pelo qual o ADR 0002 manda ler por posição: as duas colunas têm cabeçalho
`Espécie` idêntico, e só a posição diz qual delas preserva identidade.

A cardinalidade do colapso é medida na competência, nunca fixada em código —
o ADR 0004 registrou 51→40 sobre ~3 milhões de linhas, e a competência
inteira tem 65 códigos, 52 descrições e 11 colapsos.

## Rejected reading

**Que o truncamento fosse detectável pela largura do campo.**

É a leitura natural: o campo tem 20 caracteres, a descrição que não coube foi
cortada, logo descrição no limite é descrição truncada.

O contraexemplo está na própria fonte. `'Auxílio Reclusão    '` tem `strip`
de 17 e é completa; `'Pensão por Morte de '` tem 19 e está cortada no meio de
uma frase — "de" quê? Largura não distingue as duas, porque o corte pode cair
antes de preencher os 20 caracteres.

E o caso decisivo: se a largura bruta fosse o critério, as 41.572.553 linhas
seriam defeito. Um classificador que acusa tudo é indistinguível de um que
não acusa nada.

## Evidence

```sh
python3 scripts/medir_layout.py
python3 scripts/medir_colapso.py
```

observed output (layout):

```
  campos no cabeçalho : 14
  linhas lidas        : 41,572,553
  campos por linha: 14 -> 41,572,553
  largura BRUTA do campo descrição (índice 13):
     20 ->   41,572,553
  códigos com MAIS DE UMA descrição bruta: 0
```

observed output (colapso):

```
  códigos distintos    : 65
  descrições distintas : 52
  descrições que cobrem >1 código: 11
  códigos que perdem identidade  : 24

    'Pensão por Morte de '   strip=19  cobre 4: ['01', '03', '23', '59']
    'Aposentadoria por In'   strip=20  cobre 2: ['04', '83']
    ...
  colapsos que len(strip())==20 NÃO pegaria: 1
```

## Consequences

- A leitura emite defeito de identidade colapsada quando a descrição cobre
  mais de um código, e **não** por largura. Uma linha com descrição
  truncada mas identidade preservada não é defeito.
- O defeito é da descrição, não da linha: a linha permanece válida e o valor
  monetário entra nos controles (Regra 4 — classificar, nunca corrigir).
- Agrupar por descrição funde 24 códigos em 11 grupos nesta competência; por
  isso R-3 exige a chave por código, e a fronteira compara os mapas por
  valor.
- A contagem de colapsos entra no contrato como valor **medido**, junto da
  cardinalidade de códigos — comparar contra um número fixado em código
  recusaria uma competência legítima que mudasse de perfil.
- Re-verify when: uma competência nova for ancorada, ou a fonte alargar o
  campo de descrição.
