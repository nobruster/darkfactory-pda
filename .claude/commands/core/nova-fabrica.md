---
description: Monta o ferramental de uma fábrica nova — inventaria o que já existe, cria o que falta (agente, skill, comando ou KB) e registra tudo.
argument-hint: "[domínio da fábrica, ex: receita-cnpj]"
---

# /nova-fabrica

Monta ou completa o ferramental de uma fábrica de dados para o domínio
`$ARGUMENTS`.

Use o agente [`fabrica-architect`](../../agents/domain/fabrica-architect.md).
Ele conhece o ciclo **INVENTARIAR → DECIDIR → CRIAR → REGISTRAR** e os padrões
deste repositório.

## Antes de tudo

Leia [`AGENTS.md`](../../../AGENTS.md) na raiz. As 7 regras valem aqui, e duas
governam este comando:

- **Sem oráculo, não se constrói.** Nenhum recurso criado pode servir para
  pular essa etapa.
- **Não edite dentro dos submódulos.** `converge/` é a exceção (vendorizado).

## O que fazer

1. **Inventarie** o que já existe antes de criar qualquer coisa — 19 agentes,
   8 comandos, 26 skills, 20 domínios de KB. O índice
   [`.claude/README.md`](../../README.md) separa o núcleo da herança do curso.
2. **Decida** por recurso: usar o que existe, estender o próximo, ou criar.
   Duplicar é pior que não criar.
3. **Crie** o que faltar seguindo os padrões existentes — nunca invente
   estrutura nova.
4. **Registre** em `.claude/README.md` (e em `kb/_index.yaml`, se for KB).

## A ordem de montagem

O juiz vem **antes** do pipeline:

1. Entender a fonte — catalogue os defeitos, não corrija
2. KB do domínio (`/create-kb`)
3. Contrato e oráculo — nasce `NAO_MEDIDO`, e a fábrica recusa construir
4. O juiz — `pytest fabrica/tests/ -v` prova que ele **acusa**
5. O pipeline — Makefile só encadeia
6. Gates (`converge/`) e tarefas assinadas (`task-spec/`)
7. Auditar — `/audit` e `code-reviewer`
8. `docs/MANUAL.md` — fábrica sem manual é reprovada

## Ao final

Diga o que foi inventariado, o que foi criado, onde ficou e como invocar.
Se houver lacuna que você não preencheu, diga qual e por quê.
