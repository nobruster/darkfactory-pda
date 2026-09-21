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

## `checar_deps.py`

Confere as dependências dos evals **antes** de rodar o loop.

```bash
python3 fabrica/ponte/checar_deps.py cvg/tasks/T-*.md
```

Token final: `DEPS=OK | DEPS=MISSING | DEPS=ERROR`.

### O problema que ela resolve

O `cvg doctor host` verifica o que a **máquina** precisa — git, bash,
python3, shellcheck, sha256. Não confere o que os **evals da tarefa**
importam.

Medido no Pass 8 desta fábrica: **três dos quatro bloqueios foram
ambientais**, não de lógica.

| Bloqueio | O que faltava |
|---|---|
| `pytest: command not found` | pytest |
| `fatal: empty ident name` | identidade git |
| `ModuleNotFoundError: yaml` | PyYAML |

O custo não é o erro — é o que ele faz o loop fazer. **O agente gastou uma
tentativa inteira de LLM consertando código que estava correto**, porque a
mensagem que chegou até ele foi `ModuleNotFoundError`, não "falta uma
dependência no ambiente".

### O que confere

1. `required_tools` do frontmatter — cada um no PATH
2. Todo `import` dos testes que os evals invocam — importa de verdade
3. Identidade git (`user.name`/`user.email`) — o settlement commita

### Ele acusa — testado

```
FALTA ferramenta pytest                      DEPS=MISSING
FALTA módulo modulo_que_nao_existe           DEPS=MISSING
FALTA identidade git — falta user.name       DEPS=MISSING
```

⚠️ **Antes do trabalho existir, os testes não existem** — não há import a
conferir, e a lista de `required_tools` é o que segura a verificação. O
script diz isso em vez de fingir cobertura completa.

## Ao escrever outra ponte aqui

1. **Meça a discordância** antes de escrever — qual componente procura o quê,
   com arquivo:linha.
2. **Acuse a própria defasagem.** Um `--check` com token estável, não um
   script que só copia.
3. **Registre em ADR**, com a leitura rejeitada e a evidência que a matou.
4. **Não toque nas pastas vendorizadas.** Se a ponte não resolve por fora, o
   problema é outro.
