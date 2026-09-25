# Composição do medalhão nome-oficial — arquivada

Composicao da receita D (nome oficial na Gold), selada em baf9b69; dois loops LOCAL_SETTLED na 1a; suite 1 failed: a guarda test_testes_leves acusou a mudanca autorizada — registrada pela receita F.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
