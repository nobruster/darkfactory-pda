---
adr: "0005"
status: accepted
date: 2026-09-17
ground: brownfield
converge_pass: 2
spec_ref: "R-1, R-7"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0005 — no-anchor runs end as ACEITO_SEM_ANCORA, with NAO_MEDIDO as the internal cause

## Context

Dois nomes descrevem a mesma execução — a que roda sem âncora medida — e
nenhum documento dizia qual é o veredito.

| Nome | Onde aparece | O que é |
|---|---|---|
| `NAO_MEDIDO` | `AGENTS.md`, Regra 2 | o **estado do contrato**: falta âncora |
| `ACEITO_SEM_ANCORA` | tech-spec, R-1 | o **veredito da execução** |

A ambiguidade não é acadêmica: *"um consumidor implementado pela spec e outro
implementado pelo plano discordarão sobre o resultado esperado"* — objeção C19
do adversário cross-family, 2026-09-17.

Ampliar a enumeração de vereditos terminais não resolveu: aceitar os dois como
terminais deixou em aberto qual deles **é** a execução.

## Decision

Uma execução sem âncora termina com veredito **`ACEITO_SEM_ANCORA`**.
`NAO_MEDIDO` **é a causa**, registrada como campo dentro do pacote, nunca o
veredito publicado.

```
veredito : ACEITO_SEM_ANCORA      ← o que a execução vale
causa    : NAO_MEDIDO             ← por que ela vale isso
```

Os dois **não** são alternativas: são camadas distintas, e o pacote carrega as
duas. `ACEITO_SEM_ANCORA` **não autoriza publicar** — o nome diz "aceito" no
sentido de que a execução terminou, não de que o número está provado.

## Rejected reading

**`NAO_MEDIDO` como veredito publicado**, descartando `ACEITO_SEM_ANCORA`.
Seria mais direto — um nome só — e evita a leitura errada de que "aceito"
significa aprovado.

Descartado porque R-1 nomeia `ACEITO_SEM_ANCORA` como o veredito, e a
tech-spec é canônica (sign-off de 2026-09-17). Trocar o nome exigiria revisar
a spec, e o problema real não era o nome: era **faltar a relação** entre os
dois. Um vocabulário de vereditos que só existe quando há âncora deixaria a
execução sem âncora sem lugar — que é o defeito que C19 apontou.

## Evidence

Os dois nomes coexistem nos documentos canônicos, sem relação declarada:

```sh
grep -n "ACEITO_SEM_ANCORA" cvg/docs/tech-spec/tech-spec-exemplo-fabrica.md
grep -n "NAO_MEDIDO" AGENTS.md
```

observed output:

```
tech-spec R-1 : "Sem âncora, o veredito é ACEITO_SEM_ANCORA, nunca ACEITO"
AGENTS.md     : "nasce com contrato NAO_MEDIDO e recusa rodar"
```

A tech-spec fala do **veredito**; o AGENTS.md fala do **contrato**. Nenhum dos
dois define o que o pacote registra.

## Consequences

- O pacote de evidência tem **dois campos**: `veredito` e `causa`. Um pacote
  com `veredito: NAO_MEDIDO` é defeito de implementação.
- Os vereditos terminais são **quatro**, não três: `ACEITO`,
  `ACEITO_SEM_ANCORA`, `RECUSADO` (competência ancorada com divergência
  bloqueante) e `ERRO`. A recusa com âncora estava faltando — objeção C16.
- `ACEITO_SEM_ANCORA` e `RECUSADO` **não autorizam publicar**. Só `ACEITO`
  autoriza, e só com os cinco controles conferidos.
- Re-verify when: a tech-spec mudar o vocabulário de vereditos, ou surgir um
  quinto estado terminal.
