---
adr: "0016"
status: accepted
date: 2026-09-25
ground: brownfield
converge_pass: 2
spec_ref: "R-2"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0016 — the postgres loads its own files and is validated against the gold

## Context

O ADR 0015 fixou que todo arquivo de fonte passa por landing, Bronze, Silver e
Gold, e escreveu que "o consumo lê da Gold". A referência do INSS já está em
produção pelas quatro camadas (`gold/pda/referencia/dim_especie` e
`dim_termo`, v1, 2026-09-25).

Ao ver o Postgres (`pda-postgres`, schema `ontologia`), o dono decidiu:
*"deixa o postgres lendo os próprios arquivos, validar contra a gold"*.

## Decision

O Postgres **carrega pelos próprios arquivos** — os dois `.xlsx` do INSS, com
o sha256 conferido contra o aprovado na ontologia — e, dentro da mesma
transação, **antes do commit**, é **validado contra a Gold**: `especie` ×
`dim_especie` da competência e `termo` × `dim_termo` do sha256 aprovado,
linha a linha. Divergência desfaz a transação e a carga anterior continua
visível. As versões da Gold conferidas ficam registradas no próprio schema.

Isso **refina** o ADR 0015 no ponto do consumo; não o substitui: todo arquivo
continua passando pelas quatro camadas, e o Postgres é um **segundo caminho,
independente**, que só publica o que concorda com a Gold.

## Rejected reading

**Postgres lido da Gold.** Era a leitura do 0015. Um Postgres que copia a
Gold concorda com ela mesmo quando ela está errada. Com a extração
independente — o parser da ontologia, que não é o da Bronze — um erro num dos
dois caminhos aparece como divergência. É a doutrina do ADR 0005 (o juiz não
usa o motor que julga) aplicada ao consumo.

**Parear as duas dimensões da Gold por `id_execucao`.** Objeção C1 da R4 da
referência. Desnecessário: cada dimensão tem de bater, linha a linha, com a
carga independente; um par misturado de execuções diferentes divergiria.

## Consequences

- Receita B: `projetar_validado` em `src/medalhao/projecao_postgres.py`, ao
  lado da `projetar_ontologia` existente, que fica até a limpeza.
- Receita C (limpeza): retirar os caminhos antigos por lista nomeada e deixar
  o YAML só com conceitos.
