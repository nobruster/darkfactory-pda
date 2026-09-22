# T-20260921-leitura-posicional

Costura `SEAM-LEITURA` · módulo `src/pda/leitura.py`

| | |
|---|---|
| base | `task/contrato-ancora` |
| head | `task/leitura-posicional` |
| código | 627 linhas (`leitura.py` + testes) |
| diff total | 683 linhas em 6 arquivo(s) |
| testes | 12 em `tests/test_leitura.py` |
| selo | Tier 1 — HMAC v3 |
| veredito | `pass` · path_policy `pass` |

## As objeções do Pass 4 que viraram código aqui

| # | O que faltava |
|---|---|
| `C3` | Leitura posicional não provava rejeição de mudança de layout; trocar duas colunas não monetárias preservaria os cinco controles. |
| `C6` | O truncamento do ADR 0004 podia nunca chegar à classificação — dinheiro válido e descrições truncadas passariam com defeitos vazio |
| `R2-C6` | A regra que EU escrevi na rodada 1 — descrição com exatamente 20 caracteres — deixava de fora o exemplo principal do ADR 0004. |
| `R3-C1` | O ADR 0005 põe a infra Spark no escopo do Pass 3, e o out_of_scope da receita a exclui. Terceira rodada da mesma objeção. |
| `R4-C1` | Minha correção de R3-C5 exigia comparar o hash computado, mas nada no grafo levava esse valor até o validador. |
| `R4-C2` | Minha correção de R3-C2 não distinguia falta de âncora de falha na execução — as duas chegam sem hash e não são o mesmo desfecho. |

## Como conferir

```bash
git checkout task/leitura-posicional
pytest tests/test_leitura.py -q
```

## Abrir o PR

https://github.com/nobruster/darkfactory-pda/compare/task/contrato-ancora...task/leitura-posicional?expand=1

---

⚠️ Escrito por um agente sob contrato selado no Pass 5, com escopo
de escrita declarado. O agente **não pode** editar a Task-Spec nem
os testes que o avaliam.
