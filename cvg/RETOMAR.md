# Onde parei — 23/09/2026, madrugada

Descida do **medalhão** (Bronze, Silver, Gold) sobre a partição já
publicada no lago. Leia [`MEDALHAO.md`](MEDALHAO.md) para o detalhe; isto
aqui é só para retomar sem reconstruir contexto.

## Posição

| Passe | Gate | Veredito |
|---|---|---|
| 3 · Decompose | `seamwise map` | 🟢 `SEAM_MAP=READY` |
| 4 · Consensus | `cvg review --check` | 🔴 **RED** — o plano mudou na R13 |
| 5 · Tasking | `taskspec gate --stamp` | 🟡 selado, mas sobre texto antigo |
| 7 · Bind | `cvg bind --check` | 🟡 idem |
| 8 · Loop | `cvg loop` | 🛑 Bronze deu `blocked`, e o plano foi corrigido |

⚠️ **O Pass 4 está RED de propósito.** Corrigi o plano na R13 e não
re-rodei o adversário — os hashes moveram e a procedência quebrou, como
deve. Não é defeito: é o preço de mexer no plano, e a Regra 10 manda
pagá-lo em vez de afrouxar a cerca.

## O comando para retomar

**De dentro do WSL Ubuntu-24.04**, com os overrides:

```bash
cd ~/darkfactory-pda
export PATH="$HOME/.local/bin:$PATH"
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
export CVG_SEAMWISE_BIN="$PWD/.bin/seamwise"
export SEAMWISE_WORKSPACE=/tmp/ws-medalhao
```

⚠️ **O workspace `/tmp/ws-medalhao` some ao reiniciar a máquina.** Se
sumir, recrie com `bash ~/cadeia_medalhao.sh`, que roda
map → plan → review → compile e devolve `TASK_GRAPH=READY`.

## O próximo passo, na ordem

1. **Rodada 14 do adversário** — `bash ~/adversario13.sh` (renomeie o eco)

   **O critério de parada já está definido**, e defini antes de ver o
   resultado para não racionalizar depois:

   > Se a rodada trouxer **só** as famílias `contrato-pendente` e
   > `storage`, **fecho**. Se trouxer classe nova, corrijo e sigo.

2. **Fechar o Pass 4** — `python3 ~/fechar_pass4.py` gera o script de
   decisão a partir do log, com razão própria por objeção; depois
   `bash ~/decidir_pass4.sh`

3. **Recompor e re-selar** — `bash ~/pass5_prepare.sh`,
   `~/pass5_completar.sh`, `~/pass5_selar.sh`

4. **Re-bindar** — `bash ~/pass7_bind.sh`

5. **Pass 8** — `bash ~/pass8_bronze.sh`, e **ler o receipt**, não a tela

## As duas lacunas que não são do plano resolver

Elas reaparecem em toda rodada, e vão reaparecer até alguém decidir
**fora** do plano:

| | O que falta | De quem é |
|---|---|---|
| contrato | o mapa código→descrição dos 11 colapsos | **decisão sua** — medir é técnico (`scripts/medir_colapso.py` já sabe), aprovar é de negócio |
| storage | atomicidade da publicação, estabilidade dos objetos | Pass 8, contra o mecanismo que ele escolher |

Declarar o mapa sem aprovador e data seria inventar referencial — a
Regra 2. Por isso ficou pendente em vez de resolvido.

## O que já foi declarado no contrato, e como

Toquei `contracts/`, que é cercado. Provei que não afrouxei:

```
ORACULO=INTACTO
  ancora, cardinalidade, layout, procedencia, defeitos_conhecidos,
  competencia — byte a byte iguais
  politica_decimal SÓ GANHOU campos
  120 testes passando
```

- `particionamento` — remedido no lago naquela sessão, não inferido
- `politica_decimal.emax/emin` — 999999/-999999, o limite que **não
  interfere**, com contraexemplo executado

## Publicação

| | |
|---|---|
| `darkfactory-pda` | publicado até `354689aa`; **há commits novos depois** |
| `darkfactory-template` | `NAO_MEDIDO` — o `ls-remote` dele falha enquanto o do PDA responde |

```bash
cd ~/darkfactory-pda && git push origin task/orquestra-desfecho
cd ~/darkfactory-template && git push origin main
```

⚠️ **Publique do seu terminal.** O Git Credential Manager é GUI e pendura
para sempre quando chamado de sessão não-interativa — medido: `exit=124`,
stdout e stderr vazios, e `GIT_TERMINAL_PROMPT=0` não resolve porque não é
prompt de terminal.

## O estado do ambiente

| | |
|---|---|
| `pda-minio`, `pda-spark` | de pé; o Spark tem `pytest 8.3.4` e `pyspark 3.5.9` |
| `tests/` no contêiner | montado (`:ro`), corrigido nesta sessão |
| lago | `competencia=2026-01` bate com a âncora ao centavo; `fatia-teste` isolada |
| 120 testes | passando |

## ⚠️ O padrão que custou treze rodadas

```
R3  → R8   escopo sem orçamento
R8  → R9   contexto sem DefaultContext
R9  → R11  piso sem contar
R11 → R12  exigência sem fonte
R12 → R13  contexto em dois de três
```

**Cada correção minha virou o achado da rodada seguinte** — porque eu
corrigia a junta apontada sem testar a própria correção contra o mesmo
tipo de ataque. Quando testei (`1 de 5`, `4 de 5`, `5 de 5`, `5 com
falha`), o furo apareceu na hora.

Se retomar corrigindo algo: **teste a correção, não só o defeito.**
