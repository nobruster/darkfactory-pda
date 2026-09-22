# T-20260921-agregacao-exata

Costura `SEAM-AGREGACAO` · módulo `src/pda/agregacao.py`

| | |
|---|---|
| base | `task/leitura-posicional` |
| head | `task/agregacao-exata` |
| código | 434 linhas (`agregacao.py` + testes) |
| diff total | 482 linhas em 5 arquivo(s) |
| testes | 9 em `tests/test_agregacao.py` |
| selo | Tier 1 — HMAC v3 |
| veredito | `pass` · path_policy `pass` |

## As objeções do Pass 4 que viraram código aqui

| # | O que faltava |
|---|---|
| `C2` | Declarar um modo de arredondamento não demonstrava HALF_EVEN — uma implementação com HALF_UP passaria nos testes descritos. |
| `R2-C7` | Os cinco controles não tinham semântica para registros ilegíveis — cada implementação decidiria se contá-los. |
| `R3-C4` | Minha correção de C7 dizia "os quatro monetários somam"; não existem quatro monetários, e min/max não somam. |
| `R4-C4` | Demonstrar que dois agrupamentos diferem não prova qual deles o agregador entregue usa. |
| `R5-C5` | O ADR 0003 põe precisão e arredondamento no contrato, mas o carregador não os carregava — ficavam escolha privada da implementação |
| `R8-C8` | A prova do agregador local exigia as chaves, não os valores — somar por descrição e zerar os demais códigos passaria. |

## Como conferir

```bash
git checkout task/agregacao-exata
pytest tests/test_agregacao.py -q
```

## Abrir o PR

https://github.com/nobruster/darkfactory-pda/compare/task/leitura-posicional...task/agregacao-exata?expand=1

---

⚠️ Escrito por um agente sob contrato selado no Pass 5, com escopo
de escrita declarado. O agente **não pode** editar a Task-Spec nem
os testes que o avaliam.
