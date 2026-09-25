# Composição do medalhão postgres-validado — arquivada

Composicao da receita B (Postgres validado pela Gold), selada em c17e6df; LOCAL_SETTLED na 1a; suite 545 passed; Postgres de producao recarregado pelo caminho novo, validado contra a Gold.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
