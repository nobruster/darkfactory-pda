# Composição do medalhão v3 — arquivada

Composicao do medalhao com Delta, selada em 2a7e32a. As quatro tarefas foram entregues no Pass 8 (contrato-ext, bronze, silver, gold — LOCAL_SETTLED) e rodaram sobre o dado real. Sai da raiz para a receita da procedencia.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
