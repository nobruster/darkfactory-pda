# Onde parei — 24/09/2026, madrugada

O dono pediu para parar. Isto é só para retomar sem reconstruir contexto; o
histórico completo está no `git log` desta branch.

## O que está em produção (MinIO, Delta) — 2026-01 publicada

| Camada | Tabela | Versão | Linhas | Soma | Estado |
|---|---|---|---:|---:|---|
| Landing | `s3a://landing/pda/beneficios-emitidos` + `_PROCEDENCIA.json` | — | 41.572.553 | 78.521.752.562,12 | vinculada ao CSV `505725d9…` |
| Bronze | `s3a://bronze/pda/beneficios-emitidos` | v4 | 41.572.553 | 78.521.752.562,12 | `INTEGRO`, commit nomeia o pacote `ACEITO` da ingestão |
| Silver | `s3a://silver/pda/beneficios-emitidos` | v5 | 41.572.553 | 78.521.752.562,12 | `INTEGRO` |
| Gold | `s3a://gold/pda/beneficios-emitidos` | v3 | 65 códigos | 78.521.752.562,12 | `INTEGRO`, lida **só da Silver** (17 s; antes 1326 s) |
| Assuntos | `s3a://gold/pda/assuntos/fat_especie` e `kpis_nacionais` | v7 | 65 / 1 | 78.521.752.562,12 | `INTEGRO`, código a código igual à Gold |

Execução real que publicou: `v4-20260924T011752` (evidência em
`/app/trabalho/evidencia/`). Preparos antigos e prefixos de teste já foram
apagados; `_preparo` vazio.

## Cadeias entregues (todas `LOCAL_SETTLED`, receipt `pass/pass`)

Primeira descida (7) · contrato-ext · medalhão Delta (bronze, silver, gold) ·
procedência (vinculador, bronze lê a prova) · **v4** (ingestão julgada, gold
lê a silver, grupos no contrato, gold por assuntos, limpeza do preparo).
Suíte: **327 testes verdes por módulo** (numa JVM só estoura o heap de 1 GB
herdado — é o que a cadeia de performance corrige).

Contrato: mapa dos 11 colapsos e `grupos_especie` (65 códigos por texto, 6
nomeados em Outros) aprovados pelo dono, com nome e data.

## Onde a cadeia de PERFORMANCE parou

Receita `cvg/swimlanes/performance-recipe.yaml`, 4 costuras: memória
declarada + `unpersist` + reconferência numa passada (bronze/silver);
`unpersist` + um CHECK só (gold/assuntos); testes mais leves; limpeza de
execuções substituídas.

| Passe | Estado |
|---|---|
| 3 · 4 | 🟢 `CHECK_CONSENSUS=OK` na R2 (commit `16cd810`) |
| Arquivo da composição v4 | 🟢 `ca40f3c` |
| **5 · Tasking** | 🟡 **no meio** — compose `MATERIALIZED`; `perf-bronze-silver` e `perf-gold` **seladas**; `testes-leves` e `limpa-substituidas` **não seladas**; **nada deste passe commitado** (a árvore tem `seamwise/`, `cvg/tasks/T-20260924-*`, `cvg/receipts/` sem commit — é o estado esperado, não lixo) |
| 7 · Bind | ⬜ |
| 8 · Loop | ⬜ 4 loops |

Baselines de performance em `perf/` (gate `spark-perf`, 6 GB declarados,
ruído `PERF=IGUAL`): bronze executor 374 s, silver 678 s, assuntos 167 s.

## O comando para retomar

```bash
# de dentro do WSL Ubuntu-24.04
bash ~/retomar_perf.sh      # sela o que falta, Pass 5 commit, Pass 7, os 4 loops
```

Ele confere a branch (`task/limpa-preparo`), para no primeiro loop que não
assentar e confere os caminhos de cada tarefa (Regra 10 pelos dois lados).

## Depois do Pass 8 — verificação pós-assentamento prometida no Pass 4

1. Rodar de novo bronze, silver e assuntos com event log e 6 GB e comparar
   com `perf/` pela skill: só aceitar `PERF=MELHOR` com saída **idêntica** à
   produção (controles + multiconjunto 0/0). `PIOR`/`IGUAL` → reverter.
2. Rodar os assuntos **duas vezes** — a segunda não pode acrescentar CHECK
   nem falhar (R2 C3).
3. Rodar `test_gold.py` e `test_gold_assuntos.py` **inteiros, cronometrados**;
   meta: assuntos abaixo de 275 s (hoje 551 s).
4. Comparar pela AST e por `git diff` as funções `test_*` contra o commit
   selado do Pass 5 (gravado em `/tmp/perf_selado.txt` pelo script).

## Pendências fora da performance

- **Fase 2 da Gold:** landing v2 com as 14 colunas → `fat_uf`, `fat_banco`,
  perfil demográfico.
- `scripts/medir_colapso.py`: piso da Regra 9 (conta descartes, zero linhas
  é `NAO_MEDIDO`).
- `cvg/MEDALHAO.md` está defasado em relação a este arquivo.
- **Publicar:** muitos commits locais aqui e no template (`main`). O push é
  do dono, do terminal dele (o Git Credential Manager pede interação).

## Armadilhas desta sessão (já na bancada, `AGENTS.md` do template)

- Nunca montar comando destrutivo por `wsl.exe -- bash -lc '… $var …'`: o
  shell do Windows expande a variável vazia. Um `mc rm l/$p/` virou `l//` (o
  site inteiro) — o `mc` recusou. Apagar é por script, caminho literal, lista
  fechada.
- Enquanto um loop inplace roda, **nada mais** escreve neste repositório.
- O agente do loop pode rodar **só** `docker compose -f infra/docker-compose.yml
  exec -T spark python3 -m pytest…` (autorizado pelo dono, escopo mínimo),
  via `~/bin/claude-loop-testes` e `CVG_CLAUDE_CMD` no `~/pass8_tarefa.sh`.
