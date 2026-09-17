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

### GAP-001 — a âncora · **parcial**

Uma âncora tem três partes. Duas estão respondidas:

| Parte | Estado |
|---|---|
| Competência | ✅ 2026-08 (mês fechado anterior) |
| Aprovador | ✅ Bruno Nunes |
| Total | ⚠️ **declarado, não medido** — R$ 78.771.556.568,72 |

Registrado no [ADR 0002](docs/adrs/0002-the-first-anchor-is-competencia-2026-08-approved-by-bruno-nunes.md),
com status `proposed` — e é por isso que `cvg structure --final` reprova.

**Por que ainda não fecha.** O número foi *declarado*, não *medido*: não há
comando que releia a origem e o reproduza, porque nenhuma fonte está
conectada (`_raw/` vazio). Declaração e medição não são a mesma prova.

🔴 **Divergência a resolver antes de aceitar.** Esse mesmo valor aparece no
`darkfactory-inss` como total da competência **2026-03**, não 2026-08
(`darkfactory-inss/CLAUDE.md:33` — verificado). Uma das duas leituras está
errada. **Meça antes de escolher** — pegar a mais conveniente é exatamente o
que a Regra 7 proíbe.

### ~~GAP-002 — o arredondamento~~ ✅ resolvido em 17/09/2026

**Meio-para-par (HALF_EVEN)**, a 2 casas, decidido por Bruno Nunes.

Registrado em
[ADR 0001](docs/adrs/0001-money-rounds-half-to-even-at-two-decimals.md), com a
evidência verificada: dos três empates testados, dois divergem em um centavo
entre as duas regras.

## Como destravar

Falta **medir** o total da competência 2026-08 na origem:

1. Conectar a fonte — o arquivo da competência 2026-08 em `_raw/`, imutável
   (chmod 444 + sha256)
2. Medir o total **por fora do pipeline**, com um comando que releia o
   arquivo e imprima o número. Esse comando vira a seção `Evidence` do
   ADR 0002
3. Resolver a divergência 2026-08 × 2026-03 — o que a medição mostrar, vale
4. Promover o ADR 0002 de `proposed` para `accepted`
5. No `tech-spec-exemplo-fabrica.md`: `resolution:` substantiva no GAP-001 e
   veredito `canonical`
6. Fechar: `cvg structure --final` e depois `cvg intent`

⚠️ **O passo 2 não pode ser o pipeline.** Medir com o pipeline é o pipeline
conferindo a si mesmo — o gate passa a comparar o resultado contra o próprio
resultado, e o defeito comum às duas execuções fica invisível.

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
