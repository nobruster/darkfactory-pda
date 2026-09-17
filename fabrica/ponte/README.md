# Ponte — adaptadores entre ferramentas de terceiros

Camada de adaptação da **opção 1 da Regra 1**: quando duas pastas vendorizadas
discordam, o conserto vem para cá, não para dentro delas.

## `lanes_para_converge.py`

Projeta as lanes planas do Seamwise no layout de diretório que o Converge
gateia.

```bash
# entre `seamwise plan` e `cvg review --adversary`
python3 fabrica/ponte/lanes_para_converge.py \
  --de   cvg/swimlanes/workspace/seamwise/swimlanes \
  --para cvg/swimlanes/lanes

# antes de despachar o adversário — precisa dizer OK
python3 fabrica/ponte/lanes_para_converge.py --check \
  --de   cvg/swimlanes/workspace/seamwise/swimlanes \
  --para cvg/swimlanes/lanes
```

Token final: `PONTE_LANES=OK | STALE | EMPTY | ERROR`.

### O problema que ela resolve

| Componente | Procura | No layout plano |
|---|---|---|
| `check-consensus-gate.sh:189` | `<dir>/_lane.md` | **FAIL** — acusa |
| `dispatch-review.sh:86` | `<dir>/*/*.md` | **0 arquivos, sem erro** |

O segundo é o perigoso: o adversário atacaria o vazio e o gate recusaria
depois por outro motivo — o resultado certo pela razão errada.

Medido nesta máquina:

```
layout plano     → FAIL no swimlane PRDs — nothing to gate     · dispatcher vê 0
layout projetado → ok fork line present at the top of all 5 PRDs · dispatcher vê 5
```

Decisão e leituras rejeitadas em
[ADR 0003](../../cvg/docs/adrs/0003-seamwise-lanes-are-projected-into-the-converge-dir-per-lane-layout.md).

### Por que projeta, e por que a cópia não mente

O Seamwise **regrava** `swimlanes/` a cada `plan` — mover quebraria o
`compile`. A projeção é derivada e descartável.

Symlink seria mais barato, mas `git config core.symlinks` é **false** aqui: no
Windows o link versionado vira um arquivo de texto com o caminho dentro, e o
gate leria o caminho como se fosse o PRD.

Como é cópia, cada `_lane.md` carrega o `sha256` da origem e `--check`
recompara. Testado:

```
DEFASADO LANE-JUIZO.md — a origem mudou desde a projeção   PONTE_LANES=STALE
FALTA    LANE-CONTRATO.md -> .../contrato/_lane.md         PONTE_LANES=STALE
```

Uma ponte que não acusasse a própria defasagem seria pior que nenhuma ponte.

### ⚠️ Regras de uso

- **`cvg/swimlanes/lanes/` é derivado.** Não edite ali — a próxima projeção
  sobrescreve. Edite a recipe e rode `seamwise plan`.
- **`--check` precisa dizer `OK` antes do dispatch.** `STALE` significa que o
  Seamwise regravou e a projeção ficou para trás.
- **Isto não destrava o Pass 4.** Resolve o layout; o adversário cross-family
  (`DOCTOR=FAIL`) continua faltando.

## Ao escrever outra ponte aqui

1. **Meça a discordância** antes de escrever — qual componente procura o quê,
   com arquivo:linha.
2. **Acuse a própria defasagem.** Um `--check` com token estável, não um
   script que só copia.
3. **Registre em ADR**, com a leitura rejeitada e a evidência que a matou.
4. **Não toque nas pastas vendorizadas.** Se a ponte não resolve por fora, o
   problema é outro.
