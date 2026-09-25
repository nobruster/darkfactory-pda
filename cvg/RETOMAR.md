# Onde parei — 24/09/2026, noite

Isto é para retomar sem reconstruir contexto. O histórico completo está no
`git log`; as decisões, nos ADRs (`cvg/docs/adrs/`, 0000–0014) e no
[`ESTADO.md`](ESTADO.md).

## O que está em produção

| Onde | O quê | Versão | Linhas | Soma | Estado |
|---|---|---|---:|---:|---|
| Landing | `s3a://landing/pda/beneficios-emitidos` + `_PROCEDENCIA.json` | — | 41.572.553 | 78.521.752.562,12 | vinculada ao CSV `505725d9…` · 95 objetos, 126.778.295 bytes |
| Bronze | `s3a://bronze/pda/beneficios-emitidos` | v4 | 41.572.553 | 78.521.752.562,12 | `INTEGRO` |
| Silver | `s3a://silver/pda/beneficios-emitidos` | v5 | 41.572.553 | 78.521.752.562,12 | `INTEGRO` |
| Silver | `s3a://silver/pda/especie` | v1 | 65 | — | nome oficial do INSS ao lado do texto da fonte; 65 nomes distintos (os 11 colapsos desfeitos), 43 textos iguais ao prefixo |
| Gold | `s3a://gold/pda/beneficios-emitidos` | v3 | 65 códigos | 78.521.752.562,12 | `INTEGRO` |
| Assuntos | `fat_especie`, `kpis_nacionais` | v7 | 65 / 1 | 78.521.752.562,12 | `INTEGRO` |
| Postgres | `pda-postgres`, banco e schema `ontologia` | carga 1 | 2/13/14/5/65 | — | projeção da ontologia, reconferida; sha256 da ontologia na tabela `carga` |

Só a competência **2026-01** está no lago.

## A cadeia — onde termina

A cadeia encadeia branches `task/*`, sem merge. A ponta é
**`task/vinculador-gramatica`** (`bf984d6`), com a árvore limpa.

| Verificador | Hoje |
|---|---|
| Suíte inteira numa JVM só | **460 passed**, sem skip nem xfail |
| `scripts/verificar_procedencia.py` | `PROCEDENCIA=OK` — 20 de 20 em `src/`, cada um com Task-Spec selada |
| `scripts/verificar_cercas.py` | `CERCAS=OK` — `.github/workflows` cercado por isenção nomeada |
| `scripts/checar_w1.py` | `W1=OK` |

O que foi entregue desde a madrugada de 24/09, em ordem:

1. **Performance** — memória declarada (6 GB), reconferência numa passada.
   `PERF=MELHOR` com saída idêntica à produção; a ablação mostrou que o ganho
   é do código, não do `shuffle.partitions`.
2. **Teste da regra antiga da limpeza** retirado por lista nomeada.
3. **Dicionários do INSS** em `_raw/` (444, sha256 no `CHECKSUMS.txt`).
4. **Ontologia** (ADR 0014) — `src/ontologia/beneficios-emitidos.yaml`, a
   fonte da verdade; a Delta `especie` e o Postgres são projeções.
5. **Linha `pds` reunida** (`dae1042`) — ADRs 0010–0013 dela. O ADR da
   ontologia foi renumerado de 0010 para 0014.
6. **Verificadores de cercas e de procedência** consertados — acusavam e
   aprovavam na mesma saída.
7. **Produtor adotado** pela cadeia (Regra 11) — `PROCEDENCIA=OK` pela
   primeira vez.
8. **Defeitos latentes do produtor corrigidos** — `src/produtor/gramatica.py`
   dá o veredito do juiz nos três módulos Spark; ANSI; partição ou rejeitos
   ocupados recusam; rejeitos com o texto bruto em
   `s3a://landing/pda/beneficios-emitidos-rejeitos` (cópia; a tabela segue com
   todas as linhas). O produtor corrigido sobre o CSV real de 2026-01 dá a
   âncora exata.

## O que falta

| Item | Por quê |
|---|---|
| **Contratos das competências de 2025** | O layout mudou entre 2025-08 e 2025-09 (ADR 0013): 2025-07 e 2025-08 têm 13 colunas e uma só "Espécie", na posição 0. Ingerir com o contrato de 2026-01 poria o código da espécie em "Despacho", em silêncio. Cada competência precisa de contrato próprio, **medido** (Regra 2) |
| Guarda de `--rejeitos` dentro do destino | Resíduo aceito na R3 da correção do produtor. Hoje só o dono ou o orquestrador passam o argumento |
| Fase 2 da Gold | `fat_uf`, `fat_banco`, perfil demográfico — exigem a landing com as 14 colunas |
| `MEDALHAO.md` | defasado em relação a este arquivo |
| **Publicar** | `git push` das branches `task/*` até `task/vinculador-gramatica`, e do merge da `pds`. O push é do dono, do terminal dele |

## Como retomar

```bash
# de dentro do WSL Ubuntu-24.04
cd ~/darkfactory-pda
git checkout task/vinculador-gramatica
docker compose -f infra/docker-compose.yml up -d      # minio, postgres, spark
python3 scripts/verificar_procedencia.py | tail -1     # PROCEDENCIA=OK
python3 scripts/verificar_cercas.py | tail -1          # CERCAS=OK
```

Uma receita nova segue o molde das de hoje: gerador em `~/gerar_*.py`, R1
corrige só o que toca dinheiro, publicação ou deleção, R2 decide sem editar —
**salvo contradição real entre o plano e um teste selado**, que se corrige
antes do loop (custou um `STALLED` e quase um segundo).

## Armadilhas desta fábrica (também no `AGENTS.md` do template)

- Nunca montar comando por `wsl.exe -- bash -lc '… $var …'`: o shell do
  Windows expande a variável vazia. Script em arquivo, sempre — e conferir as
  linhas de variável com `sed -n` antes de rodar.
- **Árvore limpa não prova que o loop terminou**: ele comita o trabalho do
  agente antes da conferência final. Nada escreve no repositório enquanto
  houver `cvg loop` vivo — um commit no meio deu `BLAST_RADIUS`.
- Plano que fatia em tarefas módulos que **dividem fixtures de teste** cria um
  estado intermediário impossível. Tarefa única, ou fixtures separadas.
- Medir antes de escrever a premissa: "todo CSV de `_raw/`" ignorava que o
  layout mudou — o loop recusou com razão.
- O agente do loop pode rodar **só** `docker compose -f infra/docker-compose.yml
  exec -T spark python3 -m pytest…`, via `~/bin/claude-loop-testes`.
