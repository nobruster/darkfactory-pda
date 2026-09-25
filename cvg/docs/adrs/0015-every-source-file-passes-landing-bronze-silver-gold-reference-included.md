---
adr: "0015"
status: accepted
date: 2026-09-24
ground: brownfield
converge_pass: 2
spec_ref: "R-2"
supersedes: "0014"
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0015 — every source file passes landing, bronze, silver and gold — reference included

## Context

O ADR 0014 fez da ontologia versionada a fonte da verdade e tratou a Delta
`especie` e o Postgres como **projeções** dela. Na prática, os 65 nomes
oficiais do dicionário do INSS foram **copiados para o YAML** e dali gravados
direto na Silver. A `especie` v1 registra `versao_silver: 5` e o sha256 da
ontologia — e nada mais: os bytes do dicionário, que estão em `_raw/` desde
`51cc9f0`, **nunca entraram no lago**.

O dono apontou, em 2026-09-24: *"o arquivo de especie foi gravado direto na
silver"* — e fixou a regra: *"todos os arquivos sempre deverão passar pela
landing, bronze, silver e gold"*.

## Decision

**Todo arquivo de fonte passa por landing → Bronze → Silver → Gold**, cada
camada lendo só da anterior, e o consumo lê da Gold. Não há exceção para
arquivo de referência, dicionário, glossário ou tabela auxiliar.

| Camada | O que guarda | Lê de |
|---|---|---|
| Landing | os **bytes** como vieram, com `_PROCEDENCIA.json` (sha256, tamanho) | `_raw/` — a única camada que lê `_raw/` |
| Bronze | as **linhas** como vieram, sem filtro nem trim | o landing |
| Silver | o dado **conformado** | a Bronze |
| Gold | o que se **serve** | a Silver |
| Consumo (Postgres, BI, agentes) | — | a Gold |

Cada commit registra a versão (ou a partição e a prova) da camada que leu.

A ontologia versionada **fica só com conceitos**: a ligação coluna → termo
por posição, a referência aos grupos do contrato, e o sha256 **aprovado** de
cada arquivo de referência. Nomes e descrições são **dado da fonte** e vêm do
lago. Um dicionário novo do INSS, com outro sha256, entra no landing e na
Bronze, mas a Silver o recusa (`DICIONARIO_NAO_APROVADO`) até o dono aprovar
o novo sha256 — a proteção que o ADR 0014 dava continua, agora no ponto certo.

## Rejected reading

**Referência como configuração.** É o atalho do ADR 0014: um arquivo pequeno,
estável, "que não é dado". Rejeitado pelo dono — e com razão: sem landing não
há prova de qual versão do dicionário gerou o nome publicado, e sem Bronze
não há o registro das linhas como vieram (o dicionário tem 69 linhas no XML,
duas sem valor; o glossário, 24, dez sem valor — o YAML não guardava nenhuma
dessas).

**Postgres lido da Silver.** Considerado; o dono fixou a Gold como camada de
serviço para todo consumo.

## Evidence

- Linhagem medida em 2026-09-24 nos commits Delta vigentes: Silver v5 ← Bronze
  v4; Gold v3 ← Silver v5; `especie` v1 ← Silver v5 **e o YAML** — sem Bronze
  nem landing do dicionário.
- A Bronze dos benefícios registra só o `hash_procedencia` do CSV, não a
  partição do landing lida — lacuna fechada pela mesma receita.

## Consequences

- Receita A (`cvg/swimlanes/referencia-recipe.yaml`): a Bronze nomeia o
  landing; landing, Bronze, Silver (glossário, `especie`) e Gold
  (`dim_especie`, `dim_termo`) da referência.
- Receita B: o Postgres passa a ler da Gold; o YAML perde os nomes e as
  descrições.
- A `especie` v1 em produção fica até a versão lida da Bronze substituí-la
  pela cadeia; o Delta guarda o histórico.
