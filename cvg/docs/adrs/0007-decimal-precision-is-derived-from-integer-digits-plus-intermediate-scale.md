---
adr: "0007"
status: accepted
date: 2026-09-21
ground: brownfield
converge_pass: 2
spec_ref: "R-4"
supersedes: "0003"
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0007 — decimal precision is derived from integer digits plus intermediate scale

## Context

O ADR 0003 fixou três camadas — precisão declarada, arredondamento único no
total, meio-para-par — e as três continuam valendo. O que este ADR corrige é
**um número e a conta que o produziu**.

O 0003 escreveu: *"41,5 milhões de linhas somando ~7,9 × 10¹⁰ precisam de 12
dígitos inteiros mais 2 decimais"*. A âncora medida é 78.521.752.562,12, que
tem **11** dígitos inteiros, não 12.

Um adversário cross-family apontou a divergência quando o plano do Pass 3
declarou "mínimo de 13 dígitos significativos" — número correto para
representar o total, e que contradizia a cláusula do ADR sem que nenhum
registro dissesse qual das duas valia. O mesmo plano manda validar o contrato
**contra o ADR**, então dois implementadores poderiam aceitar e recusar
`prec=13` alegando conformidade.

## Decision

**A precisão suficiente não é uma constante: é derivada.**

Ela é o número de dígitos inteiros do maior total esperado somado à maior
escala decimal que os valores intermediários carregam — não à escala do
resultado.

Para esta âncora: 11 dígitos inteiros + 3 casas de intermediário = **14**.

Representar o total exige 13. Somá-lo exige 14, porque a perda acontece
**durante** a soma, quando um intermediário de três casas encontra um
acumulador de onze dígitos inteiros. Por isso a precisão entra no contrato
como valor derivado da âncora e da escala declarada, e é conferida por
suficiência no carregamento — nunca por estar presente.

O número 14 do ADR 0003 estava certo. A conta que o justificava, não.

## Rejected reading

**Que 13 bastasse**, por ser quanto o total ancorado ocupa.

Foi a leitura que o plano do Pass 3 adotou, e ela é plausível: 13 dígitos
representam 78.521.752.562,12 exatamente, e `prec=12` perde o último centavo
de forma visível.

O contraexemplo executado a mata. Somando 78521752562.12 + 0,005 + 0,005:

| precisão | soma | quantizado |
|---|---|---|
| 13 | 78521752562.12 | 78521752562.12 |
| 14 | 78521752562.130 | **78521752562.13** |

Em `prec=13` o centavo some **antes** da quantização — exatamente a falha que
o ADR 0003 nomeou na sua primeira camada, agora atingindo a precisão que
parecia suficiente. Suficiência para representar não é suficiência para somar.

## Evidence

```sh
python3 - <<'PY'
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
vals = [Decimal("78521752562.12"), Decimal("0.005"), Decimal("0.005")]
for p in (12, 13, 14, 20):
    with localcontext() as c:
        c.prec = p
        s = Decimal(0)
        for v in vals: s += v
        print(p, s, s.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))
PY
```

observed output:

```
12 78521752562.1 78521752562.10
13 78521752562.12 78521752562.12
14 78521752562.130 78521752562.13
20 78521752562.130 78521752562.13
```

E a contagem de dígitos que o ADR 0003 errou:

```sh
python3 -c "from decimal import Decimal; t=Decimal('78521752562.12'); \
  print(len(str(int(t))), 'inteiros +2 =', len(str(int(t)))+2)"
```

observed output:

```
11 inteiros +2 = 13
```

## Consequences

- O contrato carrega a precisão como valor **derivado** — dígitos inteiros da
  âncora mais a escala máxima declarada para intermediários — e o carregador
  recusa precisão insuficiente, em vez de deixá-la aparecer na agregação.
- Planos do Pass 3 citam este ADR, não a cláusula de 12+2 do 0003.
- As três camadas do ADR 0003 permanecem: precisão declarada nunca herdada,
  arredondamento uma vez no total, meio-para-par. Só o número e sua derivação
  mudaram.
- A escala dos intermediários é uma **declaração do contrato**, não um
  padrão: se uma fonte futura publicar quatro casas, a precisão derivada sobe
  junto, sem novo ADR.
- Re-verify when: a âncora mudar de ordem de grandeza, ou a fonte passar a
  publicar valores com mais casas decimais.
