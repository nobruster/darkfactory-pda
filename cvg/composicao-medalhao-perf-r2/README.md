# Composição do medalhão perf-r2 — arquivada

Composicao da performance selada em 66ea97b, antes da correcao do plano: perf-gold esgotou 5 tentativas por uma contradicao entre o CHECK combinado e um teste selado. perf-bronze-silver foi entregue a partir dela e nao roda de novo.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição revisada ali, o `prepare`
curto-circuita com `CHANGED=false` — verde pelo motivo errado.

Nada foi apagado: `git mv` preserva o histórico. As folhas aqui estão
superseded pelas da composição seguinte, com os mesmos ids.
