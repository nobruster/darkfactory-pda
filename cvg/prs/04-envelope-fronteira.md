# T-20260921-envelope-fronteira

Costura `SEAM-FRONTEIRA` · módulo `src/pda/envelope.py`

| | |
|---|---|
| base | `task/agregacao-exata` |
| head | `task/envelope-fronteira` |
| código | 729 linhas (`envelope.py` + testes) |
| diff total | 777 linhas em 5 arquivo(s) |
| testes | 23 em `tests/test_envelope.py` |
| selo | Tier 1 — HMAC v3 |
| veredito | `pass` · path_policy `pass` |

## As objeções do Pass 4 que viraram código aqui

| # | O que faltava |
|---|---|
| `C1` | O fluxo dito inteiro não cobria a arquitetura do ADR 0005 — dava para concluir a cadeia com módulos Python e fixtures, sem nunca c |
| `C4` | A procedência não vinculava a âncora ao arquivo efetivamente lido — uma republicação com os mesmos controles passaria. |
| `R2-C2` | A regra que EU escrevi na rodada 1 confundia contagem de defeitos com linhas inválidas, e recusaria a competência 2026-01, que est |
| `R3-C5` | Comparar o hash declarado não prova que ele veio dos bytes lidos — um produtor com cache errado pode copiar o hash ancorado. |
| `R3-C6` | A prova integrada de R-7 passaria sem exercitar o juízo: remover uma linha muda o hash, e a fronteira recusa antes da comparação. |
| `R4-C1` | Minha correção de R3-C5 exigia comparar o hash computado, mas nada no grafo levava esse valor até o validador. |

## Como conferir

```bash
git checkout task/envelope-fronteira
pytest tests/test_envelope.py -q
```

## Abrir o PR

https://github.com/nobruster/darkfactory-pda/compare/task/agregacao-exata...task/envelope-fronteira?expand=1

---

⚠️ Escrito por um agente sob contrato selado no Pass 5, com escopo
de escrita declarado. O agente **não pode** editar a Task-Spec nem
os testes que o avaliam.
