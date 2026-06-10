# agentcore-enhanced — AI Layer Integration Guide

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│ agentcore-enhanced sidecar                                     │
│                                                                │
│  FastAPI (port 7865)          CLI                              │
│       ↓                        ↓                               │
│  AgentCoreOrchestrator                                         │
│       ├── PatternLibrary (15 patterns + BGE-large search)      │
│       ├── ProviderAdapter (6 providers + auto-fallback)        │
│       ├── MCPManager (server + client + 4 built-in tools)      │
│       ├── EvalBenchmark (5-metric scorer)                      │
│       └── MemoryManager (SQLite)                               │
│                                                                │
│  tools/                                                        │
│       ├── knowledge_updater.py (daily ArXiv/Scholar crawl)     │
│       ├── llm_client.py (Claude/OpenAI/Ollama)                 │
│       └── hf_model_manager.py (BGE-large/MiniLM/CodeT5+)      │
└────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# 1. Clone and configure
cd 19
cp config/.env.example .env
# Edit .env: set ANTHROPIC_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the agent
python -m agent.main serve

# 4. Test it
curl http://localhost:7865/health
```

---

## REST API Quick Reference

```bash
# Health check
curl http://localhost:7865/health

# List all 15 patterns
curl http://localhost:7865/patterns

# Semantic pattern search
curl -X POST http://localhost:7865/patterns/search \
  -H "Content-Type: application/json" \
  -d '{"query": "agent that uses tools iteratively", "top_k": 3}'

# Run a pattern
curl -X POST http://localhost:7865/run \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "react",
    "task": "Find the 3 most popular Python agent frameworks in 2025",
    "provider": "claude",
    "max_steps": 8
  }'

# Benchmark providers
curl -X POST http://localhost:7865/benchmark \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "chain_of_thought",
    "task": "What makes a good AI agent evaluation benchmark?",
    "providers": ["claude", "openai", "ollama"]
  }'

# Trigger knowledge update
curl -X POST http://localhost:7865/knowledge/update

# Cost report
curl http://localhost:7865/cost

# Prometheus metrics
curl http://localhost:7865/metrics
```

---

## CLI Quick Reference

```bash
# Run a pattern
python -m agent.main run --pattern react --task "Research latest MCP tools" --provider claude

# Benchmark all providers
python -m agent.main benchmark --pattern cot --task "List 5 agent evaluation metrics" --providers claude,openai,ollama

# Search patterns
python -m agent.main pattern search --query "multi-agent coordination"

# List all patterns
python -m agent.main pattern list

# Update knowledge base
python -m agent.main update-knowledge

# Cost report (last 30 days)
python -m agent.main cost-report --days 30
```

---

## Cross-Agent Integration

### With academic-research-enhanced (Folder 18)
agentcore-enhanced can delegate literature reviews to the academic-research-enhanced agent's REST API:

```python
# In pattern: research_agent
# POST http://localhost:8018/synthesize
# {"topic": "multi-agent evaluation frameworks", "max_papers": 20}
```

### With ai-benchmark-agent (Folder 22)
agentcore-enhanced exposes Prometheus metrics at `/metrics`. The benchmark agent can scrape these metrics for cross-agent performance analysis:

```yaml
# In ai-benchmark-agent's prometheus.yml:
scrape_configs:
  - job_name: agentcore-enhanced
    static_configs:
      - targets: ['agentcore-enhanced:7865']
```

### With turbovec-enhanced (Folder 16)
Use turbovec-enhanced as an external MCP vector search tool:

```python
mcp_manager.register_external_server("turbovec", "http://turbovec-enhanced:7860")
# Then in patterns: call tools on the external vector DB
```

---

## Prometheus Metrics Reference

| Metric | Type | Description |
|--------|------|-------------|
| `agentcore_runs_total` | counter | Total agent pattern runs |
| `agentcore_benchmark_composite_score_avg` | gauge | Average composite benchmark score |
| `agentcore_cost_usd_total` | counter | Total LLM cost in USD |

---

## Adding a New Provider

1. Create a new adapter class in `agent/modules/provider_adapter.py` extending `BaseProviderAdapter`
2. Implement `complete()` and `stream()` async methods
3. Add the new instance to the `_ADAPTERS` dict
4. Add the provider to `FALLBACK_CHAIN` at desired priority position
5. Add `COST_PER_1K` entry for the provider's models

---

## Adding a New Pattern

1. Create a new `PatternConfig` instance in `agent/modules/pattern_library.py`
2. Add it to the `PATTERNS` list
3. Define: `name`, `description`, `system_prompt`, `prompt_template`, `tools_required`, `recommended_providers`
4. The pattern is immediately searchable via semantic search and available via REST API

---

## Production Hardening Checklist

- [ ] Set `ANTHROPIC_API_KEY` and at least one fallback provider key
- [ ] Set `GITHUB_TOKEN` for higher GitHub release crawl rate limits
- [ ] Set `PRIVACY_MODE=true` for sensitive workloads (forces Ollama)
- [ ] Mount `./data/` as a persistent volume in Docker Compose
- [ ] Mount `./SECOND-KNOWLEDGE-BRAIN.md` as a persistent volume
- [ ] Configure Prometheus scraping of `/metrics`
- [ ] Enable Docker health checks (already configured in Compose)
- [ ] Set resource limits in docker-compose.yml for production deployment
- [ ] Review and restrict `code_execute` tool timeout for your threat model
- [ ] Rotate `ANTHROPIC_API_KEY` regularly per Anthropic key management best practices
