# Glossário — termos desta descida

Termos fixados conforme se firmam. Um termo aqui tem **um** significado; se
mudar, muda com ADR novo, não por edição silenciosa.

## Do domínio

| Termo | Significado |
|---|---|
| **Competência** | O mês de referência do arquivo (`AAAA-MM`). Não é a data de processamento nem a de publicação. |
| **Âncora** | O total medido **direto na origem**, independente do pipeline, mais quem do negócio confirmou e quando. Um número que ninguém viu ser medido não é âncora — é palpite. |
| **Agregado** | O total que o pipeline produz a partir da competência. É o que se compara contra a âncora. |
| **Campo monetário** | Valor em dinheiro. Trafega como decimal exato ou string, **nunca** float, e arredonda meio-para-par ([ADR 0001](adrs/0001-money-rounds-half-to-even-at-two-decimals.md)). |

## Dos vereditos

| Termo | Significado |
|---|---|
| **`NAO_MEDIDO`** | Estado inicial do contrato. A fábrica **recusa construir**. Não se sai dele gerando a âncora automaticamente. |
| **`ACEITO`** | Agregado bateu contra âncora medida. Única forma que autoriza publicar. |
| **`ACEITO_SEM_ANCORA`** | Pipeline rodou, mas não havia âncora. **Não autoriza publicar.** Existe para que a ausência de prova seja visível, em vez de virar `ACEITO` silencioso. |

## Das classificações

Toda diferença recebe **exatamente uma**. Não classificar bloqueia.

| Código | Significado | Bloqueia? |
|---|---|---|
| `CONFIRMED_SOURCE_DEFECT` | A origem mentiu | não |
| `CONFIRMED_LEGACY_DEFECT` | O sistema em que se confiava está errado | não |
| `APPROVED_BEHAVIOR_CHANGE` | Mudou de propósito, aprovado | não |
| `MODERN_DEFECT` | O código novo está errado | **sim** |
| `CONTRACT_AMBIGUITY` | O contrato não decide | **sim** |
| `UNRESOLVED` | Não classificado | **sim** |

## Do processo

| Termo | Significado |
|---|---|
| **Gate** | Verificação que **reprova**. Um gate que nunca reprovou não é gate — é decoração. |
| **Blocker (gap)** | Pergunta que impede descer de passe. Só sai com resolução substantiva; `open`, `tbd`, `pending` não resolvem. |
| **Evidência** | O pacote por execução que permite reconstruir o veredito **sem reexecutar** o pipeline. |
| **Preservar o defeito** | A fábrica classifica, nunca corrige em silêncio. Corrigir destrói a prova de que a origem errou. |

## Palavras que não se usam aqui

| Evite | Por quê |
|---|---|
| "tolerância" | Não existe parâmetro de tolerância (R-4). Tolerância configurável é como um centavo inexplicado vira um centavo aceito. |
| "aproximadamente igual" | Ou bate, ou é diferença classificada. |
| "corrigir a origem" | Classifica-se como `CONFIRMED_SOURCE_DEFECT`; a origem não é alterada (W-1). |
