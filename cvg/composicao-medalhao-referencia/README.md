# Composição do medalhão referencia — arquivada

Composicao da referencia pelo medalhao, selada em 83cde49; seis loops LOCAL_SETTLED na 1a; suite 534 passed; publicada em producao pelas quatro camadas, especie v2 identica a v1.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
