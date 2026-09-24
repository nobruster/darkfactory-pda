# Composição do medalhão ontologia-v1 — arquivada

Composicao da ontologia v1, selada em a2fc435. O loop da T-20260924-ontologia-versionada deu STALLED: o plano mandava conferir o cabecalho de todo CSV de _raw, e 2025-07/08 tem outro layout (13 colunas). Tentativa guardada em ~/arquivo-loops/ontologia-versionada-stalled-1.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
