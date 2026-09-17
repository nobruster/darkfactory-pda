# BRD — Exemplo: fábrica de dados a partir de arquivo mensal

> **Este é um EXEMPLO de andaime, não um pedido real.** Serve para provar que
> o Pass 0 funciona e para copiar ao abrir uma fábrica nova. O sign-off abaixo
> é fictício — substitua pelo dono de verdade antes de usar em produção.

## Executive summary
Um arquivo mensal é conferido à mão antes de virar relatório, e ninguém
consegue provar depois que o número publicado estava certo.

## Problem
A conferência manual de cada competência leva 6 horas (measured) e já deixou
passar uma divergência de R$ 0,01 por linha em 41.000 linhas (measured), que
só apareceu 3 meses depois. O retrabalho custou cerca de R$ 8.000 (estimated)
em horas de analista e uma republicação.

## Goals
- KPI-1 — tempo de conferência: 6 horas → menos de 10 minutos.
- KPI-2 — divergência não classificada publicada: hoje desconhecida → zero.

## Scope
**In:**
- um pipeline que lê o arquivo da competência e produz o agregado
- um juiz que compara o agregado contra uma âncora medida na fonte
- pacote de evidência por execução, com o veredito e os números

**Out:**
- corrigir defeitos da fonte — a fábrica classifica, nunca corrige
- substituir o sistema atual; ele continua rodando em paralelo
- painel ou interface visual

## Definition of success
Uma competência fecha sozinha, com veredito verde explicado por evidência, e
uma divergência de um centavo introduzida de propósito é **recusada** pelo
juiz antes de qualquer publicação.

## Stakeholders
- Bruno Nunes — owner and decider (desempata).

## Risks
- A âncora ser estimada em vez de medida na fonte. Bloqueante: sem âncora
  medida, o contrato nasce `NAO_MEDIDO` e a fábrica recusa construir.
- O juiz nunca reprovar, e ninguém perceber que ele está cego. Mitigado por
  testes que exigem que ele **acuse** um centavo alterado.

## Constraints
- Dinheiro em Decimal, nunca float — o juiz recusa float em campo monetário.
- O arquivo original fica imutável (chmod 444 + sha256); nada reescreve a
  fonte.
- Sem parâmetro de tolerância em lugar nenhum.

## Open questions
- question: qual competência do passado será a primeira âncora, e quem do
  negócio confirma que aquele número foi conferido e fechado
  owner: Bruno Nunes
- question: confirmar as 6 horas de conferência manual (measured) com quem
  executa hoje
  owner: Bruno Nunes

## Source
Escrito a partir da doutrina em `AGENTS.md` e do caso real do
`darkfactory-inss`, onde o vale de dezembro (−2,38%) permanece `UNRESOLVED`
porque nenhum gate compara competências vizinhas.

## Do-nothing test
Não fazer nada mantém as 6 horas por competência e, pior, mantém a
impossibilidade de provar depois que um número publicado estava certo. O
incidente de R$ 0,01 por linha levou 3 meses para aparecer; sem evidência por
execução, o próximo também levará.

## Sign-off
- Owner/decider: Bruno Nunes — verdict: **approved — canonical**
- Date: 2026-09-17
