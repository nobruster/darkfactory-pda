# GenAI Architecture Quick Reference

> Fast lookup tables. For code examples, see linked files.
> **MCP Validated:** 2026-02-17

## Orchestration Patterns

| Pattern | Topology | Best For | Complexity |
|---------|----------|----------|------------|
| Sequential | Chain | Step-by-step pipelines | Low |
| Concurrent | Fan-out | Independent parallel tasks | Medium |
| Hub-and-Spoke | Star | Centralized coordination | Medium |
| Mesh | Peer-to-peer | Resilient distributed systems | High |
| Plan-and-Execute | Hierarchical | Cost-optimized multi-step | High |

## RAG Pipeline Stages

| Stage | Input | Output | Key Tools |
|-------|-------|--------|-----------|
| Chunking | Documents | Text chunks | LangChain, LlamaIndex |
| Embedding | Chunks | Vectors | OpenAI, Cohere, Sentence-Transformers |
| Indexing | Vectors | Vector store | Pinecone, Weaviate, ChromaDB, pgvector |
| Retrieval | Query | Relevant chunks | Hybrid search, MMR |
| Reranking | Candidates | Ranked results | Cohere Rerank, Cross-encoders |
| Generation | Context + Query | Answer | GPT-4, Claude, Gemini |

## Tool Calling Protocols

| Protocol | Provider | Transport | Status |
|----------|----------|-----------|--------|
| Function Calling | OpenAI | JSON Schema | Production |
| Tool Use | Anthropic | JSON Schema | Production |
| MCP | Anthropic (open) | Streamable HTTP | Production |
| Function Calling | Google | JSON Schema | Production |

## Guardrail Types

| Type | Layer | Purpose | Example |
|------|-------|---------|---------|
| Input rails | Pre-LLM | Filter harmful prompts | Jailbreak detection |
| Output rails | Post-LLM | Validate responses | Hallucination check |
| Topic rails | Pre-LLM | Restrict conversation scope | Off-topic blocking |
| Retrieval rails | Mid-pipeline | Filter retrieved content | Relevance threshold |

## Evaluation Metrics

| Metric | Measures | Range | Framework |
|--------|----------|-------|-----------|
| Faithfulness | Grounding in context | 0-1 | RAGAS |
| Answer Relevancy | Query-answer alignment | 0-1 | RAGAS |
| Context Precision | Retrieved relevance | 0-1 | RAGAS |
| Context Recall | Coverage of ground truth | 0-1 | RAGAS |
| Toxicity | Harmful content | 0-1 | Langfuse |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| Simple Q&A over docs | Basic RAG pipeline |
| Multi-step research | Agentic workflow with tool calling |
| Customer support bot | State machine + RAG + guardrails |
| Data pipeline monitoring | Multi-agent crew with escalation |
| Content generation | LLM chain with evaluation loop |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Use frontier models for every step | Plan-and-Execute with model tiering |
| Skip evaluation metrics | Implement RAGAS + LLM-as-judge from day one |
| Build monolithic agents | Compose specialized agents with clear handoffs |
| Ignore guardrails in production | Layer input, output, and topic rails |
| Chunk documents blindly | Use semantic chunking with overlap |

## Related Documentation

| Topic | Path |
|-------|------|
| Multi-Agent Design | `concepts/multi-agent-systems.md` |
| RAG Fundamentals | `concepts/rag-architecture.md` |
| Full Index | `index.md` |
