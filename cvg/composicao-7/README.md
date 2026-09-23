# Composição das 7 costuras — arquivada

Estes são os artefatos da **primeira descida** do PDA: as sete costuras que
foram de BRD a código entre 21 e 22/09/2026.

## Por que foram arquivados

O `cvg compose` só enxerga o workspace da **raiz do repositório** —
`converge/bin/_cvg_compose.py:166` fixa `--workspace str(self.root)`, e
`SEAMWISE_WORKSPACE` é ignorado. Com a raiz ocupada por esta composição,
`compose prepare` curto-circuitava (`:266-267`, `if state.get("reviewed")`)
e nunca lia o `--source` do medalhão.

Compor o medalhão exigia liberar a raiz. **Isto não é descarte** — é dar
lugar à descida seguinte, preservando a anterior inteira.

## O que estas 7 entregaram, medido antes de arquivar

| | |
|---|---|
| receipts do Pass 8 | **7/7** com `result=pass` e `path_policy=pass` |
| módulos em `src/pda/` | **7/7** presentes |
| testes | **120 passando** |
| folhas em `cvg/tasks/` | 7, seladas em Tier 1, versionadas |

As folhas seladas **continuam em `cvg/tasks/`** — elas são o contrato, e
não se movem. O que veio para cá é a projeção do Seamwise e os receipts
da composição, que já cumpriram o papel.

## O que está aqui

```
seamwise/     seam-map, task-plan, delivery-plan, seams, swimlanes,
              legs, decisions, reviews — a projeção revisada das 7
receipts/     composition-receipt, source, taskspec-materialization
```

A composição registrava `pda-recipe.yaml @ d20d7852... commit 5baed60`.
Esse arquivo foi restaurado a esse exato conteúdo no commit `46ec56b`,
depois de eu tê-lo editado por engano — as costuras do medalhão foram
para `cvg/swimlanes/medalhao-recipe.yaml`, que é onde deveriam ter
nascido.
