# T-20260921-juizo-classifica

Costura `SEAM-JUIZO` · módulo `src/pda/juizo.py`

| | |
|---|---|
| base | `task/envelope-fronteira` |
| head | `task/juizo-classifica` |
| código | 465 linhas (`juizo.py` + testes) |
| diff total | 513 linhas em 5 arquivo(s) |
| testes | 15 em `tests/test_juizo.py` |
| selo | Tier 1 — HMAC v3 |
| veredito | `pass` · path_policy `pass` |

## As objeções do Pass 4 que viraram código aqui

| # | O que faltava |
|---|---|
| `R2-C1` | O fluxo não construiria o produtor Spark nem a infraestrutura que o ADR 0005 menciona — dava para fechar a cadeia com Python e env |
| `R2-C4` | O juízo provava ausência de classificação, não classificação única — duas classificações na mesma diferença passariam. |
| `R3-C1` | O ADR 0005 põe a infra Spark no escopo do Pass 3, e o out_of_scope da receita a exclui. Terceira rodada da mesma objeção. |
| `R3-C6` | A prova integrada de R-7 passaria sem exercitar o juízo: remover uma linha muda o hash, e a fronteira recusa antes da comparação. |
| `R4-C5` | Minha correção de R3-C6 SUBSTITUIU o cenário obrigatório de R-7 em vez de somar a ele. |
| `R6-C5` | Minha correção de R4-C5 dividiu R-7 em duas provas; R-7 escreveu uma propriedade CONJUNTA. |

## Como conferir

```bash
git checkout task/juizo-classifica
pytest tests/test_juizo.py -q
```

## Abrir o PR

https://github.com/nobruster/darkfactory-pda/compare/task/envelope-fronteira...task/juizo-classifica?expand=1

---

⚠️ Escrito por um agente sob contrato selado no Pass 5, com escopo
de escrita declarado. O agente **não pode** editar a Task-Spec nem
os testes que o avaliam.
