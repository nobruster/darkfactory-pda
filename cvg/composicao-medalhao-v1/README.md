# Composição do medalhão v1 — arquivada

Plano de 3 costuras (Bronze, Silver, Gold), selado em Tier 1 no commit
2ca5dcb, antes das rodadas R14–R30 do Pass 4.

**Por que saiu da raiz:** o `cvg compose` sempre opera na raiz
(`_cvg_compose.py:166`) e, com uma composição já revisada ali, o
`prepare` curto-circuita e devolve `CHANGED=false` — verde pelo motivo
errado. O v2 (4 costuras, com SEAM-CONTRATO-EXT) precisa da raiz livre.

**Conferido antes de arquivar:** das 3 folhas, só a Bronze rodou no Pass 8,
e terminou `result: blocked` (`path_policy: not-run`) — nenhuma entrega
aterrissou. A branch `loop/T-20260922-bronze-confere-ancora-379610`
continua no remoto.

Nada foi apagado: `git mv` preserva o histórico. As folhas v1 estão em
`tasks/`, superseded pelas do v2 com os mesmos ids.
