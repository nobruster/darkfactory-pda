# Composição do medalhão guarda-nome — arquivada

Composicao da receita F (guarda registra o nome oficial), selada em befebc8; LOCAL_SETTLED na 1a; DIFF_GUARDA=EXATO; suite 561 passed; Gold v4/fat v8 publicadas com nome_oficial e OPTIMIZE.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
