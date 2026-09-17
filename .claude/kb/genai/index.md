# GenAI Architecture Knowledge Base

> **Purpose**: Architecture patterns for GenAI systems -- multi-agent orchestration, agentic workflows, RAG, chatbots, LLM pipelines
> **MCP Validated**: 2026-02-17

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/multi-agent-systems.md](concepts/multi-agent-systems.md) | Agent orchestration patterns: hub-spoke, mesh, sequential, concurrent |
| [concepts/rag-architecture.md](concepts/rag-architecture.md) | RAG pipeline design: chunking, embedding, retrieval, generation |
| [concepts/state-machines.md](concepts/state-machines.md) | Finite state machines for conversational flow control |
| [concepts/tool-calling.md](concepts/tool-calling.md) | LLM function/tool calling protocols and execution |
| [concepts/guardrails.md](concepts/guardrails.md) | Safety guardrails: input/output filtering, topic control |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/agentic-workflow.md](patterns/agentic-workflow.md) | Multi-step agent workflow with plan-and-execute |
| [patterns/chatbot-architecture.md](patterns/chatbot-architecture.md) | Production chatbot with state management and routing |
| [patterns/rag-pipeline.md](patterns/rag-pipeline.md) | End-to-end RAG with hybrid search and reranking |
| [patterns/evaluation-framework.md](patterns/evaluation-framework.md) | LLM evaluation with LLM-as-judge and RAGAS metrics |

### Specs (Machine-Readable)

| File | Purpose |
|------|---------|
| [specs/genai-patterns.yaml](specs/genai-patterns.yaml) | Architecture patterns specification with decision matrix |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) - Fast lookup tables

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Multi-Agent Systems** | Orchestration of specialized LLM agents with handoff protocols |
| **RAG Architecture** | Retrieval-augmented generation for grounded responses |
| **State Machines** | Deterministic conversation flow with LLM-powered transitions |
| **Tool Calling** | Structured function invocation from LLM reasoning |
| **Guardrails** | Safety layers for input validation and output filtering |

---

## Learning Path

| Level | Files |
|-------|-------|
| **Beginner** | concepts/tool-calling.md, concepts/rag-architecture.md |
| **Intermediate** | concepts/multi-agent-systems.md, patterns/rag-pipeline.md |
| **Advanced** | patterns/agentic-workflow.md, patterns/evaluation-framework.md |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| genai-architect | patterns/agentic-workflow.md, patterns/chatbot-architecture.md | Design multi-agent and chatbot systems |
| genai-architect | patterns/rag-pipeline.md, concepts/rag-architecture.md | Build RAG pipelines with evaluation |
