# Prompt Engineering Quick Reference

> Fast lookup tables. For code examples, see linked files.
> **MCP Validated:** 2026-02-17

## Technique Selection

| Technique | Best For | Accuracy Boost | Token Cost |
|-----------|----------|---------------|------------|
| Zero-shot | Simple tasks, classification | Baseline | Low |
| Few-shot | Format-sensitive, tone matching | +15-25% | Medium |
| Chain-of-Thought | Reasoning, math, logic | +20-40% | Medium |
| Self-consistency | High-stakes decisions | +10-15% | High |
| Multi-pass | Document extraction | +25-35% | High |

## Temperature Guide

| Task Type | Temperature | Reason |
|-----------|-------------|--------|
| Data extraction | 0.0 | Deterministic, factual |
| Classification | 0.0-0.2 | Consistent labels |
| Summarization | 0.3-0.5 | Slight variation OK |
| Creative writing | 0.7-1.0 | Diversity desired |
| Code generation | 0.0-0.2 | Correctness critical |

## Prompt Structure

| Section | Required | Purpose |
|---------|----------|---------|
| System/Role | Yes | Define persona and constraints |
| Task | Yes | What the LLM should do |
| Context/Input | Yes | Data to process |
| Output Format | Yes | Expected response structure |
| Examples | Recommended | Teach by demonstration |
| Constraints | Recommended | Guardrails and edge cases |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| Extract fields from invoice | `patterns/document-extraction.md` |
| Need step-by-step reasoning | `concepts/chain-of-thought.md` |
| Consistent JSON output | `concepts/output-formatting.md` |
| Teach format by example | `concepts/few-shot-prompting.md` |
| Validate LLM output accuracy | `patterns/validation-prompts.md` |
| High-accuracy extraction | `patterns/multi-pass-extraction.md` |
| Reusable prompt code | `patterns/prompt-template.md` |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Use vague instructions ("be helpful") | Be explicit ("Extract the invoice number") |
| Skip output format specification | Always define JSON schema or structure |
| Use high temperature for extraction | Set temperature to 0.0 for factual tasks |
| Send raw documents without context | Pre-process and chunk documents |
| Trust LLM output without validation | Always validate with Pydantic or schema |
| Write monolithic prompts | Split into composable template sections |

## Related Documentation

| Topic | Path |
|-------|------|
| Chain-of-Thought | `concepts/chain-of-thought.md` |
| System Prompts | `concepts/system-prompts.md` |
| Full Index | `index.md` |
