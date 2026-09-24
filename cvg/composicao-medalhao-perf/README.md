# Composição do medalhão perf — arquivada

Composicao da performance (plano corrigido), selada em f2f7221. As tres tarefas foram entregues na 1a tentativa; a verificacao pos-assentamento achou a memoria declarada com 1g, corrigida pela receita memoria-6g.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
