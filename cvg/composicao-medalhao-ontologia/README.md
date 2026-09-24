# Composição do medalhão ontologia — arquivada

Composicao da ontologia (v2, layout do contrato), selada em 6e9220d; tres tarefas LOCAL_SETTLED na 1a iteracao; suite 418 passed; especie 2026-01 e schema ontologia publicados.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
