---
adr: "0003"
status: accepted
date: 2026-09-17
ground: brownfield
converge_pass: 2
spec_ref: "R-2"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0003 — seamwise lanes are projected into the converge dir-per-lane layout

## Context

Um planejador do Pass 3 que entregasse as lanes do Seamwise direto ao Pass 4
descobriria — só depois do dispatch — que o adversário atacou o vazio.

As duas ferramentas discordam do layout, e a discordância é **silenciosa de um
lado**:

| Componente | Padrão que procura | No layout plano do Seamwise |
|---|---|---|
| `check-consensus-gate.sh:189` | `<dir>/_lane.md` | **FAIL** — *"no swimlane PRDs — nothing to gate"* |
| `dispatch-review.sh:86` | `"$SKETCH_DIR"/*/*.md` | **zero arquivos, sem erro** |

O gate acusa. O dispatcher não: ele montaria o prompt sem nenhum plano, o
adversário produziria objeções sobre nada, e o gate recusaria depois por outro
motivo — **o resultado certo pela razão errada**.

É a costura aberta que o `AGENTS.md` registra na Regra 1.6 (*"as duas cadeias
ainda não se chamam"*), aqui com custo concreto.

## Decision

As lanes do Seamwise **são projetadas**, não movidas nem reescritas. O
adaptador
[`fabrica/ponte/lanes_para_converge.py`](../../../fabrica/ponte/lanes_para_converge.py)
lê `cvg/swimlanes/workspace/seamwise/swimlanes/LANE-*.md` e escreve
`cvg/swimlanes/lanes/<seam>/_lane.md`, acrescentando no topo a linha
`FORK: B (task-driven)` que o gate exige nas 15 primeiras linhas.

A projeção **é derivada e descartável**: o Seamwise regrava `swimlanes/` a
cada `plan`, então mover quebraria o `compile`. Apagar `lanes/` e rodar de
novo é o caminho normal.

Cada `_lane.md` carrega o `sha256` da sua origem. `--check` recompara, e uma
projeção defasada **falha** em vez de passar despercebida.

A ponte fica em `fabrica/` — é a opção 1 da Regra 1 (camada de adaptação),
não edição das pastas vendorizadas.

## Rejected reading

**Symlink de `<seam>/_lane.md` para o arquivo plano.** Seria a ponte mais
barata: zero cópia, hash sempre idêntico por construção.

Matou-a uma medição: `git config core.symlinks` é **false** neste
repositório. No Windows, o symlink versionado vira um arquivo de texto com o
caminho dentro — e o gate leria esse caminho como se fosse o PRD. A ponte
passaria e o conteúdo atacado seria uma linha de texto.

Também descartado: **editar `converge/` para aceitar o layout plano.** Mais
curto, e o upstream está fora do ar (404), o que torna a edição direta
aceitável pela Regra 1. Descartado porque o `converge/bin/` e
`skills/task-loop/scripts/` estão atrás da cerca em `.claude/settings.json`:
um agente que edita o próprio verificador é o modo de falha por
*specification-gaming*. A ponte resolve por fora, sem tocar em quem julga.

## Evidence

O check [5] do gate, nos dois layouts, verificado nesta máquina:

```sh
G=converge/skills/sketch-plans-adversarial-review/scripts/check-consensus-gate.sh
bash "$G" --dir cvg/swimlanes/workspace/seamwise/swimlanes   # layout plano
bash "$G" --dir cvg/swimlanes/lanes                          # projetado
```

observed output:

```
plano     : FAIL no swimlane PRDs (.../<seam>/_lane.md, or the legacy ...)
            — nothing to gate
projetado : ok   fork line present at the top of all 5 swimlane PRD(s)
```

E o que o dispatcher enxergaria (`*/*.md`, o padrão de `dispatch-review.sh:86`):

```sh
ls cvg/swimlanes/workspace/seamwise/swimlanes/*/*.md | wc -l   # 0
ls cvg/swimlanes/lanes/*/*.md | wc -l                          # 5
```

A ponte também **acusa** quando deve — testado alterando uma origem e
removendo um PRD:

```
DEFASADO LANE-JUIZO.md — a origem mudou desde a projeção   PONTE_LANES=STALE
FALTA    LANE-CONTRATO.md -> .../contrato/_lane.md         PONTE_LANES=STALE
```

## Consequences

- Rodar a ponte é passo obrigatório **entre** `seamwise plan` e
  `cvg review --adversary`. Pular resulta em adversário atacando o vazio.
- `--check` precisa dizer `PONTE_LANES=OK` **antes** do dispatch. Um `STALE`
  significa que o Seamwise regravou e a projeção ficou para trás.
- `cvg/swimlanes/lanes/` é **derivado**. Não edite ali: a próxima projeção
  sobrescreve. Edite a recipe e rode `seamwise plan`.
- A linha `FORK: B (task-driven)` é token de compatibilidade **congelado**, não
  escolha desta fábrica — o fork foi aposentado na v3.4
  (`converge/skills/sketch-plans-adversarial-review/references/the-fork.md`).
- ⚠️ Isto **não destrava o Pass 4**. Resolve o blocker de layout; o blocker do
  adversário (`DOCTOR=FAIL`, zero engines cross-family) continua aberto.
- Re-verify when: o Seamwise mudar o formato de saída das lanes, ou o Converge
  mudar o padrão que `dispatch-review.sh` e `check-consensus-gate.sh`
  procuram.
