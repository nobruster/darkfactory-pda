# Composição do medalhão adota-produtor — arquivada

Composicao da adocao do produtor, selada em 20142c9; LOCAL_SETTLED na 1a; PROCEDENCIA=OK pela primeira vez; suite 437 passed; landing intocado.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
