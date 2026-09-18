---
adr: "0004"
status: accepted
date: 2026-09-17
ground: brownfield
converge_pass: 2
spec_ref: "R-3, R-1"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0004 — rounding happens once on the final total, not per field

## Context

O [ADR 0001](0001-money-rounds-half-to-even-at-two-decimals.md) fixou a
**regra** de arredondamento (meio-para-par, 2 casas), mas não a
**granularidade** — quantas vezes ela é aplicada no caminho até o total.

Um planejador do Pass 3 que lesse só o 0001 escolheria qualquer uma das duas,
e elas divergem:

| | `2,345 + 2,345` |
|---|---|
| arredondar **cada campo**, depois somar | **4,68** |
| somar exato, arredondar **só o total** | **4,69** |

Ambos são HALF_EVEN. Ambos seguem o ADR 0001. O resultado difere em um
centavo — e com três valores iguais o desvio já é de dois centavos.

Levantado pelo adversário cross-family no Pass 4 (objeção C12, 2026-09-17),
que notou a lacuna entre *"somar exato e arredondar uma vez no final"* no
plano e *"todo campo monetário é arredondado"* no ADR 0001.

## Decision

O arredondamento acontece **uma vez, sobre o total final**. Os valores de
entrada trafegam com a precisão que a origem publicou, a soma é exata, e a
quantização a 2 casas ocorre apenas no número que será comparado com a âncora.

A mesma granularidade vale para a **medição da âncora** (R-1). Medir a âncora
por campo e o agregado só no total faria a comparação medir a granularidade,
não o dado — e a diferença apareceria como divergência inexplicada.

Arredondar somas parciais também está excluído: é o caso intermediário, e
acumula erro linha a linha.

## Rejected reading

**Arredondar cada campo na entrada.** É o que muitos sistemas de origem fazem,
e tem a vantagem de que todo valor intermediário já é apresentável.

Descartado porque cada arredondamento é uma perda, e elas somam: com `2,345`
repetido, por campo dá 4,68 contra 4,69, e com três valores 7,02 contra 7,04.
Num volume de 41,7 milhões de linhas o desvio deixa de ser arredondamento e
vira diferença estrutural — sem que nenhum gate acuse, porque os dois lados
"seguem o ADR 0001".

## Evidence

Verificado nesta máquina:

```sh
python3 -c "
from decimal import Decimal, ROUND_HALF_EVEN
C=Decimal('0.01'); vals=[Decimal('2.345'), Decimal('2.345')]
print('por campo :', sum(v.quantize(C, ROUND_HALF_EVEN) for v in vals))
print('so total  :', sum(vals).quantize(C, ROUND_HALF_EVEN))
"
```

observed output:

```
por campo : 4.68
so total  : 4.69
```

Com três ocorrências de `2,345`: 7,02 por campo contra 7,04 só no total — o
desvio dobra.

## Consequences

- A agregação **não quantiza** valores de entrada nem somas parciais. Um teste
  exige que arredondar por campo produza total diferente do esperado e
  **falhe**.
- A âncora de 2026-03 do [ADR 0002](0002-the-first-anchor-is-competencia-2026-03-measured-at-source.md)
  foi medida somando a fonte; esta decisão confirma que a comparação é
  legítima. ⚠️ **Se a medição tiver arredondado por campo**, a divergência
  aparecerá — e é `CONTRACT_AMBIGUITY` até alguém remedir, não defeito do
  pipeline.
- Este ADR **complementa** o 0001, não o substitui: a regra continua
  meio-para-par; o que se acrescenta é onde ela se aplica.
- Re-verify when: a origem declarar que publica valores já arredondados por
  campo, ou o domínio monetário mudar de número de casas.
