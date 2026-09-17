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
| 3 · Decompose | `seamwise compile` | 🟢 `TASK_GRAPH=READY` — 5 tarefas |
| 4 · Consensus | `cvg review --check` | 🔴 `CHECK_CONSENSUS=EMPTY` — 🛑 **parado** |
| 5 · Tasking | `taskspec gate --stamp` | ⬜ |
| 7 · Bind | `cvg bind` | ⬜ |
| 8 · Loop | `cvg loop` | ⬜ |

Os vereditos acima vêm dos **gates**, não do `[+]` do conductor — o conductor
só confere que o arquivo existe.

## Barreira B — vencida

```
reviewer   : Bruno Nunes
reason     : PASSOU com os valores exatos
reviewed_at: 2026-09-17T23:19:52Z
```

O `compile` produziu **5 tarefas** ligadas ao digest do plano revisado:

| Tarefa | O que faz |
|---|---|
| `T-20260917-contrato-ancora` | recusa competência sem âncora |
| `T-20260917-leitura-competencia` | lê sem alterar a fonte |
| `T-20260917-agregacao-exata` | soma com meio-para-par |
| `T-20260917-juizo-classifica` | compara e classifica |
| `T-20260917-evidencia-packet` | grava evidência reconstruível |

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

## Pass 4 · Consenso 🛑 **parado — dois blockers medidos**

Rodado nesta máquina em 17/09/2026. Nenhum dos dois foi contornado.

### Blocker 1 — não há adversário nesta máquina

```
$ cvg doctor
  SKIP  codex   (openai)    not installed (codex)
  SKIP  kimi    (moonshot)  not installed (kimi)
  SKIP  claude  (anthropic) not installed (claude)
engines ready: 0   cross-family: 0
DOCTOR=FAIL
```

O Pass 4 exige **≥ 2 engines, ≥ 1 de família diferente** da autora
(anthropic). O `dispatch-review.sh` chama a **CLI própria** do engine, que
se autentica sozinha — a sessão do Claude Code **não serve**: ela não é um
binário no PATH. Nenhum `node` de Linux nesta máquina (o `npm` visível é o
do Windows, em `/mnt/c`), então instalar uma CLI via npm exige passo extra.

Sem engine, `cvg review --adversary` devolve `REVIEW=SKIP` e não escreve
log. Sem log, o gate para:

```
$ check-consensus-gate.sh --dir cvg/swimlanes/workspace/seamwise/swimlanes
GATE: no objection log at .../.consensus/objection-log.json
CHECK_CONSENSUS=EMPTY
```

**Não se fabrica o objection-log à mão.** O gate confere a família do
adversário, re-hasheia os planos que ele atacou e exige `decided_by` humano
por objeção. Escrever o log manualmente é a Regra 3 — editar o oráculo para
o portão passar. É justamente o que quebrou em 2026-08-03.

### Blocker 2 — as duas cadeias discordam do layout das lanes

Independente do engine, e mais silencioso. O `seamwise` emite lanes como
**arquivos planos**:

```
seamwise/swimlanes/LANE-CONTRATO.md
```

O Converge espera lanes como **subdiretórios com PRD**:

```
swimlanes/<seam>/_lane.md      (canônico)
swimlanes/swimlane-<seam>/swimlane-<seam>.plan.md   (legado)
```

Consequência medida:

| Componente | Padrão | Resultado no layout atual |
|---|---|---|
| `dispatch-review.sh` | `<tree>/*/*.md` | **zero planos** — o adversário atacaria o vazio |
| gate, check [5] | `<seam>/_lane.md` | `FAIL` — "no swimlane PRDs … nothing to gate" |

O gate **acusa** (check [5] falha), então isto não passa despercebido. Mas o
dispatcher **não acusa**: ele montaria o prompt sem nenhum plano e o
adversário produziria objeções sobre nada. O gate depois recusaria por outro
motivo — o resultado certo pela razão errada.

É a costura aberta que o `AGENTS.md` registra na Regra 1.6: *"as duas cadeias
ainda não se chamam"*. Aqui ela tem um custo concreto e reproduzível.

### Para destravar

1. Instalar uma CLI cross-family (`codex` ou `kimi`) no **Linux/WSL**, não no
   Windows. `cvg doctor` precisa dizer `DOCTOR=OK`.
2. Decidir a ponte de layout — e **registrar em ADR**, porque é decisão
   vinculante entre duas ferramentas de terceiros:
   - adaptador em `fabrica/` que projeta as lanes planas do seamwise na
     forma `<seam>/_lane.md` que o Converge gatea (Regra 1, opção 1); ou
   - editar direto o `converge/` vendorizado — cujo upstream saiu do ar —
     e anotar a divergência no `VENDORED.md`.

   A primeira preserva as duas cópias; a segunda é mais curta e o
   `converge/` é o único onde editar direto é o caminho normal.
3. Só então `cvg review --adversary`, e uma decisão humana por objeção.

⚠️ O dispatch precisa rodar **de dentro do WSL**, com:

```bash
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
```

⚠️ **A âncora veio de outro repositório.** Uma fábrica nova mede a sua
própria: copiar número entre projetos é herdar um fato sem a evidência que o
sustenta.

## O que já ficou provado

Rodado nesta máquina, não presumido:

- `DOCTOR_HOST=OK` — a máquina assina, faz bind, loop e settle
- O gate do Pass 0 **acusa** 6 defeitos diferentes, incluindo sign-off
  `pending` no lugar de `canonical`
- O gate do Pass 1 **acusa** blocker sem resolução substantiva
- O roteamento de modelo existe em código: FAST→Haiku, NORMAL→Sonnet,
  FULL→Opus (`converge/skills/task-to-runtime-contract/scripts/cost-profile.py:52`)
- O gate do Pass 4 **acusa** duas vezes sem engine nenhum: `CHECK_CONSENSUS=EMPTY`
  por falta de log, e o check [5] por falta de PRD de lane. Fail-closed confirmado
  na prática — nenhum dos dois cede a um atalho
