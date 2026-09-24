# Composição do medalhão memoria — arquivada

Composicao da memoria 6g, entregue na 1a tentativa; PERF=MELHOR 6g contra 6g. A suite numa JVM so achou o teste selado da regra antiga da limpeza, retirado pela receita teste-limpeza.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
