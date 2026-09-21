# Estado da descida — exemplo de fábrica

Onde o caso de exemplo parou, e o que falta para destravar.
Atualizado em 17/09/2026.

> **Este é um caso real**, não uma demonstração. Os dois blockers do Pass 1
> foram decididos pelo dono, e o plano de entrega foi revisado e assinado.

## Posição

| Passe | Gate | Veredito |
|---|---|---|
| 0 · Capture | `cvg capture` | 🟢 `CHECK_BRD=PASS` |
| 1 · Intent | `cvg intent` | 🟢 `CHECK_TECH_SPEC=PASS` |
| 2 · Structure | `cvg structure --final` | 🟢 `CHECK_ADR=OK` |
| 3 · Decompose | `seamwise compile` | 🟢 `TASK_GRAPH=READY` — 6 tarefas |
| 4 · Consensus | `cvg review --check` | 🟢 `CHECK_CONSENSUS=OK` — **GREEN** |
| 5 · Tasking | `taskspec gate --stamp` | 🟢 `TIER=1` — HMAC v3 nas 6 folhas |
| 7 · Bind | `cvg bind` | 🟢 `CHECK_RUNTIME_CONTRACT=PASS` nas 6 |
| 8 · Loop | `cvg loop` | 🟢 `LOCAL_SETTLED` — **6 de 6 entregues** |

## A cadeia entregou a fábrica inteira

As 6 tarefas do steel thread fecharam o ciclo, do BRD ao commit aceito.
**58 testes passando**, conferidos branch a branch em worktree separado —
não pelo relatório do loop.

| Branch | Iter | Testes |
|---|---|---|
| `task/contrato-ancora` | 2 | 8 |
| `task/leitura-competencia` | 1 | 6 |
| `task/agregacao-exata` | 2 | 7 |
| `task/juizo-classifica` | 1 | 14 |
| `task/evidencia-packet` | 1 | 9 |
| `task/orquestra-desfecho` | 1 | 14 |

Cada uma com dois commits: `green eval` e `protected acceptance`.

### As decisões do Pass 4 chegaram ao código

O que o adversário cross-family apontou, seis passes antes, aparece na
implementação:

| Verificação | Resultado |
|---|---|
| As 6 classificações no juízo | ✅ todas |
| Precedência da C30 (controle recusa mesmo classificado) | 14 menções |
| **Tolerância / epsilon** | **0 ocorrências** |
| Os 4 vereditos do ADR 0005 (com `RECUSADO`) | ✅ |
| `localcontext` + `prec` (ADR 0006) | 9 menções |
| `quantize` **uma única vez** (ADR 0004) | ✅ |

O `quantize` aparecendo uma vez só é o ADR 0004 no código: arredonda no
total, não por campo. O `RECUSADO` **não existia** no plano original — nasceu
da objeção C16.

E a orquestração declara na própria docstring o que a C11 e a C17 exigiram:

> *"nunca `sys.exit` dentro de uma etapa — a etapa sempre retorna ou levanta,
> e é `orquestrar` quem decide o desfecho. E o relógio corre uma única vez,
> do início da leitura ao veredito — nunca por etapa somada depois."*

O roteamento de modelo decidiu com dado real: `--model sonnet --effort
medium`, como o `cost-profile.py` previu para esforço M.

**A aceitação é independente** (Barreira E): quem faz não aceita. O registro
tem `attempt_id`, digest e tier próprios, e só então o status vira
`accepted`.

⚠️ **`external_writes` está em `deny`** — por isso `LOCAL_SETTLED` e não
`SETTLED`. O commit existe, o PR não. Para publicar:
`cvg loop --allow-external-writes`.

### 🔴 Achado: o doctor não cobre as dependências dos evals

Três dos quatro bloqueios do Pass 8 foram **ambientais**, não de lógica:

| Bloqueio | O que faltava |
|---|---|
| `pytest: command not found` | pytest no WSL |
| `fatal: empty ident name` | `user.name`/`user.email` no git |
| `ModuleNotFoundError: yaml` | PyYAML |

O `cvg doctor host` verifica git, bash, python3, shellcheck e sha256 — mas
**não confere o que os evals da tarefa importam**. A Task-Spec declara
`required_tools: [git, bash, python3, pytest]` e ninguém valida isso antes
de gastar tentativas de LLM.

O agente chegou a gastar uma tentativa inteira tentando consertar código
que estava certo — o erro era `ModuleNotFoundError`.

⚠️ Também: worktrees de tentativas anteriores **prendem a branch `task/*`** e
bloqueiam o settlement seguinte com *"already used by worktree"*. O loop não
os limpa sozinho.

Os vereditos acima vêm dos **gates**, não do `[+]` do conductor — o conductor
só confere que o arquivo existe.

## Barreira B — vencida

```
reviewer   : Bruno Nunes
reason     : PASSOU com os valores exatos
reviewed_at: 2026-09-17T23:19:52Z
```

O `compile` produziu **6 tarefas** ligadas ao digest do plano revisado — a
sexta nasceu da objeção C14, no Pass 4:

| Tarefa | O que faz |
|---|---|
| `T-20260917-contrato-ancora` | recusa competência sem âncora |
| `T-20260917-leitura-competencia` | lê sem alterar a fonte |
| `T-20260917-agregacao-exata` | soma com meio-para-par |
| `T-20260917-juizo-classifica` | compara e classifica |
| `T-20260917-evidencia-packet` | grava evidência reconstruível |
| `T-20260917-orquestra-desfecho` | conduz o fluxo e decide o desfecho |

Antes da revisão, `compile` devolvia `TASK_GRAPH=BLOCKED` com
`[review_missing]`. A barreira era real.

## Os dois gaps, resolvidos

Ambos os blockers do Pass 1 foram decididos por Bruno Nunes em 17/09/2026:

### GAP-001 — a âncora ✅ resolvido

**Competência 2026-03**, medida na fonte em 2026-09-16 —
[ADR 0002](docs/adrs/0002-the-first-anchor-is-competencia-2026-03-measured-at-source.md):

| Campo | Valor |
|---|---|
| `count_linhas` | 41.719.140 |
| `sum_vl_liquido` | `78771556568.72` |
| `max_vl_liquido` | `60588.24` |
| `linhas_invalidas` | 0 |

Medida por `totais_controle.py` (~46s), **independente do pipeline**.
Evidência: `darkfactory-inss/evidence/_totais-202603.json`.

**Uma divergência foi resolvida medindo, não escolhendo.** A primeira
resposta indicou a competência 2026-08 com este total. O contrato do
`darkfactory-inss` mostrou que o número pertence a **2026-03**, e que não
existe âncora medida para 2026-08. A leitura descartada está registrada no
ADR 0002 — para ninguém re-litigar depois.

### ~~GAP-002 — o arredondamento~~ ✅ resolvido em 17/09/2026

**Meio-para-par (HALF_EVEN)**, a 2 casas, decidido por Bruno Nunes.

Registrado em
[ADR 0001](docs/adrs/0001-money-rounds-half-to-even-at-two-decimals.md), com a
evidência verificada: dos três empates testados, dois divergem em um centavo
entre as duas regras.

## Pass 4 · Consenso 🟢 **GREEN**

```
GATE: GREEN — consensus reached (different-family attack, all objections
resolved, fork named, provenance intact)
CHECK_CONSENSUS=OK
```

Seis rodadas de ataque adversarial, **36 objeções** decididas.

### O que foi preciso para chegar aqui

Dois blockers, ambos derrubados:

**1. Não havia adversário.** `DOCTOR=FAIL`, zero engines. Não há Node de
Linux nesta máquina (o `npm` visível é o do Windows). Resolvido sem `sudo`:
tarball oficial do Node em `~/.local`, depois `@openai/codex` e
`@anthropic-ai/claude-code`.

A autenticação teve duas armadilhas: o `~/.bashrc` do Ubuntu sai na linha 8
quando o shell não é interativo (a chave foi para `~/.profile`), e o `codex`
via a chave no ambiente mas exigia `~/.codex/auth.json` — resolvido com
`printenv OPENAI_API_KEY | codex login --with-api-key`, que lê por stdin.

**2. As duas cadeias discordavam do layout.** O `seamwise` emite lanes como
arquivo plano; o Converge espera diretório com PRD. O gate acusava, mas o
**dispatcher não**: ele montaria o prompt com zero planos.

Resolvido pela ponte em
[`fabrica/ponte/`](../fabrica/ponte/lanes_para_converge.py) — ADR 0003.

### A série de objeções

| Rodada | 1ª | 2ª | 3ª | 4ª | 5ª | 6ª |
|---|---|---|---|---|---|---|
| Objeções | 7 | 6 | 6 | 6 | 5 | 6 |

**Não converge — e isso é esperado.** Um revisor adversarial competente
sempre encontra algo num plano em prosa. O Pass 4 fecha quando o dono decide,
não quando o adversário desiste.

O que mudou foi a **natureza**. As três primeiras rodadas acusavam
**estrutura**; as três últimas, **cobertura de teste**.

### O que as objeções estruturais mudaram

| Achado | Consequência |
|---|---|
| **C11 / C44** — build-order | A correção de C2 criou ciclo entre a primeira e a última tarefa. Encerrar virou decisão de fluxo, não de etapa |
| **C14** — ninguém possui o fluxo | Criada a **sexta costura**, `SEAM-ORQUESTRACAO` |
| **C19** — dois nomes, nenhuma relação | **ADR 0005**: `ACEITO_SEM_ANCORA` é o veredito, `NAO_MEDIDO` é a causa. Daí saiu que os terminais são **quatro** |
| **C12** — granularidade | **ADR 0004**: `2,345+2,345` dá 4,68 por campo e 4,69 no total, ambos meio-para-par |
| **C31** — precisão do contexto | **ADR 0006**: em `prec=6`, `10000.00 + 0.01` vira `10000.0`, e quantizar depois não recupera |

A C31 foi a mais grave: o mesmo defeito do float, por outra porta. O contexto
decimal é global e mutável — qualquer biblioteca importada pode abri-la.

### A decisão de fechamento

**30 objeções corrigidas** no plano. **6 aceitas** com risco declarado por
Bruno Nunes:

> *cobertura de teste se prova no Pass 5 com evals executáveis; um eval só
> vira prova quando existe código que ele execute.*

As seis pedem cenários de teste — e cenário de teste se escreve no Pass 5. É
o que a Barreira C aceita: risco assumido com dono. O que ela não aceita é
objeção **não decidida**.

⚠️ **O conductor mostra `[.] pass 4`** porque procura o log em
`cvg/swimlanes/`, e o nosso está em `cvg/swimlanes/lanes/`. Quem decide é
`cvg review --check`, e ele diz `OK`. *"Evidence presence is not a verdict."*

⚠️ **A âncora veio de outro repositório.** Uma fábrica nova mede a sua
própria: copiar número entre projetos é herdar um fato sem a evidência que o
sustenta.

### Próximo: Pass 5 · Tasking

```bash
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
task-spec-3.8.1/bin/taskspec gate --stamp tasks/T-<id>.md
```

🛑 **Barreira D** — cada folha é autorizada individualmente por HMAC. Não
carimbe `signed_off` nem `accepted` à mão.

## O que já ficou provado

Rodado nesta máquina, não presumido:

- `DOCTOR_HOST=OK` — a máquina assina, faz bind, loop e settle
- O gate do Pass 0 **acusa** 6 defeitos diferentes, incluindo sign-off
  `pending` no lugar de `canonical`
- O gate do Pass 1 **acusa** blocker sem resolução substantiva
- O roteamento de modelo existe em código: FAST→Haiku, NORMAL→Sonnet,
  FULL→Opus (`converge/skills/task-to-runtime-contract/scripts/cost-profile.py:52`)
- O gate do Pass 4 **acusava** duas vezes sem engine nenhum:
  `CHECK_CONSENSUS=EMPTY` por falta de log, e o check [5] por falta de PRD de
  lane. Fail-closed confirmado na prática — nenhum dos dois cedeu a atalho,
  e os dois só abriram depois que o bloqueio real foi resolvido
- O adversário cross-family **acha defeito que o autor não vê**: em seis
  rodadas, 36 objeções, incluindo um ciclo de construção que uma correção
  minha criou (C11) e a perda de centavo por precisão de contexto (C31) —
  o mesmo defeito do float, por outra porta
- **O ciclo de consenso não converge sozinho.** 7 → 6 → 6 → 6 → 5 → 6. Fecha
  quando o dono decide, não quando o adversário desiste
- O gate do Pass 5 **executa** os evals em vez de ler o spec, e distingue
  *eval quebrado* de *eval que falha corretamente*: `0 pass / 4 fail; fails
  are expected for unbuilt work`
- O selo HMAC **acusa** edição pós-carimbo: alterando o spec, `DO NOT
  DELEGATE — signed_off_sig HMAC mismatch`; restaurado, volta a `OK(Tier 1)`
- A política de caminho do Pass 8 **recusou um eval verde** porque um
  `.coverage` caiu fora do escopo autorizado — *"Do not open a PR. Do not
  hack the eval."*

## Publicado

[github.com/nobruster/darkfactory-template](https://github.com/nobruster/darkfactory-template)
— `main` em `0e129d4` e as 6 branches `task/*`, hash conferido um a um
contra o remote.

**Nada mesclado.** As branches ficam para revisão. Os PRs não foram abertos —
o `gh` CLI não está instalado nesta máquina.

## O que ainda não foi provado

⚠️ **O código nunca rodou contra dado real.** A âncora de 2026-03 veio do
`darkfactory-inss`, e `_raw/` está vazio. Os 58 testes provam a lógica dos
seis módulos; **não provam que a fábrica confere uma competência**.

O primeiro gate da própria doutrina continua de pé: sem fonte conectada e
âncora medida aqui, o contrato desta fábrica seria `NAO_MEDIDO`.

⚠️ **`external_writes: deny`** — foi o que manteve tudo em `LOCAL_SETTLED` em
vez de `SETTLED`. Para publicar PRs pelo loop:
`cvg loop --allow-external-writes`.

## Para retomar

1. Revisar as 6 branches e decidir os merges
2. Conectar uma fonte real em `_raw/` (imutável, chmod 444 + sha256)
3. Medir a âncora **dessa** fonte, por fora do pipeline — copiar número entre
   projetos é herdar um fato sem a evidência que o sustenta
4. Rodar o fluxo completo numa competência e conferir o veredito

⚠️ **Antes de qualquer loop**, rode o pré-voo — ele existe porque três dos
quatro bloqueios do Pass 8 foram ambientais:

```bash
python3 fabrica/ponte/checar_deps.py cvg/tasks/T-*.md
```
