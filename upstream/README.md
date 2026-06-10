# Upstream: awslabs/agentcore-samples

**Pinned tag:** `v0.1.0`
**Repository:** https://github.com/awslabs/agentcore-samples
**Clone command:** `git clone --branch v0.1.0 https://github.com/awslabs/agentcore-samples.git upstream/`

---

## Upstream Baseline (v0.1.0)

| Capability | Upstream | agentcore-enhanced Delta |
|-----------|---------|--------------------------|
| LLM providers | 1 (AWS Bedrock only) | +5 providers (Claude, OpenAI, Azure, GCP, Ollama) |
| Agent patterns | ~8 (AWS-specific) | 15 provider-agnostic patterns in typed catalog |
| Tool integration | Ad-hoc function calling | MCP server/client + tool registry + JSON Schema validation |
| Evaluation | None (manual) | 5-metric benchmark suite auto-scored per run |
| Provider fallback | None | Automatic Claude → OpenAI → Azure → GCP → Ollama chain |
| Knowledge base | None | Daily ArXiv/Scholar crawl → SECOND-KNOWLEDGE-BRAIN.md |
| Observability | None | Prometheus metrics at /metrics |
| REST API | None | FastAPI 7-endpoint server |

---

## Sidecar Architecture

agentcore-enhanced uses a **sidecar pattern**: all new AI code lives in `agent/` and `ai_layer/`, with `upstream/` holding unmodified awslabs/agentcore-samples code. This enables pulling upstream updates without merge conflicts.

```
agentcore-enhanced/
├── upstream/          ← unmodified awslabs/agentcore-samples @ v0.1.0
├── agent/             ← new AI orchestration code (sidecar)
├── tools/             ← universal tools (knowledge_updater, llm_client, hf_model_manager)
├── ai_layer/          ← integration patches and documentation
└── ...
```

---

## Three Quantified Improvement Targets

| Target | Baseline | Target | Test Method |
|--------|---------|--------|-------------|
| Provider coverage | 1 | 6 | Integration tests: all 6 providers return CompletionResult |
| Benchmark automation | 0 metrics | 5 metrics/run in < 5s overhead | pytest: composite_score in [0,1] for all runs |
| Pattern catalog | ~8 patterns | 15 patterns | pytest: all 15 patterns searchable with similarity ≥ 0.65 |
