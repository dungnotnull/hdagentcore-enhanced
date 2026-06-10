# agentcore-enhanced — Test Scenarios

## Scenario 1: ReAct Pattern — Web Research Task

**Trigger:** `agent run --pattern react --task "Find the top 3 MCP server implementations on GitHub and summarize them" --provider claude`

**Setup:**
- `ANTHROPIC_API_KEY` set to valid key
- Network access available for web_search tool

**Expected behavior:**
1. Pattern library returns `react` with similarity ≥ 0.65
2. `web_search` tool registered in MCP tool registry
3. Agent calls `web_search("MCP server implementations GitHub")` at least once
4. Agent produces Final Answer listing ≥ 3 MCP server names with summaries
5. `eval_benchmark.py` scores: task_success ≥ 0.70, composite ≥ 0.45
6. Run persisted to SQLite `runs` table
7. Benchmark result persisted to `benchmark_results` table

**Pass criteria:** Final answer contains ≥ 3 named MCP implementations. Composite score ≥ 0.45.

---

## Scenario 2: Provider Fallback — Claude Unavailable

**Trigger:** `agent run --pattern chain_of_thought --task "Explain the difference between ReAct and CoT" --provider claude` with `ANTHROPIC_API_KEY` unset

**Setup:**
- `ANTHROPIC_API_KEY` not set
- `OPENAI_API_KEY` set to valid key

**Expected behavior:**
1. `ClaudeAdapter.complete()` raises `RuntimeError: ANTHROPIC_API_KEY not set`
2. `ProviderRouter` catches error and falls back to `openai`
3. `OpenAIAdapter.complete()` succeeds
4. `CompletionResult.provider_used == "openai"`
5. Final answer explains ReAct vs CoT differences
6. No exception raised to CLI

**Pass criteria:** Command completes successfully with `provider_used == "openai"`. No traceback.

---

## Scenario 3: Provider Benchmark Comparison

**Trigger:** `agent benchmark --pattern cot --task "What are the 5 most important properties of a good AI agent?" --providers claude,openai,ollama`

**Setup:**
- At least Claude and OpenAI keys set; Ollama running locally OR mocked

**Expected behavior:**
1. 3 concurrent `run_pattern()` calls dispatched via `asyncio.gather`
2. Each run produces a `BenchmarkResult` with all 5 metrics
3. Comparison Markdown table shows all 3 providers sorted by composite score
4. Best provider highlighted with ★
5. Provider comparison persisted to `benchmark_results` table

**Pass criteria:** Table contains 3 rows. Composite scores in [0, 1]. Best provider identified.

---

## Scenario 4: Pattern Semantic Search

**Trigger:** `agent pattern search --query "agent that thinks before acting with tools"`

**Setup:**
- BGE-large model available (or FAISS-based vector index built)

**Expected behavior:**
1. `PatternLibrary.search()` encodes query with BGE-large (or keyword fallback)
2. Returns top-3 patterns sorted by similarity
3. `react` pattern should appear in top-3 (highest relevance to "thinks before acting with tools")
4. Each result includes: name, description, similarity, tools_required, recommended_providers

**Pass criteria:** `react` in top-3 results. All results have similarity ≥ 0.50.

---

## Scenario 5: Code Agent Pattern — Execution and Debugging

**Trigger:** `agent run --pattern code_agent --task "Write Python code to compute the Fibonacci sequence up to n=20 and return the result as a JSON list" --provider claude`

**Expected behavior:**
1. Pattern library returns `code_agent` pattern
2. `code_execute` tool registered
3. Agent writes Python code and calls `code_execute`
4. If code has errors: agent reads stderr, debugs, re-executes
5. Final answer contains JSON list `[0, 1, 1, 2, 3, 5, 8, ...]` with correct values
6. `error_recovery` metric = 1.0 if any retry was needed and succeeded

**Pass criteria:** Final answer contains valid Fibonacci sequence as JSON. `task_success ≥ 0.80`.

---

## Scenario 6: Knowledge Crawler Update

**Trigger:** `agent update-knowledge` (or REST POST `/knowledge/update`)

**Setup:**
- Network access available
- `SECOND-KNOWLEDGE-BRAIN.md` writable

**Expected behavior:**
1. `KnowledgeUpdater.run_daily_update()` crawls ArXiv cs.AI category
2. At least 1 new paper discovered and scored
3. SHA256 dedup check: paper not already in `knowledge_hashes` table
4. Paper appended to `## Knowledge Update Log` section in SECOND-KNOWLEDGE-BRAIN.md
5. `memory_manager.mark_paper_known()` called with paper identifier
6. Returns: `papers_added >= 1`, `next_scheduled` contains future ISO date

**Pass criteria:** `papers_added ≥ 1`. SECOND-KNOWLEDGE-BRAIN.md updated. Duplicate run returns `papers_added = 0`.

---

## Scenario 7: Graceful Degradation — All LLM Providers Unavailable

**Trigger:** `agent run --pattern react --task "test"` with all API keys unset and Ollama not running

**Expected behavior:**
1. `ClaudeAdapter` raises `RuntimeError: ANTHROPIC_API_KEY not set`
2. `OpenAIAdapter` raises `RuntimeError: OPENAI_API_KEY not set`
3. `OllamaAdapter` raises connection error (Ollama not running)
4. `ProviderRouter` exhausts all providers
5. `AllProvidersExhausted` exception raised
6. REST API returns HTTP 500 with JSON error body (not hang, not empty response)
7. Error message identifies which providers were tried

**Pass criteria:** HTTP 500 returned in < 10s. Error JSON body present with provider list.

---

## Scenario 8: REST API Full Integration

**Trigger:** `docker compose up` then curl REST endpoints

**Setup:**
- Docker Compose running with agentcore-agent container
- `ANTHROPIC_API_KEY` set in `.env`

**Expected behavior:**
1. `GET /health` → `{"status": "ok", "service": "agentcore-enhanced"}`
2. `GET /patterns` → JSON array with 15 pattern objects
3. `POST /patterns/search {"query": "react"}` → top-3 patterns with similarity scores
4. `POST /run {"pattern": "chain_of_thought", "task": "List 3 benefits of modular software", "provider": "claude"}` → RunResponse with non-empty `final_answer`
5. `GET /cost` → JSON with `total_usd` float and `by_provider` dict
6. `GET /metrics` → Prometheus text format with `agentcore_runs_total` metric

**Pass criteria:** All 6 endpoints return 200 with expected schema. Run produces non-empty final answer.
