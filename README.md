# Dark Factory — Template

Ambiente padrão para novos projetos de **fábrica de dados**: pipelines que
rodam sozinhos, provam que o resultado está certo e recusam publicar quando
não conseguem provar.

Este repositório não é uma fábrica. É a **bancada**: as ferramentas, os
padrões e o exemplo de referência a partir dos quais uma fábrica nova nasce.

> Fábrica de referência já em produção:
> [`nobruster/darkfactory-inss`](https://github.com/nobruster/darkfactory-inss)
> — 41,7 milhões de linhas por competência, 5 defeitos de origem catalogados,
> 8 ADRs.

---

## A regra que governa tudo

> **Sem juiz, não se constrói. Preserve o defeito. Recuse o lote.
> Verde pelo motivo certo.**

Quatro consequências práticas, e elas valem para qualquer fábrica gerada
daqui:

1. **Sem oráculo, não se constrói.** Um número que ninguém viu ser medido é
   indistinguível de um palpite. Uma fábrica nova nasce com o contrato
   `NAO_MEDIDO` e **recusa rodar** até alguém medir a fonte.
2. **Preserve o defeito.** A fonte tem erros reais. A fábrica **classifica**,
   nunca corrige em silêncio — corrigir destrói a prova de que a origem tem um
   problema, e sem prova ninguém cobra quem mandou o dado errado.
3. **Dinheiro é Decimal, nunca float.** `0.1 + 0.2 != 0.3` em binário, e é
   assim que um centavo some sem nada acusar.
4. **Quando um gate reprova, investigue — nunca ajuste a expectativa para
   fazer passar.** É a única coisa proibida sem exceção.

---

## O que tem aqui

| Componente | O que é | Origem |
|---|---|---|
| [`.claude/`](.claude/) | **Ambiente de agentes** — 50 agentes, 18 comandos, 26 skills, KB de 25 domínios | herdado |
| [`fabrica/`](fabrica/) | **O juiz** — oráculo + golden-match. O núcleo: 6 classificações, zero tolerância. | próprio |
| [`converge/`](converge/) | Motor de convergência e gates (`cvg`) | vendorizado |
| [`task-spec/`](task-spec/) | Tarefas assinadas (HMAC) — v3.9.0, traz o TaskMesh | vendorizado |
| [`task-spec-3.8.1/`](task-spec-3.8.1/) | ⚠️ A versão que o `cvg` exige (3.8.x exato) | vendorizado |
| [`brief-spec/`](brief-spec/) | Especificação de briefings para agentes | vendorizado |
| [`seamwise/`](seamwise/) | Skills e costura entre agentes | vendorizado |
| [`uc-northwind-pay-edp/`](uc-northwind-pay-edp/) | Caso de uso completo de referência (legado × moderno) | vendorizado |

### Não há submódulos

Todo o conteúdo está versionado direto aqui. `git clone` traz tudo de uma vez
— sem `--recurse-submodules`, sem pasta vazia.

As cinco pastas acima vieram de repositórios de
[@luanmorenommaciel](https://github.com/luanmorenommaciel), congeladas no
commit indicado no `VENDORED.md` de cada uma:

| Pasta | Commit | Upstream | Licença |
|---|---|---|---|
| [`converge/`](converge/VENDORED.md) | `f6df8af` | ⚠️ fora do ar (404) | MIT |
| [`brief-spec/`](brief-spec/VENDORED.md) | `93d51b4` | ativo | MIT |
| [`seamwise/`](seamwise/VENDORED.md) | `a49748e` | ativo | MIT |
| [`task-spec/`](task-spec/VENDORED.md) | `76ff7b8` | ativo | MIT |
| [`uc-northwind-pay-edp/`](uc-northwind-pay-edp/VENDORED.md) | `868f1c1` | ativo | ⚠️ sem LICENSE |

**O que isso custa:** não há `git submodule update` — atualizar qualquer uma
delas é trabalho manual contra o upstream, e o histórico original não veio
junto.

### O ambiente de agentes

`.claude/` traz o ferramental que vem junto do template, ativo assim que o
Claude Code abre na raiz do repositório. Os mais relevantes para uma fábrica:

- **`medallion-architect`** — bronze → silver → gold, o padrão de camadas
- **Spark e Lakeflow** (7 agentes) — pipeline, performance, troubleshooting
- **Ciclo SDD** — `/brainstorm` → `/define` → `/design` → `/build` →
  `/iterate` → `/ship`
- **`fabrica-architect`** — usa o que existe, cria o que falta

Reúne dois projetos (btc-zero e Semana AI Data Engineer), e **parte é
específica deles** (slides, CrewAI, produto BTC). O índice em
[`.claude/README.md`](.claude/README.md) separa o núcleo de fábrica da
herança — comece por ele.

---

## Clonar

```bash
git clone https://github.com/nobruster/darkfactory-template.git
cd darkfactory-template
```

Só isso. Sem flags, sem passo extra — tudo vem no clone.

---

## Começar: o juiz primeiro

A ordem importa. O juiz vem **antes** do pipeline — sem ele, automação é só um
agente rodando solto.

```bash
cd fabrica

# 1. Provar que o juiz ACUSA quando deve (12 testes)
python -m pytest tests/ -v

# 2. Ver o veredito num resultado
python judge/run_judge.py \
  --oracle contracts/oracles/exemplo-lote-001.json \
  --actual /caminho/do/resultado.json
```

Saída em `evidence/<batch_id>/golden-match.json`, e exit **0** (verde) ou
**1** (empacado).

O teste mais importante é `tests/test_judge_fails_red.py`: ele não testa se o
juiz aprova, testa se ele **acusa**. Um portão que nunca falhou não é um
portão — é decoração que dá falsa confiança.

Detalhes completos em [`fabrica/README.md`](fabrica/README.md).

---

## As seis classificações

Toda diferença encontrada recebe exatamente uma:

| Código | Significa | Bloqueia? |
|---|---|---|
| `CONFIRMED_SOURCE_DEFECT` | A fonte mentiu | Não — explicado |
| `CONFIRMED_LEGACY_DEFECT` | O sistema em que você confiava está errado | Não — explicado |
| `APPROVED_BEHAVIOR_CHANGE` | Mudou de propósito, aprovado | Não — explicado |
| `MODERN_DEFECT` | Seu código está errado | **Sim** |
| `CONTRACT_AMBIGUITY` | O contrato não decide | **Sim** |
| `UNRESOLVED` | Não classificado | **Sim** |

Não existe parâmetro de tolerância em lugar nenhum. É deliberado: tolerância
configurável é como um centavo inexplicado vira um centavo aceito.

---

## O roadmap de uma fábrica

| Etapa | O que entra |
|---|---|
| 1 | **O juiz** — oráculo + golden-match |
| 2 | Fases 0, 3 e 6 no pipeline real |
| 3 | Determinismo (mesmo hash) + ambiente limpo |
| 4 | O loop (fila, tick, stall, cron) |
| 5 | Evidência + PR + revisão matinal |
| 6 | Apagar as luzes |

---

## Estrutura de uma fábrica gerada

O que o `darkfactory-inss` tem e toda fábrica nova deve ter:

```
_raw/         bytes originais (chmod 444 + sha256) — escrita proibida
contracts/    O JUIZ — oráculos, âncoras, schemas — escrita proibida
docs/adrs/    decisões vinculantes — revisão se faz com ADR novo
docs/MANUAL.md  como operar ESTA fábrica
lakehouse/    bronze → silver → gold
evidence/     pacotes por execução
tasks/        Task-Specs assinadas
scripts/      evals executáveis
Makefile      só encadeia — nada de lógica dentro dele
```

**O Makefile só encadeia.** Nada de `curl` ou `sed` com regra de negócio: o
que decide fica em script Python versionado e testável.

---

## Para o agente que trabalha neste repositório

Se você é um agente (Hermes, Claude Code, Codex) operando aqui, leia
[`AGENTS.md`](AGENTS.md) antes de alterar qualquer coisa. Os pontos que mais
causam estrago:

- **Não edite arquivos dentro dos submódulos** achando que está editando este
  repo. Eles são repositórios de terceiros — mudança ali vira commit no lugar
  errado.
- **Nunca edite um oráculo para um gate passar.** É a manobra mais perigosa
  que existe.
- **Objeção de auditoria é hipótese, não veredito.** Meça antes de corrigir.
  No `darkfactory-inss`, uma das nove objeções bloqueantes foi refutada — e a
  "correção" teria partido São Paulo em 27 municípios com o total continuando
  a bater.

---

## Licença

O conteúdo próprio (`fabrica/`) segue a licença deste repositório. Cada
submódulo mantém a sua própria licença, definida no repositório de origem.
