# Composição do medalhão v2 — arquivada

Plano de 4 costuras selado em 9ddd6ac, ANTES de as camadas gravarem no MinIO e em Delta. O contrato-ext foi entregue a partir dele (task/contrato-expoe-particao, LOCAL_SETTLED, 139 testes) e continua valido: a costura dele nao mudou. A Bronze dele passou nos evals sem gravar nada e ficou em task/bronze-confere-ancora, superada.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
