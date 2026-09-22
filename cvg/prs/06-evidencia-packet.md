# T-20260921-evidencia-packet

Costura `SEAM-EVIDENCIA` · módulo `src/pda/evidencia.py`

| | |
|---|---|
| base | `task/juizo-classifica` |
| head | `task/evidencia-packet` |
| código | 711 linhas (`evidencia.py` + testes) |
| diff total | 759 linhas em 5 arquivo(s) |
| testes | 19 em `tests/test_evidencia.py` |
| selo | Tier 1 — HMAC v3 |
| veredito | `pass` · path_policy `pass` |

## As objeções do Pass 4 que viraram código aqui

| # | O que faltava |
|---|---|
| `C7` | A promessa de pacote em todo caminho assumia que a própria gravação não falha. |
| `R2-C5` | O pacote podia reproduzir o rótulo do veredito sem preservar a prova que o prende ao arquivo julgado. |
| `R3-C2` | Minha correção de C5 recusava pacote sem hash incondicionalmente, o que impedia gravar justamente a execução ACEITO_SEM_ANCORA. |
| `R3-C3` | Os insumos que eu listei para rederivar o veredito não o determinam: mesmos controles e hashes admitem decisões distintas. |
| `R4-C2` | Minha correção de R3-C2 não distinguia falta de âncora de falha na execução — as duas chegam sem hash e não são o mesmo desfecho. |
| `R5-C3` | A fronteira compara TRÊS hashes e o pacote gravava dois; um RECUSADO legítimo rederivaria ACEITO. |

## Como conferir

```bash
git checkout task/evidencia-packet
pytest tests/test_evidencia.py -q
```

## Abrir o PR

https://github.com/nobruster/darkfactory-pda/compare/task/juizo-classifica...task/evidencia-packet?expand=1

---

⚠️ Escrito por um agente sob contrato selado no Pass 5, com escopo
de escrita declarado. O agente **não pode** editar a Task-Spec nem
os testes que o avaliam.
