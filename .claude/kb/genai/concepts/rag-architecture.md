# RAG Architecture

> **Purpose**: Retrieval-Augmented Generation pipeline design for grounded LLM responses
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Retrieval-Augmented Generation (RAG) grounds LLM responses in external knowledge by retrieving relevant documents before generation. This eliminates hallucination for factual queries, enables domain-specific answers without fine-tuning, and keeps responses current with updated knowledge bases. The pipeline has four core stages: chunking, embedding, retrieval, and generation.

## The Pattern

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Chunk:
    text: str
    metadata: dict
    embedding: Optional[list[float]] = None
    score: Optional[float] = None

@dataclass
class RAGConfig:
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 10
    rerank_top_n: int = 5
    similarity_threshold: float = 0.7
    embedding_model: str = "text-embedding-3-small"
    generation_model: str = "gpt-4o"

class RAGPipeline:
    def __init__(self, config: RAGConfig):
        self.config = config

    def chunk(self, document: str) -> list[Chunk]:
        """Split document into overlapping chunks."""
        chunks = []
        for i in range(0, len(document), self.config.chunk_size - self.config.chunk_overlap):
            text = document[i:i + self.config.chunk_size]
            chunks.append(Chunk(text=text, metadata={"offset": i}))
        return chunks

    def retrieve(self, query: str, chunks: list[Chunk]) -> list[Chunk]:
        """Retrieve top-k chunks by similarity, then rerank."""
        # Step 1: Vector similarity search (top_k candidates)
        candidates = self._vector_search(query, chunks, self.config.top_k)
        # Step 2: Rerank for precision (top_n results)
        reranked = self._rerank(query, candidates, self.config.rerank_top_n)
        # Step 3: Filter by threshold
        return [c for c in reranked if c.score >= self.config.similarity_threshold]

    def generate(self, query: str, context: list[Chunk]) -> str:
        """Generate answer grounded in retrieved context."""
        context_text = "\n---\n".join(c.text for c in context)
        prompt = f"Answer based ONLY on the context below.\n\nContext:\n{context_text}\n\nQuestion: {query}"
        return self._call_llm(prompt)
```

## RAG Variants

| Variant | Mechanism | Best For |
|---------|-----------|----------|
| Naive RAG | Single retrieval + generation | Simple Q&A |
| Advanced RAG | Pre/post-retrieval optimization | Production systems |
| Modular RAG | Swappable components (LEGO) | Flexible pipelines |
| Self-RAG | Self-reflective retrieval decisions | High-accuracy needs |
| Corrective RAG | Verify and re-retrieve if needed | Critical applications |
| GraphRAG | Knowledge graph augmentation | Relational reasoning |
| Agentic RAG | Agent decides when/what to retrieve | Complex multi-hop queries |

## Chunking Strategies

| Strategy | Pros | Cons |
|----------|------|------|
| Fixed-size | Simple, predictable | Breaks semantic units |
| Semantic | Preserves meaning | Slower, variable size |
| Recursive | Tries multiple separators | Good balance |
| Document-aware | Respects structure (headers, etc.) | Requires parsing |
| Sentence-window | Each chunk = sentence + context window | Higher storage |

## Common Mistakes

### Wrong

```python
# Embedding entire documents without chunking
embedding = embed(entire_document)  # too large, loses specificity

# No reranking -- vector search alone has low precision
results = vector_search(query, top_k=3)  # may miss relevant chunks
```

### Correct

```python
# Semantic chunking with overlap + hybrid search + reranking
chunks = semantic_chunk(document, max_tokens=512, overlap=50)
candidates = hybrid_search(query, top_k=20)  # vector + BM25 keyword
results = rerank(query, candidates, top_n=5)  # cross-encoder precision
```

## Hybrid Search

```python
def hybrid_search(query: str, alpha: float = 0.7) -> list[Chunk]:
    """Combine vector similarity with keyword (BM25) search.
    alpha: weight for vector search (1.0 = pure vector, 0.0 = pure keyword)
    """
    vector_results = vector_search(query, top_k=20)
    keyword_results = bm25_search(query, top_k=20)
    # Reciprocal rank fusion
    combined = reciprocal_rank_fusion(
        [vector_results, keyword_results],
        weights=[alpha, 1 - alpha],
    )
    return combined[:10]
```

## Related

- [RAG Pipeline Pattern](../patterns/rag-pipeline.md)
- [Evaluation Framework](../patterns/evaluation-framework.md)
- [Guardrails](../concepts/guardrails.md)
