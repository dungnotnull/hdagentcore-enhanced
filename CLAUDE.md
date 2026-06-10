# agentcore-enhanced — Multi-Cloud Agent Orchestrator

**Tagline:** Provider-portable multi-cloud agent patterns with self-evaluating benchmark, MCP integration, and daily research self-learning.

**Current Build Phase:** Phase 0 — Research & Architecture

---

## Problem Statement

AWS AgentCore Samples provides solid agent patterns for AWS Bedrock but locks users into a single cloud provider. Teams that run workloads across AWS, Azure, GCP, and on-premises cannot reuse these patterns without rewriting provider-specific code. This agent forks and extends AgentCore Samples with a provider-portable abstraction layer (Claude API, OpenAI, Azure AI Foundry, GCP Vertex AI, Ollama, vLLM), first-class MCP (Model Context Protocol) server/client patterns, a built-in evaluation benchmark that scores every agent pattern on task success / token efficiency / error recovery, and a daily self-learning research loop that continuously ingests new agent architecture papers into its knowledge base.

---

## Agent Architecture Summary

```
User / CI System
       ↓
┌──────────────────────────────────────────────────────────────┐
│  Orchestrator (agent/orchestrator.py)                        │
│  ┌──────────────────┐  ┌────────────────┐  ┌─────────────┐  │
│  │ Pattern Library  │→ │ Provider Router│→ │  Evaluator  │  │
│  └──────────────────┘  └────────────────┘  └─────────────┘  │
│        ↕                      ↕                    ↕         │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  Modules                                              │   │
│  │  provider_adapter.py  mcp_manager.py                 │   │
│  │  eval_benchmark.py    pattern_library.py              │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
       ↓              ↓              ↓             ↓
  Claude API     OpenAI API    Azure/GCP/        Ollama
  (primary)      (fallback)    Vertex AI         (offline)
       ↓
  MCP Tools / HuggingFace (BAAI/bge, MiniLM, CodeT5+)
       ↓
  Benchmark Report + Markdown Pattern Catalog
```

**Numbered steps:**
1. User selects a pattern (ReAct / CoT / multi-agent / memory / tool-use)
2. `pattern_library.py` loads pattern config + prompt templates
3. `provider_adapter.py` routes request to configured provider (Claude → GPT-4o → Azure → GCP → Ollama)
4. `mcp_manager.py` registers/calls MCP tools exposed by the pattern
5. `eval_benchmark.py` scores the run on 5 metrics and appends to benchmark log
6. `memory_manager.py` persists run, cost, and evaluation to SQLite
7. Orchestrator returns structured JSON + Markdown report

---

## Module List (`agent/modules/`)

| File | Description |
|------|-------------|
| `provider_adapter.py` | Unified completion/streaming interface for 6 providers (Claude, OpenAI, Azure, GCP, Ollama, vLLM). Auto-fallback chain. |
| `mcp_manager.py` | MCP server that exposes agent tools; MCP client that connects to external tool servers. Tool registry + schema validation. |
| `eval_benchmark.py` | Benchmark suite scoring task success, token efficiency, error recovery, latency, and output quality per agent run. |
| `pattern_library.py` | Catalog of reusable agent patterns (ReAct, CoT, multi-agent parliament, memory-augmented). Returns prompt templates + scaffolding. |

---

## Tools (`agent/tools/` — note: runtime tools, not the universal `tools/` components)

| File | Description |
|------|-------------|
| `web_search_tool.py` | MCP-compatible web search tool (DuckDuckGo / Brave Search API) for ReAct agent patterns. |
| `code_exec_tool.py` | Sandboxed Python code execution tool (subprocess + tempfile isolation) for code-agent patterns. |
| `file_io_tool.py` | Safe filesystem read/write tool scoped to workspace directory. |

---

## HuggingFace Models

| Model ID | Task | Why Chosen |
|----------|------|-----------|
| `BAAI/bge-large-en-v1.5` | Pattern semantic search + similarity | MTEB #1 dense retrieval; top BEIR benchmark |
| `sentence-transformers/all-MiniLM-L6-v2` | Fast embedding for benchmark result clustering | 5× faster than BGE at 90% quality; ideal for real-time eval |
| `Salesforce/codet5p-770m` | Code pattern analysis + code → spec reverse engineering | SOTA on HumanEval, CodeBLEU; purpose-built code encoder/decoder |
| `BAAI/bge-reranker-large` | Rerank retrieved patterns by contextual relevance | Cross-encoder, outperforms bi-encoder retrieval by +12 NDCG@10 |

---

## LLM API Integration

| Provider | Priority | Use Case |
|----------|----------|----------|
| Claude `claude-opus-4-8` | Primary | Multi-step reasoning, pattern synthesis, evaluation explanation, long-context analysis |
| OpenAI `gpt-4o` | Fallback | Multimodal tasks (diagram analysis), structured JSON function calling |
| Ollama `llama3` | Offline | Privacy-sensitive patterns, high-volume offline benchmarking |
| Azure AI Foundry | Cloud alt | Enterprise Azure deployments; same OpenAI-compatible API |
| GCP Vertex AI | Cloud alt | GCP-native deployments; Gemini Pro models |

---

## Knowledge Crawl Sources

| Source | Categories / Queries | Frequency |
|--------|---------------------|-----------|
| ArXiv | cs.AI, cs.MA, cs.LG, cs.SE | Daily |
| Semantic Scholar | "multi-agent systems", "LLM orchestration", "MCP model context protocol" | Daily |
| Papers with Code | Agent benchmarks, LLM evaluation leaderboards | Weekly |
| LangChain / LlamaIndex release notes | GitHub releases API | Weekly |
| AWS/Azure agent architecture blogs | RSS feed | Weekly |
| CNCF Wasm/MCP working group | RSS feed | Weekly |

---

## Supporting Tools (`tools/`)

| File | Description |
|------|-------------|
| `knowledge_updater.py` | Crawls ArXiv cs.AI/cs.MA/cs.LG + Semantic Scholar + GitHub releases. Appends to SECOND-KNOWLEDGE-BRAIN.md weekly. |
| `llm_client.py` | Unified Claude/GPT/Ollama/Azure/GCP client. Streaming, retry, cost tracking. |
| `hf_model_manager.py` | Lazy-loading HuggingFace model registry (BGE-large, MiniLM, CodeT5+, BGE-reranker). CUDA auto-detect. |

---

## Active Development Tasks

- [ ] Phase 0: Fork awslabs/agentcore-samples at pinned tag, document baseline
- [ ] Phase 1: Implement provider_adapter.py (6 providers + auto-fallback)
- [ ] Phase 2: Implement mcp_manager.py (server + client + tool registry)
- [ ] Phase 3: Implement eval_benchmark.py (5-metric scoring pipeline)
- [ ] Phase 4: Implement pattern_library.py (ReAct, CoT, multi-agent, memory patterns)
- [ ] Phase 5: Wire orchestrator + FastAPI server + CLI
- [ ] Phase 6: Integrate HuggingFace models (BGE-large pattern retrieval)
- [ ] Phase 7: tools/knowledge_updater.py first crawl run
- [ ] Phase 8: Docker Compose deployment + test suite
