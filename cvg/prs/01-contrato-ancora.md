# T-20260921-contrato-ancora

Costura `SEAM-CONTRATO` · módulo `src/pda/contrato.py`

| | |
|---|---|
| base | `main` |
| head | `task/contrato-ancora` |
| código | 569 linhas (`contrato.py` + testes) |
| diff total | 634 linhas em 27 arquivo(s) |
| testes | 20 em `tests/test_contrato.py` |
| selo | Tier 1 — HMAC v3 |
| veredito | `pass` · path_policy `pass` |

## As objeções do Pass 4 que viraram código aqui

| # | O que faltava |
|---|---|
| `C1` | O fluxo dito inteiro não cobria a arquitetura do ADR 0005 — dava para concluir a cadeia com módulos Python e fixtures, sem nunca c |
| `R2-C3` | O hash ancorado não dizia se cobria o ZIP publicado ou o CSV extraído sobre o qual a âncora foi medida. |
| `R4-C2` | Minha correção de R3-C2 não distinguia falta de âncora de falha na execução — as duas chegam sem hash e não são o mesmo desfecho. |
| `R5-C5` | O ADR 0003 põe precisão e arredondamento no contrato, mas o carregador não os carregava — ficavam escolha privada da implementação |
| `R6-C2` | NAO_MEDIDO tem várias causas — sem aprovador, sem data, sem política decimal — e minha regra lia a falta do hash como se fosse a c |
| `R6-C3` | Produtor externo podia agrupar por descrição, colapsar espécies e declarar os mesmos cinco controles, hashes e defeitos. |

## Como conferir

```bash
git checkout task/contrato-ancora
pytest tests/test_contrato.py -q
```

## Abrir o PR

https://github.com/nobruster/darkfactory-pda/compare/main...task/contrato-ancora?expand=1

---

⚠️ Escrito por um agente sob contrato selado no Pass 5, com escopo
de escrita declarado. O agente **não pode** editar a Task-Spec nem
os testes que o avaliam.
