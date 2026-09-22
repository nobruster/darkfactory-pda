---
adr: "0009"
status: accepted
date: 2026-09-21
ground: brownfield
converge_pass: 2
spec_ref: "R-4"
supersedes: "0007"
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0009 — the derived precision assumes a monotonic sum with no negative values

## Context

O ADR 0007 estabeleceu que a precisão suficiente é derivada: dígitos inteiros
do total ancorado mais a escala máxima dos intermediários. Para esta âncora,
11 + 3 = 14.

A fórmula tem uma **premissa tácita** que o 0007 não declarou: que nenhum
acumulador intermediário precise de mais dígitos inteiros que o total final.

Um adversário cross-family executou o contraexemplo. Com valores de escala 3
— `[100000000000.005, -100000000000, 0.005, 78521752562.12]` — a soma em
`prec=14` devolve `78521752562.12`, e em `prec=40` devolve `78521752562.13`.
O acumulador passa por 10¹¹ antes de voltar, e nesse pico a precisão derivada
do total já não basta.

A fórmula continua correta. O que faltava era dizer **sob que condição** ela
vale.

## Decision

**A precisão derivada vale sob soma monotônica, e a monotonia é medida.**

Sem valores negativos, o acumulador cresce sempre e nenhum parcial excede o
total final — então dígitos inteiros do total são dígitos inteiros do maior
acumulador, e a fórmula do ADR 0007 se sustenta.

Na competência 2026-01 isso é fato medido, não hipótese: **zero negativos em
41.572.553 valores**, com o pico do acumulador igual ao total, `78521752562,12`,
ambos com 11 dígitos inteiros.

Disso decorre que **valor negativo é defeito classificado**, não entrada
válida. Não por juízo de valor sobre estornos, mas porque um negativo quebra a
premissa aritmética sobre a qual a precisão do contrato foi derivada — e a
perda seria silenciosa, como toda perda decimal.

## Rejected reading

**Elevar a precisão com folga** — fixar 28, o padrão do Python, e absorver
acumuladores maiores sem fechar o domínio.

É mais simples e funcionaria para o contraexemplo. O que a mata é que escolhe
um número por conforto: 28 absorve 10¹¹, e não absorve 10²⁰. Trocar uma
premissa tácita por uma margem arbitrária mantém o mesmo defeito — a fábrica
deixaria de saber **por que** o número é suficiente, e a próxima fonte
quebraria a margem sem nada acusar.

A precisão derivada com domínio declarado diz o que assume. Uma folga
confortável, não.

## Evidence

```sh
python3 scripts/medir_sinal.py
```

observed output:

```
  valores lidos : 41,572,553
  negativos     : 0
  zeros         : 3
  maior valor   : 183725.76
  total             : 78521752562.12
  pico do acumulador: 78521752562.12
  pico > total? False
  sem negativos -> soma MONOTÔNICA crescente
  dígitos inteiros do total: 11
  dígitos inteiros do pico : 11
```

E o contraexemplo que motivou este ADR:

```sh
python3 - <<'PY'
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
vals = [Decimal("100000000000.005"), Decimal("-100000000000"),
        Decimal("0.005"), Decimal("78521752562.12")]
for p in (14, 40):
    with localcontext() as c:
        c.prec = p
        s = Decimal(0)
        for v in vals: s += v
        print(p, s.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))
PY
```

observed output:

```
14 78521752562.12
40 78521752562.13
```

## Consequences

- A leitura classifica valor negativo como defeito, com identidade, valor
  original e posição — nunca o soma em silêncio.
- A fronteira aplica o mesmo domínio ao envelope de produtor externo, que não
  passa pela gramática do CSV.
- O contrato declara a não-negatividade como parte do domínio monetário, ao
  lado da escala — é ela que torna a precisão derivada verificável.
- As camadas herdadas do ADR 0003 via 0007 permanecem: precisão declarada
  nunca herdada, arredondamento uma vez no total, meio-para-par.
- Re-verify when: a fonte passar a publicar estornos ou ajustes negativos —
  aí a fórmula precisa do maior acumulador, não do total.
