---
adr: "0006"
status: accepted
date: 2026-09-17
ground: brownfield
converge_pass: 2
spec_ref: "R-3"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0006 — decimal context precision is declared, not inherited

## Context

Os ADRs [0001](0001-money-rounds-half-to-even-at-two-decimals.md) e
[0004](0004-rounding-happens-once-on-the-final-total-not-per-field.md) fixaram
a **regra** e a **granularidade** do arredondamento. Faltava a **precisão do
contexto** — e ela decide antes dos dois.

Decimal não é exato por si: a soma respeita a precisão do contexto corrente.
Num contexto com `prec=6`, um centavo somado a dez mil desaparece **antes** de
qualquer quantização:

| | `10000.00 + 0.01` |
|---|---|
| `prec=6` | **10000.0** — o centavo sumiu |
| `prec=28` (padrão) | 10000.01 |

E quantizar depois **não recupera**: `10000.0` quantizado a duas casas dá
`10000.00`, não `10000.01`. A perda é anterior.

Levantado pelo adversário cross-family no Pass 4 (objeção C31, 2026-09-17).

## Decision

O contexto decimal usado no caminho de decisão **é declarado explicitamente**,
com precisão suficiente para o domínio, e nunca herdado do processo.

Para a competência do INSS — 41,7 milhões de linhas somando ~7,9 × 10¹⁰ — a
soma precisa de 12 dígitos inteiros mais 2 decimais. A precisão declarada é
**28** (o padrão do Python), escolhida por folga, não por herança: um contexto
menor perde, e um maior não custa.

A implementação roda a agregação dentro de um contexto próprio
(`localcontext()`), não depende do global, e um teste força `prec=6` para
provar que a perda **é detectada**.

## Rejected reading

**Confiar no padrão da linguagem (`prec=28`).** É o que a maioria dos
programas faz, e funcionaria — o padrão do Python é suficiente para este
domínio.

Descartado pelo mesmo motivo do ADR 0001: herdar o default é como um erro
estruturalmente verde entra. O contexto decimal é **global e mutável** —
qualquer biblioteca importada pode alterá-lo com `getcontext().prec = ...`, e
o agregador passaria a perder centavos sem que uma linha do seu código
mudasse. Um teste que rode no padrão nunca acusaria.

## Evidence

Verificado nesta máquina:

```sh
python3 -c "
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
with localcontext() as ctx:
    ctx.prec = 6
    perdido = Decimal('10000.00') + Decimal('0.01')
print('prec=6 :', perdido)
print('prec=28:', Decimal('10000.00') + Decimal('0.01'))
print('quantize do perdido:', perdido.quantize(Decimal('0.01'), ROUND_HALF_EVEN))
"
```

observed output:

```
prec=6 : 10000.0
prec=28: 10000.01
quantize do perdido: 10000.00
```

A terceira linha é a que importa: arredondar depois não desfaz a perda.

## Consequences

- A agregação entra num `localcontext()` com precisão declarada. Depender do
  contexto global é defeito, ainda que o total feche no ambiente de teste.
- Um teste força `prec=6` e **exige** que a soma acuse — seja recusando, seja
  divergindo da âncora. Um agregador que passe nesse teste não perde centavo
  por contexto.
- ⚠️ Vale para a **medição da âncora** também. Se ela foi medida sob um
  contexto restrito, o número âncora já nasce errado — e a comparação
  confirmaria o erro em vez de acusá-lo.
- Este ADR **completa** o 0001 (regra) e o 0004 (granularidade): precisão →
  granularidade → regra, nessa ordem de precedência.
- Re-verify when: o domínio monetário crescer em ordem de grandeza, ou a
  implementação mudar de linguagem — a armadilha existe em qualquer decimal
  com contexto.
