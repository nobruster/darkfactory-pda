# Pass 3 · Decompose — as costuras

Aqui a stack finalmente é decidida. Até o Pass 2 tudo ficou acima dela.

Só o **Seamwise** decompõe (token `COMPOSE`). Ele mapeia as costuras reais do
sistema, cria uma raia por costura, e **para** pedindo revisão humana.

## O que roda aqui

```bash
./.bin/seamwise map --source cvg/swimlanes/fabrica-recipe.yaml
./.bin/seamwise plan
./.bin/seamwise review --accept --reviewer <nome> --reason <motivo>
./.bin/seamwise compile
```

⚠️ **De dentro do WSL.** O `.bin/seamwise` é um wrapper local — o Seamwise
não está instalado no sistema, e o wrapper o roda da pasta vendorizada sem
instalar nada.

## Estado atual

```
SEAM_MAP=READY              5 costuras mapeadas
DELIVERY_PLAN=NEEDS_REVIEW  🛑 barreira B
TASK_GRAPH=BLOCKED          compile recusa sem revisão
```

Verificado: rodar `compile` sem revisão devolve

```
[plan_not_ready]  Delivery plan is not marked ready.
[review_missing]  An accepted delivery-plan review is required.
TASK_GRAPH=BLOCKED
```

Não é contornável. A revisão precisa de **nome** e **motivo** — o plano
sozinho não se aprova.

## As 5 costuras

| Costura | Responsabilidade | Prova independente |
|---|---|---|
| `SEAM-CONTRATO-ANCORA` | guardar a âncora e recusar sem ela | competência sem âncora → `NAO_MEDIDO`, exit ≠ 0 |
| `SEAM-LEITURA` | ler sem alterar a fonte | sha256 idêntico antes e depois |
| `SEAM-AGREGACAO` | somar com aritmética exata | float recusado; HALF_EVEN ≠ HALF_UP |
| `SEAM-JUIZO` | comparar e classificar | um centavo alterado é recusado |
| `SEAM-EVIDENCIA` | registrar de forma reconstruível | veredito reconstruído sem reexecutar |

O **steel thread** encadeia as cinco na ordem em que provam o caminho
completo.

## ⚠️ O workspace fica aqui, não em `seamwise/`

`seamwise init` grava o workspace no diretório corrente. Rodado da raiz, ele
escreveu 23 arquivos **dentro de `seamwise/`** — que é pasta vendorizada de
terceiros, e a [Regra 1](../../AGENTS.md) proíbe.

Foram movidos para [`workspace/`](workspace/). Ao rodar de novo, confira que
`git status seamwise/` continua vazio.

## Regras do schema que custam tempo

O `recipe.schema.json` exige mínimos que só aparecem ao validar:

| Campo | Mínimo |
|---|---|
| `behavior` por tarefa | 2 |
| `evals` por tarefa | **3** |
| `anti_patterns` por tarefa | **3** |
| `rejected_alternatives` por costura | 1 |
| `do_not_touch` por tarefa | 1 |

E `claim` aceita só `current`, `proposed`, `derived`, `external` — não
`internal`.

A mensagem de erro é boa: *"Repair the authored recipe without inventing
missing facts."* Preencher para satisfazer o schema é o oposto do que ele
pede.

## Próximo

🛑 **Barreira B** — alguém precisa revisar o plano e assinar:

```bash
./.bin/seamwise review --accept --reviewer "<nome>" --reason "<motivo>"
```

Depois vem a **Barreira C (Pass 4 · Consenso)**, a mais dura: um modelo
adversário ataca o plano e cada objeção precisa de decisão humana.
