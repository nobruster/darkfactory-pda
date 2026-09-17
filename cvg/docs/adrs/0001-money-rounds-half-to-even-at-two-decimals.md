---
adr: "0001"
status: accepted
date: 2026-09-17
ground: brownfield
converge_pass: 2
spec_ref: "R-3"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0001 — money rounds half to even at two decimals

## Context

Um planejador do Pass 3 que lesse apenas "aritmética exata" (R-3) escolheria o
arredondamento pelo default da linguagem — e os defaults divergem. `round()`
do Python é meio-para-par; `ROUND()` da maioria dos bancos é meio-para-cima.

A escolha só aparece no empate exato, e some dentro do total:

| Valor | meio-para-cima | meio-para-par |
|---|---|---|
| `2,345` | 2,35 | **2,34** |
| `2,355` | 2,36 | **2,36** |

Um centavo por empate. Em 41.000 linhas, uma diferença que o agregado esconde
e que nenhum gate acusa se a regra não estiver fixada aqui.

Resolve o GAP-002 de
[`../tech-spec/tech-spec-exemplo-fabrica.md`](../tech-spec/tech-spec-exemplo-fabrica.md).

## Decision

Todo campo monetário no caminho de decisão **é** arredondado meio-para-par
(HALF_EVEN) a 2 casas decimais. Nenhum valor monetário existe como ponto
flutuante: a representação é decimal exata, e um float recebido na entrada é
recusado, nunca convertido.

A regra vale igualmente para o dado do pipeline e para a âncora medida na
origem. Medir a âncora com outra regra faz a comparação medir o
arredondamento, não o dado.

## Rejected reading

**Meio-para-cima (HALF_UP)**, por ser o mais intuitivo para quem lê o número e
o mais comum em sistemas legados.

Descartado pelo viés acumulado: meio-para-cima empurra **todo** empate na
mesma direção. Num volume grande isso deixa de ser arredondamento e vira
tendência sistemática, sempre a favor do mesmo lado. Meio-para-par distribui
os empates e é o comportamento do IEEE 754 (*roundTiesToEven*), o que reduz
divergência contra sistemas financeiros de origem.

## Evidence

Os dois modos produzem resultados diferentes no mesmo dado — verificado nesta
máquina:

```sh
python3 -c "
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
for v in ('2.345','2.355','2.365'):
    d=Decimal(v)
    print(v,
          d.quantize(Decimal('0.01'), ROUND_HALF_EVEN),
          d.quantize(Decimal('0.01'), ROUND_HALF_UP))
"
```

observed output:

```
2.345 2.34 2.35
2.355 2.36 2.36
2.365 2.36 2.37
```

Dois dos três empates divergem em um centavo. Um total construído sobre
41.000 linhas absorve essa diferença sem que nada acuse.

## Consequences

- Planos do Pass 3 declaram a regra de arredondamento explicitamente. Herdar
  o default da linguagem ou do banco é defeito, ainda que o total feche.
- A âncora do GAP-001 é medida com esta mesma regra. Se a origem publicar com
  outra, a divergência nos empates é classificada
  `CONFIRMED_SOURCE_DEFECT` — **a fábrica não se alinha ao erro da origem**.
- O juiz carrega um teste que compara os dois modos e **falha** se a
  implementação aceitar meio-para-cima onde o contrato diz meio-para-par. Um
  teste que nunca falhou não prova nada.
- Re-verify when: a origem declarar mudança na sua própria regra de
  arredondamento, ou o domínio monetário mudar (moeda com número diferente de
  casas decimais).
