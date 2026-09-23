# Composição do medalhão procedencia — arquivada

Composicao da procedencia, selada em 1b12e71. As duas tarefas foram entregues (vincula-procedencia e bronze-le-procedencia, LOCAL_SETTLED) e a cadeia real publicou 2026-01 na Gold com ACEITO. Sai da raiz para o medalhao v4.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
