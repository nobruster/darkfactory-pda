---
description: Conduz um BRD até a entrega pelo motor do Converge — Pass 0 a 8, com roteamento Opus/Sonnet/Haiku por lane e parada obrigatória em cada barreira humana.
argument-hint: "[caminho do BRD, ou nada para descobrir o passe atual]"
---

# /fabrica-run

Conduz `$ARGUMENTS` pela cadeia real da fábrica: **BRD → tech-spec → ADRs →
decomposição → consenso → tarefas → bind → loop → PR**.

Diferente de `/brainstorm`, `/define` e `/design` — que produzem markdown para
um humano ler — este comando aciona **código executável** (`converge/bin/cvg`,
`task-spec-3.8.1/bin/taskspec`, `seamwise`), com gates que reprovam de verdade
e roteamento de modelo por lane.

> **Você conduz, não decide.** O `cvg` é o árbitro e não chama LLM nenhum
> (`converge/bin/cvg:4-5`). Quatro barreiras exigem decisão humana; nelas você
> **para e pergunta**, nunca infere.

---

## Pré-requisito: apontar a versão certa do task-spec

⚠️ **Há duas versões do task-spec neste repositório, e o `cvg` só aceita uma.**

| Pasta | Versão | Serve para |
|---|---|---|
| `task-spec/` | 3.9.0 | TaskMesh (daemon autônomo) — **o `cvg` recusa** |
| `task-spec-3.8.1/` | 3.8.1 | **O que o `cvg` exige** |

O Converge 0.2 exige `3.8.x` **exato**, não mínimo (`converge/bin/cvg:143-149`).
Aponte antes de qualquer passe:

```bash
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
```

Sem isso o `cvg` falha com `incompatible Task-Spec engine '3.9.0'` — ou, se
nada estiver no `PATH`, com `Task-Spec engine not found`.

Detalhes em [`task-spec-3.8.1/VENDORED.md`](../../../task-spec-3.8.1/VENDORED.md).

## Antes de começar

```bash
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
converge/bin/cvg doctor host      # esta máquina consegue assinar, bind, loop?
converge/bin/cvg next --guided    # em que passe o projeto está?
```

### ⚠️ Rode de dentro do WSL, não do Git Bash

O motor é bash de Linux. Do Git Bash no Windows ele falha por falta de
`shellcheck` — e sem ele **nada é assinável**, logo nada chega ao Pass 8:

```
MISSING  shellcheck  → cvg tasks gate → no spec SIGNED
                     → cvg bind refuses → cvg loop has no runtime contract
```

Dentro do WSL, com o `shellcheck` presente, o resultado é:

```console
$ cd ~/darkfactory-template/converge
$ CVG_TASKSPEC_BIN=~/darkfactory-template/task-spec-3.8.1/bin/taskspec \
    ./bin/cvg doctor host
  ok  git 2.43.0 · bash 5.2.21 · python3 3.12.3 · shellcheck 0.9.0 · sha256
GATE: OK — this host can sign, bind, loop and settle.
DOCTOR_HOST=OK
```

Se `doctor host` acusar falta, ele nomeia **quais verbos ficam bloqueados** —
resolva antes de seguir.

`cvg next` é **read-only**: nomeia o próximo passo, não o executa
(`converge/skills/evidence-to-next-pass/SKILL.md:3`).

---

## A cadeia

| Pass | Comando | O que decide |
|---|---|---|
| 0 · Capture | `cvg capture [brief]` | O BRD é canônico? |
| 1 · Intent | `cvg intent [spec]` | A tech-spec responde ao BRD? |
| 2 · Structure | `cvg structure` | As decisões viraram ADRs? |
| 3 · Decompose | `seamwise plan` | Vira um `TaskPlan/v1` |
| 4 · Consensus | `cvg review --adversary <E>` → `cvg review --resolve` | 🛑 **barreira** |
| 5 · Tasking | `taskspec` + `cvg gate --stamp` | Cada folha assinada |
| 7 · Bind | `cvg bind --task <spec>` | Perfil de execução + guards |
| 8 · Loop | `cvg loop --issue <id>` | Tenta → verifica → repete → PR |

### Pass 0 — Capture

```bash
converge/bin/cvg capture cvg/docs/brd/<arquivo>.md
```

O veredito exige a assinatura do dono dizendo `canonical`. `pending` e `draft`
**nunca autorizam handoff** (`converge/skills/idea-to-brd/scripts/check-brd.sh:18`).

🛑 **Barreira A — o BRD é do dono.** Se estiver `draft`, pare e peça o
sign-off. Não promova por conta própria.

### Pass 1–2 — Intent e Structure

```bash
converge/bin/cvg intent      # tech-spec responde ao BRD
converge/bin/cvg structure   # ADRs registram as decisões
```

Revisão de ADR se faz com **ADR novo**, nunca editando o antigo.

### Pass 3 — Decompose

Só o Seamwise decompõe (token `COMPOSE`). Ele para em
`DELIVERY_PLAN=NEEDS_REVIEW` e **recusa compilar** sem um recibo de revisão
ligado ao digest exato do plano (`seamwise/README.md:143`).

🛑 **Barreira B — a decomposição precisa de revisor nomeado:**

```bash
seamwise review --accept --reviewer <nome> --reason <motivo>
```

### Pass 4 — Consensus 🛑 **A BARREIRA**

```bash
converge/bin/cvg review --adversary codex     # ou kimi, claude
converge/bin/cvg review --check               # CHECK_CONSENSUS
converge/bin/cvg review --resolve <id> --fix
converge/bin/cvg review --resolve <id> --accept --owner <nome> --risk <peso>
```

**O adversário só PROPÕE.** `--check` fica RED até um humano decidir cada
objeção (`converge/bin/cvg:1702-1705`). Não é contornável: o `cvg` recusa se
não conseguir atribuir `decided_by`.

> Por que é rígido assim: em 2026-08-03 o gate leu a proposta do próprio
> adversário como consentimento e ficou **GREEN com sete críticos abertos**
> (`converge/bin/cvg:1218-1220`).

**Nunca resolva uma objeção em nome do usuário.** Apresente cada uma e
pergunte: corrigir ou aceitar o risco conscientemente?

### Pass 5 — Tasking

Cada folha é autorizada individualmente por HMAC:

```bash
task-spec-3.8.1/bin/taskspec gate --stamp tasks/T-<id>.md
```

🛑 **Barreira D.** Não carimbe `signed_off` nem `accepted` à mão — é
exatamente o que o selo existe para impedir.

### Pass 7 — Bind

```bash
converge/bin/cvg bind --task <spec>
```

Aqui o **roteamento de modelo** acontece, por
`converge/skills/task-to-runtime-contract/scripts/cost-profile.py:52`:

| Lane | Modelo | Raciocínio | Iterações | Verifica? |
|---|---|---|---|---|
| FAST | **Haiku** | low | 3 | não |
| NORMAL | **Sonnet** | medium | 5 | não |
| FULL | **Opus** | high | 15 | **sim** |

Multiplicado pelo esforço declarado (`XS` 0.5× … `L` 1.5×). A lane **só
aperta** um teto, nunca afrouxa — e uma flag explícita vence a tabela.

Não force `--model` para "ir mais rápido": a tabela existe porque uma build
mecânica consumia o mesmo motor de um serviço novo — 66 turnos, $7,91 medidos
numa execução real (`loop-kernel.sh:268-271`).

### Pass 8 — Loop

```bash
converge/bin/cvg loop --issue <id> [--agent claude|codex|kimi]
```

Tenta → verifica → repete, limitado por iterações, relógio e tokens, com
detector de estagnação. **Cada tentativa recebe contexto novo**, em worktree
isolado.

Termina em **exatamente um** estado nomeado:

| Estado | Significa |
|---|---|
| `SETTLED` | PR aberto |
| `LOCAL_SETTLED` | commit local, sem remote |
| `NO_OP` | nada a fazer |
| `BLOCKED` · `STALLED` · `EXHAUSTED` · `CANCELLED` · `ERROR` | não entregou |

**Só os três primeiros saem com 0.** `ERROR` nunca é sucesso — não relate
como se fosse.

🛑 **Barreira E — quem faz não aceita.** `taskspec accept` roda
independentemente. Não edite `accepted: true` à mão.

---

## O que NÃO fazer

- **Não pule uma barreira** porque "está óbvio". As quatro existem por
  incidente registrado, não por excesso de zelo.
- **Não decida objeção de consenso pelo usuário.** Pergunte.
- **Não relate `ERROR`, `BLOCKED` ou `STALLED` como entrega.**
- **Não edite o verificador** (`cvg`, `gate.yaml`, `task-loop/scripts/`) para
  um gate passar. A cerca em `.claude/settings.json` bloqueia — se você está
  tentando, pare e investigue o gate.
- **Não rode `cvg loop` em lote.** É uma issue por vez, por design.

---

## Ao final

Diga, com evidência:

1. Em que passe o projeto está agora
2. Qual gate reprovou, se algum — e **o que o gate disse**, não a sua leitura
3. Qual barreira humana está esperando decisão
4. O estado terminal do loop, se chegou ao Pass 8

Se parou numa barreira, isso **não é falha** — é o desenho funcionando.
