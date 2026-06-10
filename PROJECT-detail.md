# agentcore-enhanced — Full Technical Specification

## Executive Summary

agentcore-enhanced forks [awslabs/agentcore-samples](https://github.com/awslabs/agentcore-samples) and transforms it into a production-grade multi-cloud agent orchestration platform. The core delta from upstream: (1) a provider-portable abstraction supporting 6 LLM backends with automatic fallback, (2) first-class MCP (Model Context Protocol) server and client patterns, (3) a built-in 5-metric evaluation benchmark suite that scores every agent run, (4) a pattern library of proven agent architectures (ReAct, CoT, multi-agent parliament, memory-augmented), and (5) a daily self-learning research loop that keeps the platform current with the latest agent architecture research.

**Upstream pinned tag:** `awslabs/agentcore-samples @ v0.1.0` (commit hash documented in upstream/README.md)

**Three quantified improvement targets:**
| Metric | Upstream Baseline | Target | Method |
|--------|------------------|--------|--------|
| Provider coverage | 1 (AWS Bedrock only) | 6 providers | provider_adapter.py abstraction layer |
| Benchmark automation | 0 (manual) | 5 metrics auto-scored per run | eval_benchmark.py |
| Pattern catalog | ~8 patterns (AWS-specific) | 15+ provider-agnostic patterns | pattern_library.py + research loop |

---

## Target Users & Use Cases

| User | Trigger | Agent Does |
|------|---------|-----------|
| Platform engineer | `agent run --pattern react --provider azure` | Loads ReAct pattern, routes to Azure AI, scores result, appends to benchmark log |
| AI researcher | `agent benchmark --all-providers --pattern cot` | Runs CoT pattern across all configured providers, produces comparison report |
| DevOps engineer | `agent serve` then POST /run | REST API endpoint executes requested pattern on specified provider, returns JSON + Markdown |
| Architect | `agent pattern search "memory-augmented"` | Semantic search over pattern library using BGE-large embeddings |
| Daily cron | `agent update-knowledge` | Crawls ArXiv/Scholar/GitHub, appends top-N papers to SECOND-KNOWLEDGE-BRAIN.md |

---

## Agent Architecture (ASCII Diagram)

```
     CLI / REST API (FastAPI)
              ↓
     Orchestrator (orchestrator.py)
     ┌─────────────────────────────┐
     │  1. Load Pattern            │
     │     pattern_library.py      │
     │  2. Route to Provider       │
     │     provider_adapter.py     │
     │  3. Register MCP Tools      │
     │     mcp_manager.py          │
     │  4. Execute + Score         │
     │     eval_benchmark.py       │
     │  5. Persist + Report        │
     │     memory_manager.py       │
     └─────────────────────────────┘
              ↓
     ┌────────────────────────────────────┐
     │ Provider Layer                     │
     │ Claude  GPT-4o  Azure  GCP  Ollama │
     │      (via llm_client.py)           │
     └────────────────────────────────────┘
              ↓
     ┌────────────────────────────────────┐
     │ HuggingFace Layer                  │
     │ BGE-large (pattern search)         │
     │ MiniLM (fast embedding)            │
     │ CodeT5+ (code pattern analysis)    │
     │ BGE-reranker (relevance ranking)   │
     └────────────────────────────────────┘
              ↓
     Benchmark Report + SECOND-KNOWLEDGE-BRAIN.md
```

---

## Full Module Catalog

### `agent/modules/provider_adapter.py`

**Responsibility:** Unified LLM completion and streaming interface across 6 providers. Auto-fallback chain on error.

**Inputs:**
- `provider: str` — "claude" | "openai" | "azure" | "gcp" | "ollama" | "vllm"
- `messages: list[dict]` — OpenAI-format message list
- `model: str` — provider-specific model ID
- `stream: bool` — streaming mode flag
- `tools: list[dict]` — OpenAI-format tool definitions (for function calling)

**Outputs:**
- `CompletionResult(text, provider_used, model_used, prompt_tokens, completion_tokens, latency_ms, cost_usd)`

**Tools called:** `tools/llm_client.py`

**Quality gate:** Fallback to next provider if call fails or returns empty. Raise `AllProvidersExhausted` only if all 6 fail.

---

### `agent/modules/mcp_manager.py`

**Responsibility:** MCP server exposing agent tools; MCP client connecting to external MCP servers. Tool registry with JSON Schema validation.

**Inputs (server mode):**
- List of tool functions decorated with `@mcp_tool`
- Server port and host config

**Inputs (client mode):**
- MCP server URL
- Tool call: `{name: str, arguments: dict}`

**Outputs:**
- Server: JSON-RPC 2.0 responses
- Client: `ToolResult(content, is_error, tool_name, latency_ms)`

**Tools called:** `agent/tools/web_search_tool.py`, `agent/tools/code_exec_tool.py`, `agent/tools/file_io_tool.py`

**Quality gate:** JSON Schema validation on all tool inputs before execution. Reject malformed calls.

---

### `agent/modules/eval_benchmark.py`

**Responsibility:** Score every agent run on 5 metrics. Aggregate results into comparison reports across providers and patterns.

**5 Metrics:**
1. **Task success rate** — Did the agent complete the specified task? (LLM-judged binary + confidence 0..1)
2. **Token efficiency** — `useful_output_tokens / total_tokens_used` (higher = better)
3. **Error recovery rate** — When tool calls fail, does the agent recover? `(errors_recovered / total_errors)`
4. **Latency** — p50/p95 wall-clock time from first token to last token (ms)
5. **Output quality** — LLM-judged rubric score 0..5: correctness, completeness, coherence

**Inputs:**
- `run_id: str`, `pattern: str`, `provider: str`
- `task_description: str`, `agent_output: str`
- `tool_calls: list[ToolCall]`, `token_counts: dict`
- `elapsed_ms: float`

**Outputs:**
- `BenchmarkResult(run_id, pattern, provider, task_success, token_efficiency, error_recovery, latency_ms, quality_score, composite_score)`

**Tools called:** `tools/llm_client.py` (for LLM-judged metrics)

**Quality gate:** `composite_score = 0.30×task_success + 0.20×token_efficiency + 0.20×error_recovery + 0.15×(1/latency_norm) + 0.15×quality/5`. Min composite 0.40 triggers warning.

---

### `agent/modules/pattern_library.py`

**Responsibility:** Catalog of 15 reusable agent patterns. Semantic search via BGE-large. Returns prompt templates, scaffolding code, and recommended providers.

**Patterns included:**
1. ReAct (Reason + Act) — iterative thought/action/observation loop
2. Chain-of-Thought (CoT) — step-by-step reasoning before final answer
3. Tree-of-Thought (ToT) — branching reasoning with backtracking
4. Multi-Agent Parliament — N agents debate, majority vote, moderator summarizes
5. Critic-Actor — one agent drafts, another critiques, iterate until quality gate passes
6. Memory-Augmented — vector store retrieval injected into every prompt
7. Tool-Use Specialist — agent with rich tool library, optimized for function calling
8. Code Agent — writes → executes → debugs Python in sandbox loop
9. Document Analyst — chunking + embedding + RAG over uploaded documents
10. Self-Refine — agent critiques its own output and refines until satisfied
11. Planner-Executor — separate planning phase from execution phase
12. Supervisor-Worker — supervisor delegates sub-tasks to worker agents
13. Reflection Agent — periodic self-reflection on past runs to improve future behavior
14. Constitutional Agent — output checked against a set of rules / guardrails
15. Research Agent — ArXiv/web search → synthesis → structured report

**Inputs:**
- `query: str` — semantic search query OR exact pattern name
- `provider: str` — preferred provider (filters by compatibility)

**Outputs:**
- `PatternConfig(name, description, prompt_template, system_prompt, tools_required, recommended_providers, example_tasks, benchmark_scores)`

**Tools called:** `tools/hf_model_manager.py` (BGE-large search), `tools/llm_client.py` (pattern explanation)

**Quality gate:** Pattern search must return similarity score ≥ 0.65 before returning result; otherwise return top-3 candidates for user selection.

---

## HuggingFace Model Selection

| Model | Task | Benchmark | Reason over Alternatives |
|-------|------|-----------|--------------------------|
| `BAAI/bge-large-en-v1.5` | Pattern semantic search | MTEB avg 64.2, BEIR 54.1 | MTEB #1 English; best quality/size; open weights |
| `sentence-transformers/all-MiniLM-L6-v2` | Fast embedding for benchmark clustering | MTEB avg 56.3 | 5× faster than BGE-large; fits real-time use case |
| `Salesforce/codet5p-770m` | Code pattern analysis | HumanEval 32.1 | Code-specialized encoder/decoder; no fine-tuning needed |
| `BAAI/bge-reranker-large` | Post-retrieval pattern reranking | BEIR reranker +12 NDCG@10 vs bi-encoder | Cross-encoder beats bi-encoder by large margin |

---

## LLM API Integration Spec

### Provider Chain
```
Claude claude-opus-4-8 → OpenAI gpt-4o → Azure GPT-4o → GCP Gemini Pro → Ollama llama3
```

### Prompt Templates

**ReAct pattern system prompt:**
```
You are an autonomous agent. Think step by step using the format:
Thought: <reasoning>
Action: <tool_name>(<arguments>)
Observation: <result>
... (repeat)
Final Answer: <answer>
Available tools: {tools_list}
```

**Benchmark evaluation prompt:**
```
Score this agent output on task success (0.0-1.0):
Task: {task_description}
Output: {agent_output}
Return JSON: {"task_success": float, "confidence": float, "reasoning": str}
```

**Pattern synthesis prompt:**
```
Given these agent architecture papers: {paper_summaries}
Synthesize: (1) emerging patterns, (2) known limitations, (3) recommended provider pairing.
Return structured JSON with citations.
```

**Multi-agent parliament prompt:**
```
You are Agent {n} of {total}. Review the task and provide your position:
Task: {task}
Previous positions: {positions}
Your role: {role} ({role_description})
Provide: position, confidence (0-1), key_arguments (list)
```

### Token Budget Estimates
| Pattern | Avg Input Tokens | Avg Output Tokens | Estimated Cost (claude-opus-4-8) |
|---------|-----------------|------------------|--------------------------------|
| ReAct (3 steps) | 2,500 | 800 | ~$0.052 |
| CoT | 1,200 | 600 | ~$0.027 |
| Multi-agent (5 agents) | 8,000 | 2,500 | ~$0.158 |
| Document analyst | 12,000 | 1,500 | ~$0.204 |
| Benchmark eval | 800 | 200 | ~$0.015 |

---

## End-to-End Execution Flow

```
1. INPUT
   ├── CLI: `agent run --pattern react --task "Search arXiv for MCP papers" --provider claude`
   └── REST: POST /run {"pattern": "react", "task": "...", "provider": "claude"}

2. ORCHESTRATOR init
   ├── Load pattern_library (lazy singleton)
   ├── Load provider_adapter (lazy singleton)
   ├── Load mcp_manager (lazy singleton, start MCP server if not running)
   └── Load eval_benchmark (lazy singleton)

3. PATTERN LOAD (pattern_library.py)
   ├── Semantic search: BGE-large encode query → FAISS top-5 → BGE-reranker top-1
   ├── Return: PatternConfig with prompt_template, tools_required, system_prompt
   └── Quality gate: similarity ≥ 0.65 (else return candidates list, abort)

4. TOOL REGISTRATION (mcp_manager.py)
   ├── Register tools required by pattern (web_search, code_exec, file_io)
   ├── Validate JSON Schema for each tool
   └── Start MCP server on localhost:8765 (if not already running)

5. PROVIDER ROUTE (provider_adapter.py)
   ├── Try claude-opus-4-8: send messages + tool definitions
   │   ├── Success → CompletionResult
   │   └── Failure → try next provider (OpenAI → Azure → GCP → Ollama)
   └── Record: provider_used, model_used, prompt_tokens, completion_tokens, latency_ms, cost_usd

6. AGENT EXECUTION LOOP
   ├── While tool_calls in response AND steps < max_steps:
   │   ├── Parse tool call from LLM response
   │   ├── Execute via mcp_manager.call_tool()
   │   ├── Append tool result to message history
   │   └── Send updated history back to provider
   └── Extract final answer when no more tool calls

7. EVALUATE (eval_benchmark.py)
   ├── task_success: LLM-judged binary (async call to claude-sonnet-4-6 to save cost)
   ├── token_efficiency: useful_output / total_tokens
   ├── error_recovery: errors_recovered / total_errors (0 if no errors)
   ├── latency: elapsed_ms
   ├── quality_score: LLM-judged rubric 0..5
   └── composite_score: weighted average

8. PERSIST (memory_manager.py)
   ├── Save run to SQLite (runs table)
   ├── Save benchmark result (benchmark_results table)
   ├── Log LLM cost (llm_cost_log table)
   └── Save pattern usage (pattern_usage table)

9. RENDER REPORT
   ├── Markdown: pattern used, provider, benchmark scores, tool calls, final answer
   └── JSON: structured result for programmatic consumption

10. OUTPUT
    ├── CLI: print Markdown report
    └── REST: return JSON response
```

**Error handling:**
- Provider failure → auto-fallback, log warning, continue
- Tool execution failure → increment error count, retry once, skip if still failing
- All providers exhausted → return 503 with diagnostic message
- Pattern not found (similarity < 0.65) → return 3 closest matches

---

## SECOND-KNOWLEDGE-BRAIN.md Integration

**Update trigger:** Daily cron at 06:00 (APScheduler CronTrigger)

**Sources:**
- ArXiv API: cs.AI + cs.MA + cs.LG + cs.SE (daily, last 7 days)
- Semantic Scholar: "multi-agent LLM", "agent orchestration", "MCP model context protocol", "agent evaluation"
- Papers with Code: agent benchmarks leaderboard
- GitHub Releases: awslabs/agentcore-samples, langchain-ai/langchain, run-llama/llama_index, crewAIInc/crewAI
- AWS/Azure agent blog RSS feeds

**Dedup strategy:** SHA256 hash of DOI/arXiv-ID. Skip if already in SQLite `knowledge_hashes` table.

**Top-N selection:** Score = recency_weight × relevance_score. Recency: last 7 days = 1.0, 8–30 days = 0.7, 31–90 days = 0.4. Relevance: keyword overlap with domain terms.

---

## quality_gates

1. Pattern similarity ≥ 0.65 before executing any run
2. All MCP tool inputs validated against JSON Schema before execution
3. Provider fallback exhausted → return structured error, never hang
4. Benchmark composite score < 0.40 → emit warning in report
5. LLM cost per run > $0.50 → emit cost warning; offer cheaper provider suggestion
6. Test suite: all 5 metric calculations produce values in valid range [0,1] or [0,5]
7. Daily knowledge crawl: ≥ 1 new paper added per day to SECOND-KNOWLEDGE-BRAIN.md

---

## Test Scenarios

See `tests/test-scenarios.md` for 8 full end-to-end scenarios.

---

## Key Design Decisions

1. **Provider-portable abstraction over provider-specific SDKs.** All 6 providers use the same `CompletionResult` schema. Enables benchmark comparisons across providers with zero code changes.

2. **MCP-first tool integration.** Rather than ad-hoc function calling, all tools are registered as MCP endpoints. This means external MCP servers (e.g., a database MCP server) can be plugged in with one config line.

3. **Sidecar architecture for fork compatibility.** All new AI code lives in `agent/` and `ai_layer/`. Upstream `awslabs/agentcore-samples` code is unchanged in `upstream/`. This allows pulling upstream updates without merge conflicts.

4. **LLM-judged benchmark metrics.** Task success and output quality use a smaller, cheaper model (claude-sonnet-4-6) to judge the output of the main model (claude-opus-4-8). Keeps eval cost low.

5. **BGE-large for pattern retrieval, MiniLM for real-time embedding.** BGE-large is used for the pattern library search (one-time at query time). MiniLM is used for benchmark clustering (high-frequency). Right model for each latency requirement.

6. **15-pattern catalog covers 95% of documented agent architectures.** Based on survey of AgentBench, ALFWorld, WebArena, and HotpotQA papers. New patterns from daily research crawl are proposed as issues in the pattern catalog.

7. **Cost transparency as first-class feature.** Every run emits cost_usd. Monthly cost report CLI command. Provider comparison chart in benchmark report shows cost vs quality tradeoff.
