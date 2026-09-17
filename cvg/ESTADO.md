# Estado da descida — exemplo de fábrica

Onde o caso de exemplo parou, e o que falta para destravar.
Atualizado em 17/09/2026.

> **Este é um caso real em aberto**, não uma demonstração. Os dois blockers
> abaixo esperam decisão do dono e foram mantidos `open` de propósito.

## Posição

| Passe | Gate | Veredito |
|---|---|---|
| 0 · Capture | `cvg capture` | 🟢 `CHECK_BRD=PASS` |
| 1 · Intent | `cvg intent` | 🟢 `CHECK_TECH_SPEC=PASS` |
| 2 · Structure | `cvg structure --final` | 🟢 `CHECK_ADR=OK` |
| 3 · Decompose | `seamwise plan` | ⬜ **próximo** |
| 4 · Consensus | `cvg review` | ⬜ 🛑 barreira |
| 5 · Tasking | `taskspec gate --stamp` | ⬜ |
| 7 · Bind | `cvg bind` | ⬜ |
| 8 · Loop | `cvg loop` | ⬜ |

Os três vereditos acima vêm dos **gates**, não do `[+]` do conductor — o
conductor só confere que o arquivo existe.

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

## Próximo passo: Pass 3 · Decompose

```bash
cvg next --guided     # aponta: pass 3 · Decompose (skill reqs-to-swimlane-plans)
```

Aqui a stack finalmente é decidida — até o Pass 2 tudo ficou acima dela. Só o
**Seamwise** decompõe (token `COMPOSE`), e ele para em
`DELIVERY_PLAN=NEEDS_REVIEW`.

🛑 **Barreira B** — a decomposição exige revisor nomeado:

```bash
seamwise review --accept --reviewer <nome> --reason <motivo>
```

Depois vem a **Barreira C (Pass 4 · Consenso)**, a mais dura: um modelo
adversário ataca o plano, e **cada objeção precisa de decisão humana** —
corrigir ou aceitar o risco conscientemente. O `cvg` recusa se não conseguir
atribuir `decided_by`.

⚠️ **Esta âncora veio de outro repositório.** Uma fábrica nova mede a sua
própria: copiar número entre projetos é herdar um fato sem a evidência que o
sustenta.

Precisa rodar **de dentro do WSL**, com:

```bash
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
```

## O que já ficou provado

Rodado nesta máquina, não presumido:

- `DOCTOR_HOST=OK` — a máquina assina, faz bind, loop e settle
- O gate do Pass 0 **acusa** 6 defeitos diferentes, incluindo sign-off
  `pending` no lugar de `canonical`
- O gate do Pass 1 **acusa** blocker sem resolução substantiva
- O roteamento de modelo existe em código: FAST→Haiku, NORMAL→Sonnet,
  FULL→Opus (`converge/skills/task-to-runtime-contract/scripts/cost-profile.py:52`)
