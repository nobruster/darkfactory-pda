---
adr: "0002"
status: accepted
date: 2026-09-17
ground: brownfield
converge_pass: 2
spec_ref: "R-1"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0002 — the first anchor is competencia 2026-03 measured at source

## Context

R-1 exige que nenhuma publicação ocorra sem âncora medida na origem. Sem ela
o gate compara contra nada e publica `ACEITO` sem prova.

Uma âncora tem três partes, e faltar qualquer uma invalida as outras duas: a
competência, o número, e quem aprovou. Um número sem dono é indistinguível de
um palpite.

Resolve o GAP-001 de
[`../tech-spec/tech-spec-exemplo-fabrica.md`](../tech-spec/tech-spec-exemplo-fabrica.md).

## Decision

A primeira âncora **é** a competência **2026-03**, medida direto na fonte em
2026-09-16:

| Campo | Valor |
|---|---|
| `count_linhas` | 41.719.140 |
| `sum_vl_liquido` | `78771556568.72` |
| `min_vl_liquido` | `0.00` |
| `max_vl_liquido` | `60588.24` |
| `linhas_invalidas` | 0 |

Aprovada por **Bruno Nunes**. O valor trafega como decimal exato, nunca
float, e compara com arredondamento meio-para-par
([ADR 0001](0001-money-rounds-half-to-even-at-two-decimals.md)).

A medição é **independente do pipeline**: varre a fonte e soma, sem ler
nenhum artefato produzido pela fábrica.

## Rejected reading

**A competência 2026-08 (o mês fechado anterior), com este mesmo total.**

Foi a primeira leitura registrada nesta descida — o aprovador indicou "mês
passado" e o valor R$ 78.771.556.568,72. As duas coisas não batem: esse total
pertence a 2026-03.

Matou-a o contrato do `darkfactory-inss`, que traz as seis competências
ancoradas e atribui esse número a 2026-03 com evidência datada. **Não existe
âncora medida para 2026-08** — adotá-la significaria comparar a fábrica
contra um número que nunca foi medido naquela competência.

Também descartado: **gerar a âncora rodando o pipeline**. Seria o pipeline
conferindo a si mesmo, e qualquer defeito comum às duas execuções ficaria
invisível. Foi o defeito da objeção #28 — 82 milhões de linhas publicadas
sem nunca terem sido conferidas contra a fonte.

## Evidence

Medida por `totais_controle.py`, que varre a fonte direto (~46s), sem tocar
em artefato do pipeline:

```sh
# no darkfactory-inss, mede a competência direto da fonte
make ancora COMP=2026-03
# equivale a: python scripts/totais_controle.py --competencia 2026-03
```

observed output (`darkfactory-inss/evidence/_totais-202603.json`):

```json
{
  "competencia": "2026-03",
  "count_linhas": 41719140,
  "linhas_invalidas": 0,
  "sum_vl_liquido": "78771556568.72",
  "min_vl_liquido": "0.00",
  "max_vl_liquido": "60588.24",
  "segundos": 46
}
```

Registrada no contrato em
`darkfactory-inss/contracts/layout.yaml:146-153`, com `medido_em:
"2026-09-16"` e ponteiro para a evidência.

## Consequences

- O agregado do pipeline para 2026-03 é comparado contra estes cinco valores.
  Divergência em qualquer um deles bloqueia, e recebe classificação nomeada.
- A âncora é **por competência**. Faixa medida numa competência não vira regra
  para outra: o máximo de 2026-01 é 3× o de fevereiro e março — outlier real,
  não erro (objeção #14 do `darkfactory-inss`).
- ⚠️ **Esta âncora vem de outro repositório.** Uma fábrica nova mede a sua
  própria; copiar número entre projetos é herdar um fato sem a evidência que
  o sustenta.
- ⚠️ **Nenhum gate compara competências vizinhas.** Um salto de 6% na média
  (como 2025-12 → 2026-01) passa sem que nada acuse. A fábrica vê um centavo
  errado *dentro* de uma competência e não vê isto.
- Re-verify when: a origem republicar 2026-03, ou o layout do arquivo mudar.
  Âncora revista se faz com ADR novo, nunca editando este.
