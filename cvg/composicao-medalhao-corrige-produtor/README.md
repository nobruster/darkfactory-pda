# Composição do medalhão corrige-produtor — arquivada

Composicao da correcao do produtor, selada em 339fb1c; tres loops LOCAL_SETTLED na 1a; produtor corrigido sobre o 2026-01 real = ancora; suite 460 passed.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
