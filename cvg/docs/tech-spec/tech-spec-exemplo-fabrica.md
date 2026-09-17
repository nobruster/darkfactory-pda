# Tech-Spec — Exemplo: fábrica de dados a partir de arquivo mensal

> **Andaime, não pedido real.** Deriva de
> [`../brd/brd-exemplo-fabrica.md`](../brd/brd-exemplo-fabrica.md). O sign-off
> é fictício — substitua pelo dono antes de usar em produção.
>
> Pass 1 fica **acima da stack**: aqui se decide *o quê* e *quanto*. Motor,
> linguagem e formato de armazenamento são decididos no Pass 3.

## Problem restated

Conferir uma competência à mão leva 6 horas (measured), e uma divergência de
R$ 0,01 por linha em 41.000 linhas (measured) passou despercebida por 3 meses,
custando cerca de R$ 8.000 (estimated) em retrabalho e uma republicação.

Resolvido significa: o agregado da competência é comparado contra um valor
medido na origem antes de publicar, toda diferença recebe uma classificação
nomeada, e a execução deixa um pacote de evidência que permite responder
meses depois por que aquele número foi aceito.

## Scope

**In scope:**
- leitura da competência e produção do agregado
- comparação do agregado contra uma âncora medida na origem
- classificação obrigatória de toda diferença encontrada
- pacote de evidência por execução, com veredito e números

**Out of scope:**
- corrigir defeitos da origem — classificar não é consertar
- substituir o sistema atual, que segue rodando em paralelo
- interface visual ou painel

## Requirements

- **R-1 (must).** Nenhuma publicação ocorre sem âncora medida na origem.
  Sem âncora, o veredito é `ACEITO_SEM_ANCORA`, nunca `ACEITO` — e
  `ACEITO_SEM_ANCORA` não autoriza publicar.
- **R-2 (must).** Toda diferença recebe exatamente uma de seis
  classificações. Diferença não classificada bloqueia a publicação.
- **R-3 (must).** Campo monetário é comparado com aritmética exata, com
  arredondamento meio-para-par (HALF_EVEN) a 2 casas decimais. Um valor em
  ponto flutuante num campo monetário é recusado na entrada, não
  arredondado. A regra é declarada no contrato e verificada por teste: o
  mesmo dado arredondado meio-para-cima produz veredito diferente, e o teste
  falha se a implementação herdar o default da linguagem.
- **R-4 (must).** Não existe parâmetro de tolerância configurável em nenhum
  ponto do caminho de decisão.
- **R-5 (must).** Uma divergência de R$ 0,01 introduzida de propósito em uma
  linha é recusada antes da publicação — provado por teste que falha se o
  juiz aceitar.
- **R-6 (must).** A conferência de uma competência completa em até 10
  minutos, medido do início da leitura ao veredito.
- **R-7 (should).** Cada execução produz um pacote de evidência que permite
  reconstruir o veredito sem reexecutar o pipeline.
- **W-1 (won't).** A origem não é alterada em nenhuma hipótese: bytes
  originais permanecem imutáveis e verificáveis por hash.

## Success metrics

| Metric | Current | Target |
|---|---|---|
| Tempo de conferência por competência | 6 horas | -> menos de 10 minutos |
| Divergência não classificada publicada | desconhecido | -> 0 |
| Tempo até detectar erro de centavo | 3 meses | -> antes da publicação |

## Data named

O arquivo mensal da competência, como a origem o publica — uma linha por
registro, com identificador do registro, valores monetários e os códigos de
classificação da própria origem. A âncora é o total medido diretamente sobre
esse arquivo, independente do pipeline, mais quem do negócio confirmou aquele
número e quando.

## Open assumptions

- Existe ao menos uma competência do passado cujo número final já foi
  conferido e fechado, utilizável como primeira âncora.
  owner: Bruno Nunes
- As 6 horas de conferência manual refletem a prática atual.
  owner: Bruno Nunes

## Gap register

```yaml
- id: GAP-001
  type: number
  severity: blocker
  question: "Qual competência do passado será a primeira âncora, e quem do negócio confirma que aquele número foi conferido e fechado?"
  blocks: "R-1 — sem âncora medida não há o que comparar"
  owner: "Bruno Nunes"
  resolution: "open"
  note: "O contrato nasce NAO_MEDIDO e a fábrica recusa construir até alguém medir a origem. Não gerar a âncora automaticamente para desbloquear."

- id: GAP-002
  type: decision
  severity: blocker
  question: "O arredondamento monetário é meio-para-par ou meio-para-cima?"
  blocks: "R-3 — a regra decide o resultado e não pode ficar implícita no código"
  owner: "Bruno Nunes"
  resolution: "RESOLVIDO 2026-09-17 por Bruno Nunes: meio-para-par (HALF_EVEN). Declarado no contrato e verificado por teste; nenhum ponto do caminho de decisão herda o default da linguagem. A registrar como ADR no Pass 2."
```

## Sign-off

- **Owner/decider:** Bruno Nunes — verdict: **pending — GAP-001 e GAP-002 abertos**
- **Date:** 2026-09-17
