# BRD — Benefícios emitidos do PDA, por competência

## Executive summary
Um script publica benefícios emitidos do INSS sem comparar o resultado com a
origem, e ninguém consegue provar depois que o número publicado está certo.

## Problem
O carregamento atual lê o CSV da competência e grava Parquet no lago **sem
nenhuma conferência**: não há contagem esperada, não há total esperado, não há
registro do que foi publicado. Se a leitura perder registros ou trocar uma
coluna, o pipeline termina com sucesso e nada acusa.

Três defeitos concretos, lidos no script que roda hoje e está preservado em
`docs/legado/` (measured):

- A gravação usa `mode("overwrite")` (measured), chamada de idempotência no
  próprio comentário. Ela destrói a execução anterior: não há como responder
  meses depois o que foi publicado, nem comparar duas execuções.
- A coluna `Espécie` aparece **duas vezes** no cabeçalho (measured). O script
  desambigua renomeando a segunda, mas nada garante que a coluna certa seja
  lida — e ler por nome com cabeçalho repetido perde o código em silêncio.
- As credenciais do armazenamento estão em texto puro no código versionado
  (measured), o que impede rotacioná-las sem reeditar o script.

O arquivo da competência 2026-01 tem 575.423.625 bytes (measured) e é
publicado por uma fonte externa sobre a qual não temos controle.

## Goals
- KPI-1 — divergência não detectada entre origem e publicado: hoje
  desconhecida → zero.
- KPI-2 — competências publicadas sem prova do que contêm: hoje todas →
  zero.

## Scope
**In:**
- comparação do que foi lido contra um total medido na própria origem
- classificação obrigatória de toda diferença encontrada
- pacote de evidência por execução, com veredito e números
- preservação dos bytes originais, imutáveis e verificáveis por hash

**Out:**
- corrigir defeitos da fonte — a fábrica classifica, nunca corrige
- reescrever o carregamento atual; ele segue rodando enquanto isso
- painel, interface ou relatório de negócio
- o ETL a jusante que consome o Parquet

## Definition of success
Uma competência fecha com veredito explicado por evidência, e uma divergência
introduzida de propósito — uma linha removida ou um centavo alterado — é
**recusada** antes de qualquer publicação.

## Stakeholders
- Bruno Nunes — owner and decider (desempata).

## Risks
- A âncora ser estimada em vez de medida na origem. Bloqueante: sem âncora
  medida o contrato nasce `NAO_MEDIDO` e a fábrica recusa construir.
- A fonte republicar a competência com conteúdo diferente. Mitigado pelo
  sha256 dos bytes originais: a mudança fica visível em vez de silenciosa.
- O juiz nunca reprovar, e ninguém perceber que está cego. Mitigado por teste
  que exige que ele **acuse** um defeito introduzido de propósito.

## Constraints
- Dinheiro em decimal exato, nunca float, com regra de arredondamento
  declarada no contrato.
- Os bytes originais permanecem imutáveis (chmod 444 + sha256); nada reescreve
  `_raw/`.
- Sem parâmetro de tolerância em nenhum ponto do caminho de decisão.
- Credenciais nunca em código versionado.

## Open questions
- question: qual total e contagem da competência 2026-01 serão a âncora, e
  quem confirma que foram medidos na origem
  owner: Bruno Nunes
- question: quais colunas do arquivo são monetárias, e qual a regra de
  arredondamento que a fonte aplica
  owner: Bruno Nunes

## Source
Fonte pública do INSS — Portal de Dados Abertos, grupo "Benefícios emitidos",
arquivo `D.SDA.PDA.003.EMI.202601.CSV.ZIP`, publicado em 25/02/2026
(measured, cabeçalho HTTP). O script atual está preservado em
`docs/legado/01-LANDING-MACICAPDA.py` como registro do que existe hoje — é
evidência, não especificação.

## Do-nothing test
Não fazer nada mantém a publicação sem prova. O custo não aparece enquanto
tudo dá certo: aparece no dia em que alguém pergunta se o número de uma
competência passada estava correto, e a resposta é que não há como saber — o
`overwrite` apagou o anterior e nunca houve conferência.

## Sign-off
- Owner/decider: Bruno Nunes — verdict: **approved — canonical**
- Date: 2026-09-21
