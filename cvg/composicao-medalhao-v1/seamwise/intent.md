---
schema_version: 1
kind: delivery-intent
id: DI-PDA-MEDALHAO
title: Camadas Bronze, Silver e Gold sobre a partição já publicada no lago
claim: proposed
source:
  uri: cvg/docs/tech-spec/tech-spec-pda-beneficios.md
  captured_at: '2026-09-21T00:00:00Z'
  sha256: e619ead9d343282533110bc8cb8f1203614d8e733565b21e3157df2b8f157b88
success:
- Partição que não reproduz os DOIS controles não vira Bronze.
- A soma não muda entre Bronze e Silver.
- Os 11 colapsos saem classificados, nunca deduplicados.
- Gold que não reconcilia com a âncora não publica.
- Ausência de âncora é NAO_MEDIDO, distinto de DIVERGE.
out_of_scope:
- Alterar o produtor que escreveu a partição — src/produtor/ está sem Task-Spec (Regra 11) e mexer nele
  exige tarefa própria.
- 'Fazer o Parquet carregar a procedência. Medido: a partição tem três colunas mais a de partição e nenhuma
  é procedência; exigi-la aqui faria Bronze recusar o dado CORRETO.'
- Reabrir as 7 costuras já seladas em Tier 1. Elas declaram 16 arquivos que o Pass 8 construiu, e o map
  recusa tarefa nova que declare arquivo existente.
- Ligar Gold ao juízo. 'gold reconciliado' hoje não é consumido por ninguém; a ligação precisa ser medida
  antes de decidida.
---
# Camadas Bronze, Silver e Gold sobre a partição já publicada no lago

## Delivery outcome

Ler a partição publicada conferindo-a contra a âncora do contrato, normalizar a forma sem tocar no valor e classificar o defeito de identidade colapsada, e agregar por código reconciliando com a âncora ao centavo — recusando cada camada que não prove o que afirma.

## Evidence boundary

This artifact records a **proposed** claim. Its source, capture time,
and content hash are recorded in frontmatter; the claim is not implementation
evidence by itself.
