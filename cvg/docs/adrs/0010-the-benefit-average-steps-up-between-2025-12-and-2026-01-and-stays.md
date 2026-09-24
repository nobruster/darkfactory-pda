---
adr: "0010"
status: accepted
date: 2026-09-22
ground: brownfield
converge_pass: 2
spec_ref: "R-5"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0010 — the benefit average steps up between 2025-12 and 2026-01 and stays

## Context

O ADR 0001 registrou a âncora de 2026-01 e nomeou uma lacuna que a fábrica
não fecha:

> ⚠️ **Nenhum gate compara competências vizinhas.** Um salto na média passa
> sem que nada acuse — a fábrica vê um centavo errado *dentro* de uma
> competência e não vê isto.

Este ADR mede o que está nessa lacuna. Seis competências, de duas fontes
independentes: cinco do `darkfactory-inss`, medidas por outro código em outro
momento, e 2026-01 medida aqui.

## Decision

**A média por benefício dá um degrau de +6,01% entre 2025-12 e 2026-01, e
permanece no novo patamar.**

| competência | média/benefício | variação |
|---|---|---|
| 2025-10 | 1.777,54 | — |
| 2025-11 | 1.825,18 | +2,68% |
| 2025-12 | 1.781,71 | −2,38% |
| **2026-01** | **1.888,79** | **+6,01%** |
| 2026-02 | 1.889,15 | +0,02% |
| 2026-03 | 1.888,14 | −0,05% |

É **degrau, não pico**: as duas competências seguintes ficam a menos de 0,1%
do novo nível. Um pico voltaria; este não volta.

E é fenômeno da **fonte**, não da leitura: os números vêm de dois códigos
distintos, em repositórios distintos, sem compartilhar implementação.

**Nenhum limiar de recusa é declarado aqui.** Seis pontos não bastam para
dizer o que é variação normal, e escolher um número por conforto seria
inventar o gate em vez de medi-lo. O que este ADR fixa é o **fato**; o gate,
se vier, nasce de mais medição.

## Rejected reading

**Que o degrau fosse defeito de leitura em 2026-01** — a competência que esta
fábrica mede.

É a suspeita natural: a maior variação da série cai justamente na competência
que acabamos de processar, e um erro de agregação produziria exatamente isso.

O que a mata: 2026-01 foi medida **duas vezes por códigos independentes** —
`scripts/medir_ancora.py` aqui, e o `darkfactory-inss` lá — chegando ao mesmo
`78.521.752.562,12`. E 2026-02 e 2026-03, medidas só pelo outro repositório,
**confirmam o novo patamar**. Se o degrau fosse erro nosso, os meses seguintes
teriam voltado a 1.781.

O degrau precede esta fábrica e sobrevive a ela.

## Evidence

```sh
python3 scripts/medir_serie.py
```

observed output:

```
  competência         linhas  média/benefício   variação
  --------------------------------------------------------
  2025-10         41,472,336          1777.54
  2025-11         41,643,003          1825.18     +2.68%
  2025-12         41,641,943          1781.71     -2.38%
  2026-01         41,572,553          1888.79 +6.01%  <--
  2026-02         41,522,152          1889.15     +0.02%
  2026-03         41,719,140          1888.14     -0.05%

  1 variação(ões) acima de 5%:
    2026-01  +6.01%
SERIE=MEDIDA
```

A contagem de linhas **não** acompanha o degrau — varia menos de 0,6% em toda
a série, enquanto a média salta 6%. O que mudou foi o valor por benefício, não
a população.

## Consequences

- A fábrica continua julgando **por competência**, contra a própria âncora.
  Uma execução de 2026-01 devolve `ACEITO` apesar do degrau, e isso está
  correto: o total bate com o que a fonte publicou.
- O degrau fica **registrado**, não corrigido (Regra 4). Se alguém do negócio
  precisar explicá-lo, a série medida está aqui.
- Um gate de série exige mais pontos. Com seis, qualquer limiar seria
  arbitrário — e um gate arbitrário reprova o arquivo correto, que é a falha
  que esta descida encontrou quatro vezes (Regra 9).
- `scripts/medir_serie.py` roda a qualquer momento e mostra o que a fábrica
  não vê. Ele não recusa nada, por escolha declarada.
- Re-verify when: uma sétima competência for medida — aí a série tem base
  para dizer se +6% é raro ou rotineiro.
