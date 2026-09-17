---
adr: "0002"
status: proposed
date: 2026-09-17
ground: greenfield
converge_pass: 2
spec_ref: "R-1"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0002 — the first anchor is competencia 2026-08 approved by Bruno Nunes

## Context

R-1 exige que nenhuma publicação ocorra sem âncora medida na origem. A âncora
é o número contra o qual o agregado do pipeline é comparado — sem ela, o gate
compara contra nada e publica `ACEITO` sem prova.

Uma âncora tem três partes, e falta qualquer uma invalida as outras duas:

| Parte | Por quê |
|---|---|
| A competência | qual recorte de tempo foi conferido |
| O número | o total que se sabe correto |
| Quem aprovou | sem dono, o número é indistinguível de um palpite |

Resolve o GAP-001 de
[`../tech-spec/tech-spec-exemplo-fabrica.md`](../tech-spec/tech-spec-exemplo-fabrica.md).

## Decision

A primeira âncora **é** a competência **2026-08** — o mês fechado anterior —
com total declarado de **R$ 78.771.556.568,72**, aprovada por **Bruno Nunes**
em 2026-09-17.

O valor trafega no contrato como decimal exato `78771556568.72`, nunca float,
e é comparado com arredondamento meio-para-par conforme
[ADR 0001](0001-money-rounds-half-to-even-at-two-decimals.md).

## Rejected reading

**Gerar a âncora rodando o pipeline sobre a competência.** Seria mais rápido e
produziria um número com aparência idêntica.

Descartado porque é o pipeline conferindo a si mesmo: o gate passaria a
comparar o resultado contra o próprio resultado, e qualquer defeito comum às
duas execuções ficaria invisível. Foi exatamente o defeito da objeção #28 no
`darkfactory-inss` — os gates se desligavam quando a competência não era a
declarada, e o packet seguia dizendo `ACEITO`: **82 milhões de linhas
publicadas sem nunca terem sido conferidas contra a fonte**. Os dados estavam
certos; faltava a prova.

## Evidence

Declarado pelo aprovador em 2026-09-17, nesta sessão:

```sh
# a declaração, como registrada
echo "competencia: 2026-08"
echo "total declarado: 78771556568.72"
echo "aprovado por: Bruno Nunes"
```

observed output: os três valores acima, conforme informados.

⚠️ **Esta evidência é uma declaração, não uma medição reproduzível.** Não há
comando que releia a origem e reproduza o número, porque **nenhuma fonte está
conectada** (`_raw/` vazio — ver [`0000-context.md`](0000-context.md)). Por
isso o status deste ADR é `proposed`, não `accepted`.

Para promover a `accepted`, a evidência precisa virar um comando que meça o
ZIP/arquivo da competência 2026-08 direto na origem e imprima o total,
independente do pipeline.

## Consequences

- Enquanto este ADR estiver `proposed`, `cvg structure --final` **reprova** —
  ele exige todo ADR em `accepted`. Isso é o desejado: a âncora declarada não
  é a âncora medida.
- ⚠️ **Divergência a resolver antes de aceitar.** O valor
  R$ 78.771.556.568,72 aparece no `darkfactory-inss` como o total da
  competência **2026-03**, não 2026-08 (ver o CLAUDE.md daquele projeto).
  Uma das duas leituras está errada, e qual delas muda o que a fábrica
  considera verdade. **Medir antes de aceitar** — não escolher a mais
  conveniente.
- O contrato permanece `NAO_MEDIDO` até a medição existir. A fábrica recusa
  construir, e isso é o primeiro gate funcionando, não uma pendência.
- Re-verify when: a origem republicar a competência 2026-08, ou o aprovador
  revisar o total. Âncora revista se faz com ADR novo, nunca editando este.
