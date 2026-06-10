# Architecture Documentation

This document provides a comprehensive overview of agentcore-enhanced architecture, design decisions, and implementation details.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interface                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  CLI (agentcore)  │  FastAPI Server  │  Python SDK  │  REST API             │
└────────────────────┬────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────────────┐
│                          Orchestrator Layer                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  AgentCoreOrchestrator                                                       │
│  - run_pattern()        - benchmark_all_providers()                          │
│  - pattern_search()     - update_knowledge()                                 │
│  - get_cost_report()    - get_prometheus_metrics()                          │
└───┬───────────────┬────────────────┬───────────────┬─────────────────────────┘
    │               │                │               │
┌───▼───────────┐  │  ┌─────────────▼──────────────┐  │  ┌──────────────────┐
│ Pattern Lib   │  │  │   Provider Adapter         │  │  │  MCP Manager     │
│ - 15 patterns │  │  │ - Claude                   │  │  │ - Tool Registry  │
│ - BGE search  │  │  │ - OpenAI                   │  │  │ - 4 built-in     │
│ - Reranker    │  │  │ - Azure                    │  │  │ - JSON-RPC       │
└────────────────┘  │  │ - GCP                      │  │  └──────────────────┘
                   │  │ - Ollama                   │  │
┌──────────────────┐ │  │ - vLLM                     │  │  ┌──────────────────┐
│ Eval Benchmark  │ │  │ - Auto-fallback            │  │  │ Memory Manager   │
│ - 5 metrics     │◄─┼──│                           │  │  │ - SQLite         │
│ - LLM judge     │ │  └────────────────────────────┘  │  │ - Run history    │
│ - Composite     │ │                                   │  │ - Cost tracking   │
└──────────────────┘ │  ┌────────────────────────────────┘  └──────────────────┘
                    │  │
┌───────────────────▼──▼──────────────────────────────────────────────────────┐
│                          Supporting Services                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│  HuggingFace Models  │  ArXiv Crawler  │  APScheduler  │  Prometheus         │
│  - BGE-large         │  - Semantic      │  - Daily jobs │  - Metrics export  │
│  - MiniLM            │    Scholar       │              │                    │
│  - CodeT5+           │  - GitHub        │              │                    │
│  - BGE-reranker      │    Releases      │              │                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Module Details

### Orchestrator (`agent/orchestrator.py`)

**Purpose**: Central coordinator that wires all modules together

**Key Methods**:
- `run_pattern()`: Execute single pattern on single provider
- `benchmark_all_providers()`: Compare providers on same task
- `pattern_search()`: Semantic pattern catalog search
- `update_knowledge()`: Trigger research crawler
- `get_cost_report()`: LLM cost breakdown
- `get_prometheus_metrics()`: Prometheus endpoint

**Design Patterns**:
- Lazy initialization: Modules loaded on-demand
- Singleton pattern: Single orchestrator instance
- Async/await: All I/O operations are async

**Data Flow**:
```
user request → orchestrator → pattern_lib → provider_adapter → mcp_manager
                                        ↓
                                    eval_benchmark
                                        ↓
                                    memory_manager
                                        ↓
                                    response + report
```

### Provider Adapter (`agent/modules/provider_adapter.py`)

**Purpose**: Unified API across 6 LLM providers with auto-fallback

**Supported Providers**:
1. **Claude** (Anthropic): `claude-opus-4-8`, `claude-sonnet-4-6`
2. **OpenAI**: `gpt-4o`, `gpt-4o-mini`
3. **Azure AI Foundry**: OpenAI models via Azure endpoint
4. **GCP Vertex AI**: `gemini-1.5-pro`, `gemini-1.5-flash`
5. **Ollama**: Local models (`llama3`, `mistral`, etc.)
6. **vLLM**: Local OpenAI-compatible server

**Fallback Chain**:
```
preferred → claude → openai → azure → gcp → ollama → vllm
```

**Implementation**:
```python
class BaseProviderAdapter:
    async def complete(messages, model, system, tools) -> CompletionResult
    async def stream(messages, model, system) -> AsyncIterator[str]

class ProviderAdapter:
    async def complete(provider, messages, ...) -> dict:
        chain = _build_fallback_chain(provider)
        for provider in chain:
            try:
                return await adapter.complete(...)
            except Exception:
                continue
        raise AllProvidersExhausted()
```

**Cost Tracking**:
- All providers tracked in `COST_PER_1K` table
- Cost computed per completion: `(prompt/1000)*input_cost + (completion/1000)*output_cost`
- Logged to SQLite for cost reporting

### MCP Manager (`agent/modules/mcp_manager.py`)

**Purpose**: Model Context Protocol server + client + tool registry

**MCP Compliance**:
- JSON-RPC 2.0 over HTTP
- `tools/list` method
- `tools/call` method with JSON Schema validation

**Built-in Tools**:
1. **web_search**: DuckDuckGo search API
2. **code_execute**: Sandboxed Python subprocess (10s timeout)
3. **file_read**: Scoped to `workspace/` directory
4. **file_write**: Scoped to `workspace/` directory

**Tool Registration**:
```python
ToolDefinition(
    name="web_search",
    description="Search the web using DuckDuckGo",
    parameters={  # JSON Schema
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    },
    fn=_web_search,
    category="search"
)
```

**Security Features**:
- Path validation: file I/O scoped to workspace
- Timeout enforcement: code execution max 30s
- Schema validation: all tool inputs validated

### Eval Benchmark (`agent/modules/eval_benchmark.py`)

**Purpose**: 5-metric evaluation of every agent run

**Metrics**:

| Metric | Range | Calculation | Weight |
|--------|-------|-------------|--------|
| Task Success | 0-1 | LLM-judged completion quality | 30% |
| Token Efficiency | 0-1 | Useful tokens / total tokens | 20% |
| Error Recovery | 0-1 | Recovered errors / total errors | 20% |
| Latency Score | 0-1 | 1 - (latency_ms / 30000) | 15% |
| Quality Score | 0-5 | LLM-judged output quality | 15% |

**Composite Score**:
```python
composite = (
    0.30 * task_success +
    0.20 * token_efficiency +
    0.20 * error_recovery +
    0.15 * latency_score +
    0.15 * (quality_score / 5.0)
)
```

**LLM Judge**:
- Uses `claude-sonnet-4-6` for cost/quality balance
- Fallback to heuristic scoring if unavailable
- Cost tracked separately (not included in agent run cost)

**Rubrics**:

Task Success:
- 1.0 = fully complete, all requirements met
- 0.7 = mostly complete, minor gaps
- 0.4 = partial, key requirements missing
- 0.1 = attempted but failed
- 0.0 = no relevant output

Quality:
- 5 = expert-level, accurate, well-structured
- 4 = good, mostly accurate
- 3 = adequate, basic info present
- 2 = poor, significant issues
- 1 = very poor
- 0 = no output

### Pattern Library (`agent/modules/pattern_library.py`)

**Purpose**: 15-pattern catalog with semantic search

**Patterns**:
- ReAct, CoT, ToT (reasoning)
- Multi-agent parliament, supervisor-worker (multi-agent)
- Critic-actor, self-refine (refinement)
- Memory-augmented, reflection (memory/learning)
- Tool-use specialist, code-agent (tools)
- Document analyst (RAG)
- Planner-executor (planning)
- Constitutional (safety)
- Research agent (research)

**Semantic Search Pipeline**:
```
query → BGE-large encode → FAISS top-2k → BGE-reranker → top-1
```

**Similarity Threshold**:
- Minimum 0.65 for pattern selection
- Warns if score below 0.70
- Errors if score below 0.65

**Provider Compatibility**:
- Some patterns require function calling
- Filtered by `requires_function_calling` flag
- Provider fallback respects capability

### Memory Manager (`agent/memory/memory_manager.py`)

**Purpose**: SQLite persistence for runs, benchmarks, costs

**Schema**:
```sql
-- Agent runs
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    pattern TEXT NOT NULL,
    provider TEXT NOT NULL,
    task TEXT NOT NULL,
    final_answer TEXT,
    tool_calls_count INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    latency_ms REAL DEFAULT 0,
    composite_score REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Benchmark results
CREATE TABLE benchmark_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    pattern TEXT NOT NULL,
    provider TEXT NOT NULL,
    task_success REAL,
    token_efficiency REAL,
    error_recovery REAL,
    latency_ms REAL,
    quality_score REAL,
    composite_score REAL,
    eval_cost_usd REAL DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- LLM cost tracking
CREATE TABLE llm_cost_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    task_type TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Knowledge dedup
CREATE TABLE knowledge_hashes (
    hash TEXT PRIMARY KEY,
    title TEXT,
    source TEXT,
    added_at TEXT DEFAULT (datetime('now'))
);
```

**Thread Safety**:
- All writes protected by `threading.Lock()`
- SQLite `check_same_thread=False` for cross-thread access
- Row factory set for dict-like access

## Design Decisions

### Why 6 Providers?

Different use cases require different trade-offs:
- **Claude**: Best reasoning quality, expensive
- **OpenAI**: Good quality, widely available
- **Azure**: Enterprise compliance
- **GCP**: GCP ecosystem integration
- **Ollama**: Privacy, offline, free
- **vLLM**: High throughput local serving

### Why SQLite vs PostgreSQL?

**Decision**: SQLite

**Rationale**:
- Zero configuration
- Embedded (no separate database server)
- Sufficient for agent workload (single writer, many readers)
- Easy backup (single file)
- Lower complexity

**Trade-off**: Not suitable for multi-server deployments (use PostgreSQL in those cases)

### Why BGE-large vs OpenAI Embeddings?

**Decision**: BGE-large (HuggingFace)

**Rationale**:
- No API cost per embedding
- MTEB #1 dense retrieval benchmark
- Can run locally (privacy)
- Better control over updates

**Trade-off**: Requires GPU/CPU resources and model storage (~1.3GB)

### Why JSON-RPC 2.0 for MCP?

**Decision**: JSON-RPC 2.0 over HTTP

**Rationale**:
- MCP standard compliance
- Simpler than WebSocket (stateless)
- Language-agnostic
- Easy to debug (curl-able)

**Trade-off**: No server push (use SSE for streaming in future)

### Why FastAPI vs Flask?

**Decision**: FastAPI

**Rationale**:
- Native async support
- Automatic OpenAPI docs
- Type hints for validation
- Better performance (Starlette)
- Pydantic integration

## Performance Considerations

### Latency Breakdown

Typical agent run (ReAct, 5 steps):
- LLM calls: 80-90% (5 calls × 1-3s each)
- Tool execution: 5-10% (web search ~500ms)
- Benchmark evaluation: 5% (LLM judge ~1s)
- Overhead: <1% (orchestrator, DB writes)

### Optimization Strategies

1. **Streaming**: Use `stream()` for real-time output (reduces perceived latency)
2. **Caching**: Pattern search cached in FAISS index
3. **Batching**: Multiple runs in parallel via `benchmark_all_providers()`
4. **Model Selection**: Use smaller models (sonnet, mini) for faster iterations
5. **Local Inference**: Ollama/vLLM for privacy-sensitive or high-volume workloads

### Resource Requirements

**Minimum**:
- CPU: 4 cores
- RAM: 4 GB
- Disk: 10 GB (models cached remotely)

**Recommended**:
- CPU: 8 cores
- RAM: 16 GB
- GPU: 8 GB VRAM (for HuggingFace models)
- Disk: 50 GB (local model cache)

## Security Architecture

### Threat Model

**Trusted**:
- Local filesystem (workspace scoped)
- Admin user (API key access)

**Untrusted**:
- Agent outputs (validated via schema)
- Tool inputs (validated via JSON Schema)
- External API responses (parsed carefully)

### Protections

1. **Sandboxing**: Code execution in subprocess, scoped workspace
2. **Validation**: All tool inputs validated against JSON Schema
3. **Scoping**: File I/O limited to workspace directory
4. **Timeouts**: All I/O operations have configurable timeouts
5. **Rate Limits**: Provider-specific rate limiting (via SDKs)

### Data Flow

```
user request → validate → execute tools → validate output → response
     ↑              ↓              ↑               ↓
   auth          schema        sandbox        JSON Schema
```

## Monitoring

### Prometheus Metrics

Exposed at `/metrics`:

```
agentcore_runs_total                    # Total agent runs
agentcore_benchmark_composite_score_avg # Average composite score
agentcore_cost_usd_total                # Total LLM cost
agentcore_provider_latency_ms           # Provider latency (histogram)
agentcore_tool_calls_total              # Tool invocations by type
```

### Logging

Structured JSON logs (configurable):

```json
{
  "level": "INFO",
  "message": "Agent run completed",
  "run_id": "abc123",
  "pattern": "react",
  "provider": "claude",
  "composite_score": 0.82,
  "latency_ms": 4500,
  "cost_usd": 0.0234
}
```

## Deployment Patterns

### Single Server

```
Docker Compose:
- agentcore-agent (FastAPI + Orchestrator)
- ollama (local inference)
```

### Multi-Server

```
Load Balancer → agentcore-agent ×3
                  ↓
            Shared PostgreSQL (instead of SQLite)
                  ↓
            Redis (optional, for caching)
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: agentcore
        image: agentcore-enhanced:latest
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef: { name: api-keys, key: anthropic }
        resources:
          requests: { cpu: "2", memory: "4Gi" }
          limits: { cpu: "4", memory: "8Gi" }
```

## Future Roadmap

### Short Term (3 months)

- [ ] WebSocket support for streaming responses
- [ ] PostgreSQL backend option
- [ ] Redis caching layer
- [ ] Advanced prompt management (versioning, A/B testing)
- [ ] Multi-user support with authentication

### Long Term (6-12 months)

- [ ] Distributed agent execution (Ray integration)
- [ ] Custom pattern builder UI
- [ ] Real-time collaboration (multi-user sessions)
- [ ] Agent marketplace (share custom patterns)
- [ ] Federated learning across deployments

For API documentation, see [OpenAPI spec](../openapi.json).
