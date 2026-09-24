# Composição do medalhão v4 — arquivada

Composicao do medalhao v4, selada em bad9682. As cinco tarefas foram entregues e a execucao real publicou 2026-01 com a Gold lendo so a Silver (17s). Sai da raiz para a receita de performance.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
