# Instruções para agentes

Leia isto antes de alterar qualquer coisa neste repositório.

Este arquivo vale para qualquer agente que opere aqui — Hermes, Claude Code,
Codex, Cursor. O `CLAUDE.md` aponta para cá.

---

## O que este repositório é

A **bancada** a partir da qual nascem fábricas de dados. Não é uma fábrica: é
o juiz, as ferramentas e o exemplo de referência.

Estrutura:

- `fabrica/` — conteúdo próprio
- `.claude/` — ambiente de agentes
- `converge/`, `brief-spec/`, `seamwise/`, `task-spec/`,
  `uc-northwind-pay-edp/` — **vendorizadas**: cópias de repositórios de
  terceiros, versionadas direto aqui

**Não há submódulos.** `git clone` traz tudo.

---

## Regra 1 — Código de terceiros: edite com consciência

As cinco pastas vendorizadas vieram de repositórios de
[@luanmorenommaciel](https://github.com/luanmorenommaciel), congeladas num
commit específico (ver o `VENDORED.md` de cada uma).

Editar ali **gera commit normal deste repositório** — não se perde nada, ao
contrário de quando eram submódulos. Mas duas coisas mudam:

1. **A cópia diverge do upstream.** Quatro dos cinco repositórios continuam
   ativos; quanto mais você edita, mais caro fica comparar ou trazer
   atualizações.
2. **Atualizar é manual.** Não existe `git submodule update`. É buscar o
   upstream e reconciliar à mão.

Por isso, antes de editar dentro de uma pasta vendorizada, prefira:

1. Camada de adaptação em `fabrica/`
2. Issue ou PR no upstream, quando ele ainda existe
3. Só então, editar direto — e registre no `VENDORED.md` o que divergiu

⚠️ `converge/` é o único cujo upstream **saiu do ar** (HTTP 404). Ali não há
para onde mandar PR, e editar direto é o caminho normal.

---

## Regra 1.5 — Use o que existe antes de improvisar

O repositório traz 50 agentes, 18 comandos, 26 skills e 25 domínios de KB em
`.claude/`. Antes de escrever solução do zero, **procure**:

```bash
ls .claude/agents/*/ .claude/skills/ .claude/kb/
grep -ril "<termo>" .claude/
```

Índice comentado em [`.claude/README.md`](.claude/README.md) — ele separa o
núcleo de fábrica da herança dos projetos de origem (slides, CrewAI, produto
BTC). Para pipeline, comece pelos agentes de `data-engineering/`.

**Se não existe recurso para a demanda, crie** — não improvise um
atalho descartável. O agente
[`fabrica-architect`](.claude/agents/domain/fabrica-architect.md) faz isso:
inventaria, decide entre usar/estender/criar, cria seguindo os padrões
existentes e **registra no índice**. Recurso criado e não indexado é recurso
perdido.

Atalho: `/nova-fabrica <domínio>`.

---

## Regra 1.6 — Duas cadeias: saiba qual você está usando

Este repositório tem **duas metodologias paralelas**, e confundi-las faz você
achar que entregou quando só escreveu markdown.

| | Ciclo SDD (`.claude/`) | Motor real |
|---|---|---|
| Comandos | `/brainstorm` → `/define` → … → `/ship` | `/fabrica-run` (`cvg`, `taskspec`, `seamwise`) |
| Natureza | prompts markdown | código executável |
| Modelo | `model:` estático no frontmatter | **roteado por lane**: FAST→Haiku, NORMAL→Sonnet, FULL→Opus |
| Gates | score que o próprio LLM calcula | scripts que reprovam de verdade |
| Entrega | arquiva documentação | `git push` + `gh pr create` |

**`/ship` não abre PR.** Ele copia markdown para `archive/`. Quem entrega
software é o Pass 8 (`cvg loop`).

**Para entregar com prova, use [`/fabrica-run`](.claude/commands/workflow/fabrica-run.md).**
Ele exige `taskspec` e `cvg` instalados — ter as pastas não basta.

⚠️ As duas cadeias **ainda não se chamam**: os agentes de `.claude/workflow/`
não invocam `cvg`. Ligá-las de fato é trabalho em aberto; por ora, a escolha
é sua, na hora de começar.

---

## Regra 2 — Sem oráculo, não se constrói

Uma fábrica nova nasce com contrato `NAO_MEDIDO` e **recusa rodar** até alguém
medir a fonte.

Não gere a âncora automaticamente para "desbloquear". Um número que ninguém
viu ser medido é indistinguível de um palpite, e palpite no lugar do total faz
o gate comparar contra nada e publicar `ACEITO`.

---

## Regra 3 — Nunca edite o oráculo para um gate passar

A manobra mais perigosa que existe. Quando um gate reprova, o trabalho é
**investigar**, nunca ajustar a expectativa.

Se o número mudou legitimamente, alguém do negócio re-aprova e o `approved_at`
muda junto. Um gate que nunca falhou não é um gate — é decoração que dá falsa
confiança.

Isto vale igualmente para: afrouxar uma tolerância, marcar um teste como
`skip`, ampliar um intervalo aceito, ou trocar a comparação por uma mais
permissiva.

---

## Regra 4 — Preserve o defeito

A fonte tem erros reais. A fábrica **classifica**, nunca corrige em silêncio.

Corrigir destrói a prova de que a origem tem um problema — e sem prova ninguém
consegue cobrar quem mandou o dado errado.

Toda diferença recebe exatamente uma das seis classificações
(`CONFIRMED_SOURCE_DEFECT`, `CONFIRMED_LEGACY_DEFECT`,
`APPROVED_BEHAVIOR_CHANGE`, `MODERN_DEFECT`, `CONTRACT_AMBIGUITY`,
`UNRESOLVED`). Não classificar **bloqueia**.

---

## Regra 5 — Dinheiro é Decimal, nunca float

`0.1 + 0.2 != 0.3` em binário. É assim que um centavo some sem nada acusar.

O juiz **recusa** float em campo monetário. Dinheiro trafega como string ou
`Decimal`, e o arredondamento é explícito (`HALF_EVEN` vs `HALF_UP` é decisão
de contrato, não de implementação).

---

## Regra 6 — Leia o contrato, nunca o código antigo

Ao substituir um sistema legado, a especificação é o **contrato**. Ler o código
antigo para entender a regra faz você copiar o bug junto — e o juiz classifica
isso como `MODERN_DEFECT`, que **bloqueia**.

---

## Regra 7 — Objeção de auditoria é hipótese, não veredito

Meça antes de corrigir.

No `darkfactory-inss`, três modelos auditaram a estrutura e levantaram nove
objeções bloqueantes. **Uma foi refutada**: o número estava certo e a conclusão
invertida — a "correção" teria partido São Paulo em 27 municípios, com o total
continuando a bater e nada acusando.

---

## O que está cercado

**Neste repositório**, [`.claude/settings.json`](.claude/settings.json) nega
escrita em:

| Caminho | Por quê |
|---|---|
| `fabrica/contracts/`, `fabrica/judge/`, `fabrica/tests/` | O juiz. Editar o oráculo para um portão passar é a manobra mais perigosa que existe |
| `converge/bin/`, `converge/skills/task-loop/scripts/`, `task-spec/src/`, `seamwise/src/` | Os motores. Um agente que edita o próprio verificador é *specification-gaming* |
| `.cvg/gate.yaml`, `.claude/settings.json` | As próprias cercas. Cerca que o agente afrouxa não é cerca |
| `.github/workflows/` | Quem roda a verificação no CI |

**Numa fábrica gerada**, acrescente também — e nas **duas** cercas:

```
_raw/         bytes originais (chmod 444 + sha256)
contracts/    o juiz daquela fábrica
docs/adrs/    decisões vinculantes
evidence/     pacotes por execução
```

⚠️ **Duas cercas, uma doutrina.** `.claude/settings.json` (o agente) e
`.cvg/gate.yaml` (o gate) precisam concordar; divergência é defeito. No
`darkfactory-inss` um script confere isso — uma auditoria já encontrou as duas
discordando, com `docs/adrs/` e `evidence/` faltando de um lado. **Uma fábrica
nova deve ter o seu verificador de cercas.**

**Revisão de ADR se faz com ADR novo, nunca editando o antigo.** Um ADR
corrigido em silêncio apaga o registro de que a decisão mudou — e o motivo da
mudança é a parte que importa.

---

## Makefile: só encadeia

Nada de `curl`, `sed` ou lógica de negócio dentro do Makefile. O que decide
fica em script Python versionado e testável. O Makefile só chama, na ordem.

---

## Antes de dar commit

```bash
cd fabrica && python -m pytest tests/ -v
```

Os 12 testes provam que o juiz **acusa**. Se algum falhar, o juiz está cego —
e um juiz cego aprova tudo.

Se você alterou algo dentro de uma pasta vendorizada, anote a divergência no
`VENDORED.md` dela — é o que permite reconciliar com o upstream depois.
