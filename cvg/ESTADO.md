# Estado da descida — exemplo de fábrica

Onde o caso de exemplo parou, e o que falta para destravar.
Atualizado em 17/09/2026.

> **Este é um caso real em aberto**, não uma demonstração. Os dois blockers
> abaixo esperam decisão do dono e foram mantidos `open` de propósito.

## Posição

| Passe | Gate | Veredito |
|---|---|---|
| 0 · Capture | `cvg capture` | 🟢 `CHECK_BRD=PASS` |
| 1 · Intent | `cvg intent` | 🔴 `CHECK_TECH_SPEC=FAIL` — **parado aqui** |
| 2 · Structure | `cvg structure` | 🟢 `CHECK_ADR=OK` |
| 3 · Decompose | `seamwise plan` | ⬜ |
| 4 · Consensus | `cvg review` | ⬜ 🛑 barreira |
| 5 · Tasking | `taskspec gate --stamp` | ⬜ |
| 7 · Bind | `cvg bind` | ⬜ |
| 8 · Loop | `cvg loop` | ⬜ |

⚠️ `cvg next --guided` mostra `[+] pass 1` e `PASS_PRE=OK` para o Pass 2.
**Isso não quer dizer aprovado** — o conductor só vê que o arquivo existe.
Quem decide é `cvg intent`, e ele reprovou.

## O que trava

`cvg intent` acusa dois blockers em
[`docs/tech-spec/tech-spec-exemplo-fabrica.md`](docs/tech-spec/tech-spec-exemplo-fabrica.md):

### GAP-001 — a âncora

> Qual competência do passado será a primeira âncora, e quem do negócio
> confirma que aquele número foi conferido e fechado?

Bloqueia **R-1**: sem âncora medida, não há o que comparar. O contrato nasce
`NAO_MEDIDO` e a fábrica recusa construir.

**Não gere a âncora automaticamente para desbloquear.** Um número que ninguém
viu ser medido é indistinguível de um palpite — e palpite no lugar do total
faz o gate comparar contra nada e publicar `ACEITO`.

### ~~GAP-002 — o arredondamento~~ ✅ resolvido em 17/09/2026

**Meio-para-par (HALF_EVEN)**, a 2 casas, decidido por Bruno Nunes.

Registrado em
[ADR 0001](docs/adrs/0001-money-rounds-half-to-even-at-two-decimals.md), com a
evidência verificada: dos três empates testados, dois divergem em um centavo
entre as duas regras.

## Como destravar

Falta **só o GAP-001**:

1. Responda: qual competência do passado é a primeira âncora, e quem do
   negócio confirma que aquele número foi conferido e fechado?
2. Em `tech-spec-exemplo-fabrica.md`, troque `resolution: "open"` do GAP-001
   pela resposta (substantiva — ver a armadilha no
   [README do Pass 1](docs/tech-spec/README.md))
3. Mude o veredito de sign-off para `canonical`
4. Registre a âncora como ADR novo no Pass 2 (`scaffold-adr.sh`), e rode
   `cvg structure --final` para exigir todos os ADRs em `accepted`
5. `converge/bin/cvg intent cvg/docs/tech-spec/tech-spec-exemplo-fabrica.md`

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
