# task-spec — cópia vendorizada

Este diretório **não é um submódulo**. É uma cópia dos arquivos, versionada
direto neste repositório.

## Por quê

Para que `git clone` traga tudo de uma vez, sem
`--recurse-submodules` e sem pastas vazias.

## Procedência

| | |
|---|---|
| Origem | [https://github.com/luanmorenommaciel/task-spec](https://github.com/luanmorenommaciel/task-spec) |
| Commit congelado | `76ff7b8880c95fd583f933c69b77c8d75ad041db` |
| Autor | Luan Moreno Medeiros Maciel |
| Licença | MIT — ver `LICENSE` |
| Vendorizado em | 17/09/2026 |

## Consequências

- **O upstream continua ativo.** Diferente de `converge/` (que saiu do ar),
  este repositório existe — para comparar ou atualizar, vá à origem acima.
- **Não há `git submodule update`.** Atualizar é trabalho manual.
- **O histórico não veio.** O commit `76ff7b8880c95fd583f933c69b77c8d75ad041db` é o único ponto preservado.
- **Mudanças aqui viram commits deste repositório.**
