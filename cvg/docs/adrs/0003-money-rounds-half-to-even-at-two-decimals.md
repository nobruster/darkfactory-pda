---
adr: "0003"
status: accepted
date: 2026-09-21
ground: brownfield
converge_pass: 2
spec_ref: "R-3"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0003 — money rounds half to even at two decimals

## Context

`Vl Líquido` chega da fonte como texto — `'        1.621,00'` (medido), ponto
como separador de milhar e vírgula decimal. Converter e somar 41,5 milhões
desses valores envolve três decisões que, deixadas implícitas, produzem
resultados diferentes a partir do mesmo dado:

| Decisão | Se ficar implícita |
|---|---|
| **precisão** do contexto decimal | o centavo some **antes** do arredondamento |
| **granularidade** — quando arredondar | por campo ≠ no total |
| **regra** — para onde vai o empate | meio-para-par ≠ meio-para-cima |

As três são de contrato, não de implementação. Herdar o default da linguagem
é como um erro estruturalmente verde entra: o código está certo, o total
fecha, e ninguém consegue dizer por que está errado.

## Decision

As três, em ordem de precedência:

1. **Precisão declarada**, nunca herdada. O contexto decimal é aberto
   explicitamente (`localcontext`), com precisão suficiente para o domínio —
   41,5 milhões de linhas somando ~7,9 × 10¹⁰ precisam de 12 dígitos
   inteiros mais 2 decimais.
2. **Arredonda uma vez, sobre o total final.** Valores de entrada trafegam
   com a precisão que a origem publicou; a soma é exata; a quantização a 2
   casas ocorre apenas no número comparado com a âncora.
3. **Meio-para-par** (HALF_EVEN), 2 casas.

Nenhum valor monetário existe como `float` em ponto algum. Um float recebido
na entrada é **recusado**, nunca convertido.

## Rejected reading

**Meio-para-cima** (HALF_UP), mais intuitivo para quem lê o número e comum em
sistemas legados.

Descartado pelo viés acumulado: meio-para-cima empurra **todo** empate na
mesma direção. Em 41,5 milhões de linhas isso deixa de ser arredondamento e
vira tendência sistemática, sempre a favor do mesmo lado. Meio-para-par
distribui os empates e é o comportamento do IEEE 754 (*roundTiesToEven*).

Também descartado: **arredondar cada campo na entrada**. Cada arredondamento
é uma perda, e elas somam — a diferença aparece já com dois valores.

## Evidence

As duas regras divergem no empate exato — verificado nesta máquina:

```sh
python3 -c "
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
C = Decimal('0.01')
for v in ('2.345', '2.355', '2.365'):
    d = Decimal(v)
    print(v, d.quantize(C, ROUND_HALF_EVEN), d.quantize(C, ROUND_HALF_UP))
"
```

observed output:

```
2.345  2.34  2.35
2.355  2.36  2.36
2.365  2.36  2.37
```

Dois dos três empates divergem em um centavo. A âncora
([ADR 0001](0001-the-2026-01-anchor-is-41572553-rows-summing-78521752562-12.md))
foi medida com `prec=40` e soma exata, sem quantização intermediária — esta
decisão confirma que a comparação é legítima.

## Consequences

- A agregação entra num contexto com precisão declarada, não quantiza valores
  de entrada nem somas parciais, e arredonda uma vez no fim.
- Um teste força precisão baixa e **exige** que a soma acuse a perda; outro
  compara as duas regras de arredondamento e exige veredito diferente.
- ⚠️ **Se a fonte arredondar meio-para-cima**, haverá divergência sistemática
  nos empates. Isso é `CONFIRMED_SOURCE_DEFECT` — classificado e preservado.
  **Não alinhe a fábrica ao erro da origem.**
- Re-verify when: a moeda mudar de número de casas decimais, ou o volume
  crescer em ordem de grandeza.
