# Converge — cópia vendorizada

Este diretório **não é um submódulo**. É uma cópia dos arquivos, versionada
diretamente neste repositório.

## Por quê

O repositório de origem saiu do ar:

```
https://github.com/luanmorenommaciel/converge   →   HTTP 404
```

Enquanto era submódulo, um `git clone --recurse-submodules` falhava e a pasta
vinha vazia. Vendorizar preserva o conteúdo.

## Procedência

| | |
|---|---|
| Origem | `github.com/luanmorenommaciel/converge` (indisponível) |
| Commit congelado | `f6df8afe27e8b26715eaa2803b20261f5434c6b0` |
| Mensagem do commit | `changes` |
| Versão | `0.2.0` (ver `VERSION` e `package.json`) |
| Autor | Luan Moreno Medeiros Maciel |
| Licença | MIT — ver [`LICENSE`](LICENSE) |
| Vendorizado em | 17/09/2026 |

O `LICENSE` original foi mantido intacto, com o copyright do autor. A licença
MIT permite a redistribuição desde que esse aviso seja preservado — e ele está.

## O que mudou em relação ao original

O histórico git (`.git/`) foi removido; os 509 arquivos de trabalho são
idênticos ao commit `f6df8af`. **Nenhum arquivo de código foi alterado.**

## Consequências práticas

- **Não há upstream para atualizar.** `git submodule update --remote` não se
  aplica aqui. Se o repositório voltar ao ar, dá para reconverter em submódulo.
- **Mudanças aqui são commits deste repositório** — ao contrário dos demais
  submódulos, onde editar é erro (ver [`../AGENTS.md`](../AGENTS.md), Regra 1).
- **O histórico original se perdeu.** O commit `f6df8af` é o único ponto no
  tempo preservado.
