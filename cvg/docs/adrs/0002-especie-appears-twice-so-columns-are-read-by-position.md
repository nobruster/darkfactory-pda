---
adr: "0002"
status: accepted
date: 2026-09-21
ground: brownfield
converge_pass: 2
spec_ref: "R-2"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0002 — especie appears twice, so columns are read by position

## Context

Um planejador que lesse "leia a coluna Espécie" escolheria leitura por nome —
é o que toda biblioteca faz por padrão, e é o que o script atual faz.

O cabeçalho desta fonte traz **`Espécie` duas vezes**, nas posições 12 e 13.
Leitura por nome fica com uma das duas e **descarta a outra em silêncio** —
sem erro, sem aviso, com o total continuando a bater.

O script em `docs/legado/` já tropeçou nisso: ele renomeia a segunda
ocorrência para `Espécie_1`, o que resolve o conflito de nomes mas não decide
**qual das duas é a que importa**.

## Decision

Toda leitura desta fonte é **posicional**, por índice declarado no contrato.
Ler por nome de cabeçalho é proibido.

O layout medido da competência 2026-01:

| Índice | Coluna |
|---|---|
| 0–8 | Despacho, Sexo., Clientela, Tipo Benefício, UF, Meio pagamento, Banco, Mun Pagto, Mun Resid |
| **9** | **Vl Líquido** — a coluna monetária |
| 10–11 | Ramo Atividade, Dt início validade |
| **12** | **Espécie** |
| **13** | **Espécie** (duplicada) |

## Rejected reading

**Renomear a duplicata e ler por nome**, como o script atual faz
(`Espécie` / `Espécie_1`).

Descartado porque a renomeação é por ordem de aparição, não por significado:
nada no código diz qual das duas carrega o dado que importa. Se a fonte
inverter a ordem das colunas numa competência futura, a renomeação continua
funcionando e passa a ler a coluna errada — **sem que nada acuse**, porque o
nome ainda existe e o valor ainda é um valor.

Posição declarada no contrato falha alto: se a ordem mudar, o gate de layout
acusa antes de qualquer leitura.

## Evidence

Cabeçalho lido direto da fonte congelada:

```sh
python3 -c "
import csv
with open('_raw/D.SDA.PDA.003.EMI.202601.csv', encoding='latin-1', newline='') as f:
    cab = next(csv.reader(f, delimiter=';'))
for i, c in enumerate(cab):
    print(i, c)
"
```

observed output (trecho):

```
 9 Vl Líquido
10 Ramo Atividade
11 Dt início validade
12 Espécie
13 Espécie
```

14 colunas no total, com `Espécie` em duas delas.

O formato do valor também foi medido: `'        1.621,00'` — ponto como
separador de milhar, vírgula decimal, com espaços à esquerda.

## Consequences

- O contrato declara o índice de cada coluna consumida. Mudança de ordem na
  fonte é divergência de layout, não de dado, e bloqueia antes da leitura.
- O valor monetário é convertido removendo o separador de milhar e trocando a
  vírgula por ponto, para `Decimal` — **nunca `float`**, que perderia o
  centavo antes de qualquer soma.
- ⚠️ **As duas colunas `Espécie` são fatos distintos até prova em contrário.**
  Qual delas carrega o código e qual o nome é pergunta aberta para o dono da
  fonte; até lá, ambas são preservadas.
- Re-verify when: a fonte publicar uma competência com número de colunas
  diferente, ou o cabeçalho mudar de ordem.
