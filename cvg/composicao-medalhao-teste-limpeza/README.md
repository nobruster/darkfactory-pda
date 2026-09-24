# Composição do medalhão teste-limpeza — arquivada

Composicao do teste da limpeza: retirou o teste selado da regra antiga; LOCAL_SETTLED na 2a tentativa (a 1a bloqueou por BLAST_RADIUS, commit dos dicionarios no meio do loop); suite 361 passed numa JVM.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
