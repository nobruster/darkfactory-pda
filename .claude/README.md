# Ambiente de agentes — o que tem aqui e o que usar

630 arquivos: **50 agentes**, 18 comandos, 26 skills, base de conhecimento com
**25 domínios**, mais o loop de desenvolvimento (`dev/`) e o registro de
sessões (`telemetry/`).

Reunião de dois projetos:

| Origem | O que trouxe |
|---|---|
| **btc-zero-prd-claude-code** | 28 agentes (data engineering, workflow SDD, AWS), 9 comandos, KB de infra, `dev/`, `telemetry/` |
| **Semana AI Data Engineer** | 19 agentes, 26 skills, KB do stack de RAG/multi-agente |

Nada foi removido — mas nem tudo serve para uma fábrica de dados. Este índice
separa o que é núcleo do que é herança, para você não perder tempo procurando.

> Onde os dois projetos tinham o mesmo agente, **a versão do btc-zero
> prevaleceu** (projeto mais recente, voltado a engenharia de dados).

> Regras de conduta da fábrica: [`../AGENTS.md`](../AGENTS.md).
> Este arquivo é só o mapa do ferramental.

---

## 🟢 Núcleo — use numa fábrica de dados

### Comece por aqui

| Recurso | Para quê |
|---|---|
| [`/fabrica-run`](commands/workflow/fabrica-run.md) | **BRD → entrega pelo motor real.** Aciona `cvg`/`taskspec`/`seamwise`, com roteamento Opus/Sonnet/Haiku por lane |
| [`/nova-fabrica`](commands/core/nova-fabrica.md) | Monta o ferramental de uma fábrica nova |
| [`fabrica-architect`](agents/domain/fabrica-architect.md) | **Usa o que existe, cria o que falta.** Inventaria antes de criar, e registra o que cria |

### ⚠️ Há duas cadeias neste repositório — não as confunda

| | Ciclo SDD (`.claude/`) | Motor real (`converge/`, `task-spec/`, `seamwise/`) |
|---|---|---|
| O que é | 6 prompts markdown | ~2.000 linhas de bash/Python/Go |
| Comandos | `/brainstorm` → `/define` → … → `/ship` | [`/fabrica-run`](commands/workflow/fabrica-run.md) |
| Modelo | `model:` no frontmatter, **estático** | **roteado por lane**, em código |
| Gates | score que o LLM calcula | scripts que reprovam de verdade |
| Entrega | arquiva markdown | `git push` + `gh pr create` |
| Avança sozinho | **não** — você digita cada fase | o loop sim; as barreiras param de propósito |

**Para produzir documento**, use o ciclo SDD. **Para entregar software com
prova**, use `/fabrica-run`.

O `/ship` arquiva documentação — **não abre PR**. Quem entrega é o Pass 8 do
`cvg loop`.

Se a demanda não tem recurso correspondente, é o `fabrica-architect` que
decide entre usar, estender ou criar — e cria seguindo os padrões deste
repositório, em vez de improvisar.

### Agentes — engenharia de dados

Os mais diretamente aplicáveis a uma fábrica.

| Agente | Para quê |
|---|---|
| [`data-engineering/medallion-architect`](agents/data-engineering/medallion-architect.md) | **Bronze → Silver → Gold.** O padrão de camadas da fábrica |
| [`data-engineering/spark-specialist`](agents/data-engineering/spark-specialist.md) | Spark em geral |
| [`data-engineering/spark-performance-analyzer`](agents/data-engineering/spark-performance-analyzer.md) | Gargalos e custo (diagnóstico) |
| [`data-engineering/pipeline-performance-guardian`](agents/data-engineering/pipeline-performance-guardian.md) | **Performance com prova**: mede jobs e o pipeline inteiro pelo event log (skew, spill, shuffle) e só aceita otimização com `PERF=MELHOR` **e** resultado idêntico. Nunca tira reconferência |
| [`data-engineering/spark-troubleshooter`](agents/data-engineering/spark-troubleshooter.md) | Job que falha ou trava |
| [`data-engineering/spark-streaming-architect`](agents/data-engineering/spark-streaming-architect.md) | Ingestão contínua |
| [`data-engineering/delta-lake-specialist`](agents/data-engineering/delta-lake-specialist.md) | **Delta Lake open-source** (3.2.1, Spark + S3A/MinIO): gravar/ler medalhão com commit atômico, `replaceWhere`, linhagem por versão e reconferência. Não é Databricks |
| [`data-engineering/lakeflow-architect`](agents/data-engineering/lakeflow-architect.md) | Desenho de pipeline declarativo (Databricks) |
| [`data-engineering/lakeflow-pipeline-builder`](agents/data-engineering/lakeflow-pipeline-builder.md) | Construção do pipeline |
| [`domain/pipeline-architect`](agents/domain/pipeline-architect.md) | Arquitetura de pipeline ponta a ponta |
| [`domain/extraction-specialist`](agents/domain/extraction-specialist.md) | Extração de fonte difícil |
| [`domain/dataops-builder`](agents/domain/dataops-builder.md) | Operação e automação |

### Agentes — fluxo de trabalho (SDD)

Ciclo completo, com comando próprio para cada etapa:

| Etapa | Agente | Comando |
|---|---|---|
| 1. Explorar | [`brainstorm-agent`](agents/workflow/brainstorm-agent.md) | `/brainstorm` |
| 2. Definir | [`define-agent`](agents/workflow/define-agent.md) | `/define` |
| 3. Desenhar | [`design-agent`](agents/workflow/design-agent.md) | `/design` |
| 4. Construir | [`build-agent`](agents/workflow/build-agent.md) | `/build` |
| 5. Iterar | [`iterate-agent`](agents/workflow/iterate-agent.md) | `/iterate` |
| 6. Entregar | [`ship-agent`](agents/workflow/ship-agent.md) | `/ship` |

Artefatos em `sdd/`. O `dev/` guarda o loop de desenvolvimento (prompts, logs,
progresso) e o `telemetry/` registra as sessões.

### Agentes — qualidade e código

| Agente | Para quê |
|---|---|
| [`code-quality/code-reviewer`](agents/code-quality/code-reviewer.md) | Revisão de qualidade, segurança e manutenibilidade |
| [`code-quality/dual-reviewer`](agents/code-quality/dual-reviewer.md) | Revisão dupla (estática + arquitetural) |
| [`code-quality/test-generator`](agents/code-quality/test-generator.md) | Gerar testes — **útil para provar que o juiz acusa** |
| [`code-quality/python-developer`](agents/code-quality/python-developer.md) | Escrever e refatorar Python |
| [`code-quality/code-cleaner`](agents/code-quality/code-cleaner.md) | Remover código morto e duplicação |
| [`code-quality/code-documenter`](agents/code-quality/code-documenter.md) | Docstrings e documentação de repo |
| [`code-quality/shell-script-specialist`](agents/code-quality/shell-script-specialist.md) | Makefile e scripts de pipeline |
| [`exploration/codebase-explorer`](agents/exploration/codebase-explorer.md) | Entender um repositório desconhecido |
| [`exploration/kb-architect`](agents/exploration/kb-architect.md) | Estruturar a base de conhecimento |
| [`communication/the-planner`](agents/communication/the-planner.md) | Quebrar trabalho em plano executável |
| [`ai-ml/ai-data-engineer`](agents/ai-ml/ai-data-engineer.md) | Pipelines de dados com IA |
| [`ai-ml/ai-prompt-specialist`](agents/ai-ml/ai-prompt-specialist.md) | Escrever e afinar prompts |

### Comandos

| Comando | Para quê |
|---|---|
| [`/nova-fabrica`](commands/core/nova-fabrica.md) | Monta o ferramental de uma fábrica nova |
| [`/brainstorm`](commands/workflow/brainstorm.md) · [`/define`](commands/workflow/define.md) · [`/design`](commands/workflow/design.md) | Ciclo SDD: explorar → definir → desenhar |
| [`/build`](commands/workflow/build.md) · [`/iterate`](commands/workflow/iterate.md) · [`/ship`](commands/workflow/ship.md) | Ciclo SDD: construir → iterar → entregar |
| [`/dev`](commands/dev/dev.md) | Loop de desenvolvimento com prompt e log |
| [`/create-pr`](commands/workflow/create-pr.md) | Abrir pull request |
| [`/telemetry`](commands/core/telemetry.md) | Registro da sessão |
| [`/review`](commands/review/review.md) | Revisão de código |
| [`/memory`](commands/core/memory.md) | Gerenciar memória do projeto |
| [`/sync-context`](commands/core/sync-context.md) | Sincronizar contexto do repositório |
| [`/readme-maker`](commands/core/readme-maker.md) | Gerar/atualizar README |
| [`/create-kb`](commands/knowledge/create-kb.md) | Criar base de conhecimento nova |

### Skills

| Skill | Para quê |
|---|---|
| [`delta-lake`](skills/delta-lake/SKILL.md) | Gravar, ler, reconferir, evoluir e manter camadas de medalhão em Delta OSS — `/delta-lake gravar silver 2026-01` |
| [`spark-perf`](skills/spark-perf/SKILL.md) | Medir job/pipeline Spark pelo event log e decidir com `PERF=MELHOR\|IGUAL\|PIOR\|NAO_MEDIDO` contra baseline — `/spark-perf comparar <eventlog> <job>`. Script de referência testado em [`medir_eventlog.py`](skills/spark-perf/medir_eventlog.py) |
| [`audit`](skills/audit/SKILL.md) | Auditoria técnica com severidade P0–P3 |
| [`harden`](skills/harden/SKILL.md) | Endurecer código contra falhas |
| [`critique`](skills/critique/SKILL.md) | Crítica estruturada |
| [`optimize`](skills/optimize/SKILL.md) | Performance **de UI** (frontend). Para Spark, use `spark-perf` |
| [`clarify`](skills/clarify/SKILL.md) | Desambiguar requisito |
| [`distill`](skills/distill/SKILL.md) | Reduzir ao essencial |
| [`shape`](skills/shape/SKILL.md) | Dar forma a um problema aberto |
| [`adapt`](skills/adapt/SKILL.md) | Adaptar solução a outro contexto |

### Base de conhecimento

| Domínio | Conteúdo |
|---|---|
| [`kb/delta-lake`](kb/delta-lake/) | Delta Lake OSS 3.2.1: log de transações, schema imposto, constraints, time travel/retenção, `replaceWhere`, linhagem, reconferência |
| [`kb/spark-performance`](kb/spark-performance/) | Spark 3.5 + Delta 3.2.1: event log (campos exatos), skew, spill, shuffle, `exceptAll` por dentro, controles numa passada, tamanho de arquivo, gate `PERF=` |
| [`kb/terraform`](kb/terraform/) · [`kb/terragrunt`](kb/terragrunt/) | Infraestrutura como código |
| [`kb/gcp`](kb/gcp/) | Google Cloud |
| [`kb/python`](kb/python/) | Padrões e idiomas |
| [`kb/testing`](kb/testing/) | Estratégia e padrões de teste |
| [`kb/architecture`](kb/architecture/) | Design de sistemas, trade-offs, escalabilidade |
| [`kb/prompt-engineering`](kb/prompt-engineering/) | Técnicas de prompt |
| [`kb/pydantic`](kb/pydantic/) | Validação e contratos de dados |
| [`kb/exploration`](kb/exploration/) | Como explorar código desconhecido |
| [`kb/communication`](kb/communication/) | Analogias, audiência, divulgação progressiva |

**`kb/pydantic` e `kb/testing` são os mais diretamente aplicáveis ao juiz** —
contrato de dados e prova de que o gate acusa.

---

## 🟡 Herança do curso — específico do ShopAgent

Mantido para referência. Não tem uso direto numa fábrica de dados, mas serve
de exemplo de como o ferramental foi construído.

| O que | Onde | Observação |
|---|---|---|
| Agentes de slides | `agents/domain/aide-slide-*` (4) | Apresentações do curso |
| Agentes do ShopAgent | `agents/domain/shopagent-builder`, `crewai-specialist` | Projeto do curso |
| Comandos de slides | `/build-slides`, `/review-slides`, `/meeting` | — |
| Skills de design visual | `banner-design`, `slides`, `colorize`, `typeset`, `animate`, `layout`, `polish`, `brand`, `design`, `design-system`, `frontend-design`, `ui-styling`, `ui-ux-pro-max`, `bolder`, `quieter`, `delight`, `impeccable`, `overdrive` | ~18 skills de UI |
| KB do stack do curso | `kb/chainlit`, `kb/crewai`, `kb/langchain`, `kb/llamaindex`, `kb/qdrant`, `kb/langfuse`, `kb/deepeval`, `kb/supabase`, `kb/shadowtraffic`, `kb/genai`, `kb/aide-slides` | Stack de RAG/multi-agente |
| Specs do ShopAgent | `sdd/features/*SHOPAGENT*`, `sdd/reports/*SHOPAGENT*` | Day 3 e Day 4 |
| Specs do BTC-Zero | `sdd/` (45 arquivos) | Produto do curso btc-zero |
| Agentes AWS | `agents/aws/` (4) | Úteis se a fábrica rodar em AWS |
| Agentes de extração BTC | `agents/domain/function-developer`, `infra-deployer` | Do produto btc-zero |
| KB de LLM/API | `kb/gemini`, `kb/openrouter` | Se a fábrica não usa LLM, ignore |

### ⚠️ Os dois CLAUDE.md herdados

Nenhum dos dois descreve a darkfactory:

| Arquivo | Descreve |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | ShopAgent (Semana AI Data Engineer) |
| [`CLAUDE-btc-zero.md`](CLAUDE-btc-zero.md) | Produto BTC-Zero |

Foram mantidos como vieram, por referência. **Ao usar este template num
projeto novo, reescreva o `CLAUDE.md` para o projeto** — ou aponte para o
[`../AGENTS.md`](../AGENTS.md), que tem as regras da fábrica.

---

## Como usar

Agentes, comandos e skills ficam ativos assim que o Claude Code abre na raiz
do repositório. Skills com `user-invocable: true` são chamadas por `/nome`.

Numa fábrica nova, o caminho mais curto:

```
/nova-fabrica <domínio>   # inventaria, cria o que falta, registra
```

Ou passo a passo:

```
/create-kb                # base de conhecimento do domínio
the-planner               # quebrar o trabalho
python-developer          # construir
/audit + code-reviewer    # antes de confiar no verde
```

**Se não existe recurso para a demanda**, chame o `fabrica-architect`: ele
inventaria os 19 agentes, 26 skills e 20 domínios de KB antes de criar
qualquer coisa — e o que criar entra indexado aqui.

**A ordem importa.** O juiz vem antes do pipeline — ver
[`../README.md`](../README.md).

---

## Procedência

Copiado de `semana-ai-data-engineer/.claude` em 17/09/2026, 453 arquivos,
íntegro. Varredura de segredos executada: nenhuma credencial, nenhum `.env`.
