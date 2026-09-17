# Ambiente de agentes — o que tem aqui e o que usar

453 arquivos: 19 agentes, 8 comandos, 26 skills e uma base de conhecimento com
20 domínios.

Veio inteiro do projeto **Semana AI Data Engineer (ShopAgent)**. Nada foi
removido — mas nem tudo serve para uma fábrica de dados. Este índice separa o
que é núcleo do que é herança, para você não perder tempo procurando.

> Regras de conduta da fábrica: [`../AGENTS.md`](../AGENTS.md).
> Este arquivo é só o mapa do ferramental.

---

## 🟢 Núcleo — use numa fábrica de dados

### Comece por aqui

| Recurso | Para quê |
|---|---|
| [`/nova-fabrica`](commands/core/nova-fabrica.md) | Monta o ferramental de uma fábrica nova |
| [`fabrica-architect`](agents/domain/fabrica-architect.md) | **Usa o que existe, cria o que falta.** Inventaria antes de criar, e registra o que cria |

Se a demanda não tem recurso correspondente, é o `fabrica-architect` que
decide entre usar, estender ou criar — e cria seguindo os padrões deste
repositório, em vez de improvisar.

### Agentes

| Agente | Para quê |
|---|---|
| [`code-quality/code-reviewer`](agents/code-quality/code-reviewer.md) | Revisão de qualidade, segurança e manutenibilidade |
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
| [`/review`](commands/review/review.md) | Revisão de código |
| [`/memory`](commands/core/memory.md) | Gerenciar memória do projeto |
| [`/sync-context`](commands/core/sync-context.md) | Sincronizar contexto do repositório |
| [`/readme-maker`](commands/core/readme-maker.md) | Gerar/atualizar README |
| [`/create-kb`](commands/knowledge/create-kb.md) | Criar base de conhecimento nova |

### Skills

| Skill | Para quê |
|---|---|
| [`audit`](skills/audit/SKILL.md) | Auditoria técnica com severidade P0–P3 |
| [`harden`](skills/harden/SKILL.md) | Endurecer código contra falhas |
| [`critique`](skills/critique/SKILL.md) | Crítica estruturada |
| [`optimize`](skills/optimize/SKILL.md) | Performance |
| [`clarify`](skills/clarify/SKILL.md) | Desambiguar requisito |
| [`distill`](skills/distill/SKILL.md) | Reduzir ao essencial |
| [`shape`](skills/shape/SKILL.md) | Dar forma a um problema aberto |
| [`adapt`](skills/adapt/SKILL.md) | Adaptar solução a outro contexto |

### Base de conhecimento

| Domínio | Conteúdo |
|---|---|
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
| Specs do ShopAgent | `sdd/` (8 arquivos) | Day 3 e Day 4 |

⚠️ **[`CLAUDE.md`](CLAUDE.md) ainda descreve o ShopAgent**, não a darkfactory.
Foi mantido como veio. Ao usar este template num projeto novo, reescreva-o
para o projeto — ou aponte para o [`../AGENTS.md`](../AGENTS.md).

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
