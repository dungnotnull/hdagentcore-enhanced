# agentcore-enhanced

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Provider-portable multi-cloud agent orchestrator with self-evaluating benchmark, MCP integration, and daily research self-learning.**

## Overview

`agentcore-enhanced` extends AWS AgentCore Samples with a provider-portable abstraction layer supporting 6 LLM providers (Claude, OpenAI, Azure AI Foundry, GCP Vertex AI, Ollama, vLLM), built-in evaluation benchmark that scores every agent pattern on task success/token efficiency/error recovery, and a daily self-learning research loop that continuously ingests new agent architecture papers.

### Key Features

- **Provider-Portable**: Unified API across 6 LLM providers with automatic fallback chain
- **MCP-Native**: First-class Model Context Protocol server/client with tool registry
- **Self-Evaluating**: 5-metric benchmark scores every run (task success, token efficiency, error recovery, quality, latency)
- **15 Agent Patterns**: ReAct, CoT, Tree-of-Thought, multi-agent parliament, memory-augmented, and more
- **Semantic Search**: BGE-large + FAISS + BGE-reranker for intelligent pattern retrieval
- **Research Loop**: Daily ArXiv/Semantic Scholar/GitHub crawler keeping knowledge current
- **Production-Ready**: Docker Compose, Prometheus metrics, SQLite persistence, FastAPI server

## Quick Start

### Prerequisites

- Python 3.12+
- Docker (optional, for containerized deployment)
- API keys for at least one LLM provider

### Installation

```bash
git clone https://github.com/yourusername/agentcore-enhanced.git
cd agentcore-enhanced

pip install -e .
```

Or using uv (faster):

```bash
pip install uv
uv pip install -e .
```

### Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys. At minimum, configure one provider:

```bash
# Required - at least one provider
ANTHROPIC_API_KEY=sk-ant-xxx          # Claude (recommended)
OPENAI_API_KEY=sk-xxx                  # OpenAI (fallback)
AZURE_OPENAI_API_KEY=xxx               # Azure (fallback)
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
GCP_PROJECT_ID=xxx                    # GCP (fallback)

# Optional - for local inference
OLLAMA_BASE_URL=http://localhost:11434
VLLM_BASE_URL=http://localhost:8000/v1

# Optional - for knowledge crawling
GITHUB_TOKEN=ghp_xxx                   # GitHub personal access token
```

### Run Your First Agent

```bash
# Run ReAct pattern on a task
agentcore run --pattern react --task "Find the latest research on multi-agent systems"

# Benchmark providers
agentcore benchmark --pattern "chain-of-thought" --task "Solve: What is 15 * 23 + 7?" --providers claude,openai,ollama

# Search patterns
agentcore pattern search --query "code execution"

# List all patterns
agentcore pattern list
```

### Start the API Server

```bash
agentcore serve --host 0.0.0.0 --port 7865
```

The server includes:
- `GET /health` - Health check
- `POST /run` - Execute agent pattern
- `POST /benchmark` - Compare providers
- `GET /patterns` - List all patterns
- `POST /patterns/search` - Semantic pattern search
- `GET /metrics` - Prometheus metrics
- `GET /cost` - Cost breakdown

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Orchestrator (agent/orchestrator.py)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Pattern Lib  │→ │ Provider     │→ │  Evaluator      │   │
│  │ (15 patterns)│  │ Router (6)   │  │  (5 metrics)     │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
│        ↓                   ↓                    ↓            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Modules                                             │  │
│  │  pattern_library.py  provider_adapter.py           │  │
│  │  eval_benchmark.py    mcp_manager.py               │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
           ↓                  ↓                  ↓
    Claude/OpenAI        MCP Tools         HuggingFace
    Azure/GCP/Ollama     (search,code)     (BGE,MiniLM)
         ↓                  ↓                  ↓
  Benchmark Report    Markdown Catalog   Knowledge Base
```

## Available Patterns

| Pattern | Description | Tools | Best For |
|---------|-------------|-------|----------|
| `react` | ReAct: iterative thought/action/observation loop | web_search, code_execute | Research, fact-finding |
| `chain_of_thought` | CoT: step-by-step reasoning before answer | - | Math, logic, reasoning |
| `tree_of_thought` | ToT: branching reasoning with backtracking | - | Puzzles, strategy |
| `multi_agent_parliament` | N specialized agents debate and vote | web_search | High-stakes decisions |
| `critic_actor` | Critic evaluates and improves actor output | - | Code review, writing |
| `memory_augmented` | Vector store retrieval in every prompt | file_read, file_write | Long-running projects |
| `tool_use_specialist` | Optimized for rich tool libraries | web_search, code_execute, files | Data collection, APIs |
| `code_agent` | Write → execute → debug → iterate Python | code_execute, files | Programming, analysis |
| `document_analyst` | Chunk → embed → RAG over documents | file_read | Long document Q&A |
| `self_refine` | Agent critiques own output iteratively | - | Writing, code quality |
| `planner_executor` | Separate planning and execution phases | web_search, code_execute | Multi-step tasks |
| `supervisor_worker` | Supervisor delegates to specialized workers | - | Parallelizable tasks |
| `reflection_agent` | Reflects on past failures for improvement | file_read, file_write | Iterative improvement |
| `constitutional_agent` | Output checked against principles | - | Safe content generation |
| `research_agent` | Search → read → synthesize report | web_search, file_write | Research synthesis |

## Provider Configuration

### Claude (Recommended)

```bash
ANTHROPIC_API_KEY=sk-ant-xxx
```

Models: `claude-opus-4-8`, `claude-sonnet-4-6`

### OpenAI

```bash
OPENAI_API_KEY=sk-xxx
```

Models: `gpt-4o`, `gpt-4o-mini`

### Azure AI Foundry

```bash
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
```

Models: `gpt-4o` (via Azure)

### GCP Vertex AI

```bash
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
```

Requires `google-cloud-aiplatform` package.

Models: `gemini-1.5-pro`

### Ollama (Local)

```bash
OLLAMA_BASE_URL=http://localhost:11434
```

Requires Ollama running locally.

Models: `llama3`, `mistral`, etc.

### vLLM (Local)

```bash
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=optional
```

Requires vLLM server running.

## API Usage

### Execute Pattern

```bash
curl -X POST http://localhost:7865/run \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "react",
    "task": "Find the population of Tokyo",
    "provider": "claude",
    "max_steps": 10
  }'
```

### Benchmark Providers

```bash
curl -X POST http://localhost:7865/benchmark \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "chain-of-thought",
    "task": "Solve: What is 2^10?",
    "providers": ["claude", "openai", "ollama"],
    "max_steps": 5
  }'
```

### Search Patterns

```bash
curl -X POST http://localhost:7865/patterns/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "multi-agent debate",
    "top_k": 3
  }'
```

## Docker Deployment

### Quick Start

```bash
docker compose up -d
```

### With GPU Support

```bash
docker compose --profile gpu up -d
```

### Manual Build

```bash
docker build -f docker/Dockerfile -t agentcore-enhanced:latest .
docker run -p 7865:7865 --env-file .env agentcore-enhanced:latest
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/yourusername/agentcore-enhanced.git
cd agentcore-enhanced

pip install -e ".[dev]"
pre-commit install
```

### Run Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black agent/ tools/ tests/
ruff check agent/ tools/ tests/
```

## Benchmark Metrics

Every agent run is scored on 5 metrics:

1. **Task Success** (0-1): LLM-judged completion quality
2. **Token Efficiency** (0-1): Useful tokens / total tokens
3. **Error Recovery** (0-1): Recovered errors / total errors
4. **Quality Score** (0-5): LLM-judged output quality
5. **Latency** (ms): Normalized execution time

Composite score = weighted average (30% success + 20% efficiency + 20% recovery + 15% latency + 15% quality)

## Knowledge Crawler

Daily automatic crawl of:
- ArXiv (cs.AI, cs.MA, cs.LG, cs.SE)
- Semantic Scholar (multi-agent systems queries)
- GitHub Releases (agent framework repos)

New papers are appended to `SECOND-KNOWLEDGE-BRAIN.md`.

Manually trigger:

```bash
agentcore update-knowledge
```

## Cost Tracking

Track LLM costs per provider and pattern:

```bash
agentcore cost-report --days 30
```

Or via API:

```bash
curl http://localhost:7865/cost?days=30
```

## Prometheus Metrics

```bash
curl http://localhost:7865/metrics
```

Metrics include:
- `agentcore_runs_total` - Total agent runs
- `agentcore_benchmark_composite_score_avg` - Average composite score
- `agentcore_cost_usd_total` - Total LLM cost

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

Please see [SECURITY.md](SECURITY.md) for our security policy and vulnerability disclosure process.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Forked from [awslabs/agentcore-samples](https://github.com/awslabs/agentcore-samples)
- Inspired by ReAct, AutoGPT, CrewAI, and LangChain patterns
- Powered by HuggingFace models (BGE-large, MiniLM, CodeT5+, BGE-reranker)

## Citation

If you use agentcore-enhanced in your research, please cite:

```bibtex
@software{agentcore_enhanced,
  title={agentcore-enhanced: Provider-Portable Multi-Cloud Agent Orchestrator},
  author={Contributors},
  year={2025},
  url={https://github.com/yourusername/agentcore-enhanced}
}
```

## Support

- GitHub Issues: [Bug reports, feature requests](https://github.com/yourusername/agentcore-enhanced/issues)
- Discussions: [Questions, ideas](https://github.com/yourusername/agentcore-enhanced/discussions)
- Security: [security@yourusername.com](mailto:security@yourusername.com)
