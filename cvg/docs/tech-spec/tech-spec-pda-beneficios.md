# Tech-Spec — Benefícios emitidos do PDA, por competência

> Deriva de [`../brd/brd-pda-beneficios.md`](../brd/brd-pda-beneficios.md)
> (sign-off canônico, 2026-09-21).
>
> Pass 1 fica **acima da stack**: aqui se decide *o quê* e *quanto*. Motor de
> processamento, formato de armazenamento e orquestração são decididos no
> Pass 3.

## Problem restated

O carregamento atual publica benefícios emitidos sem comparar o resultado com
a origem. Se a leitura perder registros ou ler a coluna errada, o processo
termina com sucesso e nada acusa — e o `mode("overwrite")` apaga a execução
anterior, então nem depois dá para reconstruir o que foi publicado.

Resolvido significa: o agregado da competência é comparado contra um total
medido na origem **antes** de publicar, toda diferença recebe uma
classificação nomeada, e a execução deixa um pacote que permite responder
meses depois por que aquele número foi aceito.

## Scope

**In scope:**
- leitura posicional da competência, preservando os bytes originais
- agregação monetária exata, com precisão e arredondamento declarados
- comparação contra os cinco controles da âncora medida na origem
- classificação obrigatória de toda diferença
- pacote de evidência por execução, com veredito, causa e números

**Out of scope:**
- corrigir defeitos da fonte — a fábrica classifica, nunca corrige
- substituir o carregamento atual, que segue rodando em paralelo
- o ETL a jusante que consome o resultado
- painel, relatório de negócio ou interface

## Requirements

- **R-1 (must).** Nenhuma publicação ocorre sem âncora medida na origem para
  aquela competência. Sem âncora, o veredito é `ACEITO_SEM_ANCORA` e **não**
  autoriza publicar.
- **R-2 (must).** As colunas são lidas por **posição** declarada no contrato,
  nunca por nome de cabeçalho. Com `Espécie` em 12 e 13, ler por nome perde
  uma das duas em silêncio (ADR 0002).
- **R-3 (must).** Agrupamento, junção e contagem por espécie usam o **código**
  (posição 12). Agrupar por `descricao_especie` é recusado porque a descrição
  que cobre mais de um código **perdeu identidade** — medido na competência
  inteira, 11 descrições cobrem 24 códigos (ADR 0008). O critério de largura
  do ADR 0004 foi medido e **refutado**: as 41.572.553 descrições têm 20
  caracteres brutos, e "truncada em 20 caracteres" marcaria toda linha. A
  cardinalidade entra no contrato como valor **medido**, nunca fixada — são
  65 códigos e 52 descrições, não os 51→40 amostrados em ~3 milhões de linhas.
- **R-4 (must).** Campo monetário é somado com precisão **derivada** —
  dígitos inteiros da âncora mais a escala máxima dos intermediários, 11+3=14
  nesta competência — sem quantização intermediária, e arredondado uma vez no
  total com meio-para-par a 2 casas. A derivação vale sob **soma monotônica**,
  e valor negativo é defeito classificado, não entrada válida. Ponto flutuante
  em campo monetário é **recusado na entrada**, nunca convertido (ADR 0009).
- **R-5 (must).** Os **cinco** controles da âncora são comparados
  individualmente — `count_linhas`, `sum_vl_liquido`, `min_vl_liquido`,
  `max_vl_liquido`, `linhas_invalidas`. Divergência em qualquer um recusa,
  mesmo que classificada: a classificação explica, nunca autoriza.
- **R-6 (must).** Toda diferença recebe exatamente uma de seis
  classificações. Diferença observada sem classificação atribuída bloqueia.
- **R-7 (must).** Uma divergência introduzida de propósito — uma linha
  removida ou um centavo alterado no arquivo — é recusada antes da
  publicação, provada por teste que falha se o juízo aceitar.
- **R-8 (must).** Não existe parâmetro de tolerância em nenhum ponto do
  caminho de decisão.
- **R-9 (should).** A conferência de uma competência completa em até 20
  minutos, medido do início da leitura ao veredito. A medição da âncora levou
  64 segundos (measured) varrendo 10,88 GB, então o orçamento é folgado.
- **W-1 (won't).** Os bytes de origem não são alterados em hipótese alguma:
  permanecem imutáveis (`chmod 444`) e verificáveis por sha256.
- **W-2 (won't).** Nenhuma execução sobrescreve a evidência de outra. Cada
  execução grava o seu pacote; corrigir o histórico é falsificar prova.

## Success metrics

| Metric | Current | Target |
|---|---|---|
| Divergência não detectada entre origem e publicado | desconhecida | -> 0 |
| Competências publicadas sem prova do conteúdo | todas | -> 0 |
| Tempo da leitura ao veredito | não medido | -> menos de 20 min |

## Data named

O arquivo CSV da competência, como a origem o publica — 14 colunas,
separador `;`, encoding latin-1, valor monetário na posição 9 no formato
`1.621,00` (ponto de milhar, vírgula decimal). `Espécie` ocupa as posições
12 (código) e 13 (descrição truncada).

A âncora é o total medido diretamente sobre esse arquivo, por fora do
pipeline, mais quem confirmou e quando — registrada em
[`../adrs/0001-the-2026-01-anchor-is-41572553-rows-summing-78521752562-12.md`](../adrs/0001-the-2026-01-anchor-is-41572553-rows-summing-78521752562-12.md).

## Open assumptions

- A fonte publica uma competência por arquivo, com o mesmo layout de 14
  colunas.
  owner: Bruno Nunes
- As descrições truncadas continuarão em 20 caracteres nas competências
  futuras.
  owner: Bruno Nunes

## Gap register

```yaml
- id: GAP-001
  type: decision
  severity: nice-to-have
  question: "Qual dicionário oficial resolve o código de espécie para a descrição completa?"
  blocks: "nada — R-3 já proíbe agrupar por descrição"
  owner: "Bruno Nunes"
  resolution: "RESOLVIDO 2026-09-21: fora de escopo. A descrição truncada é preservada como rótulo; a descrição completa, se for necessária, entra por dicionário à parte, em projeto próprio."
```

## Sign-off

- **Owner/decider:** Bruno Nunes — verdict: **approved — canonical**
- **Date:** 2026-09-21
