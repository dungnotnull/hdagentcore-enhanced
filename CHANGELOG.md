# Changelog

All notable changes to agentcore-enhanced will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI/CD pipeline with GitHub Actions
- Comprehensive documentation in `docs/` directory
- Configuration management module (`agent/modules/config.py`)
- Security policy and vulnerability disclosure process
- Contributing guidelines and code of conduct
- Issue templates for bug reports and feature requests
- Dependabot for automated dependency updates

### Changed
- Improved error handling for missing API keys
- Better validation of configuration parameters
- Enhanced documentation across all modules

### Fixed
- Graceful handling of missing provider API keys
- Better error messages for configuration issues

## [1.0.0] - 2025-01-10

### Added
- **Provider Abstraction**: Unified API across 6 LLM providers (Claude, OpenAI, Azure, GCP, Ollama, vLLM)
- **MCP Integration**: Full Model Context Protocol server/client with tool registry
- **Evaluation Benchmark**: 5-metric scoring system (task success, token efficiency, error recovery, quality, latency)
- **Pattern Library**: 15 reusable agent patterns with semantic search
- **Knowledge Crawler**: Daily ArXiv/Semantic Scholar/GitHub crawler
- **HuggingFace Integration**: BGE-large, MiniLM, CodeT5+, BGE-reranker models
- **Orchestrator**: Central coordinator with lazy module initialization
- **CLI**: Full-featured command-line interface
- **FastAPI Server**: REST API with OpenAPI documentation
- **SQLite Persistence**: Run history, benchmark results, cost tracking
- **Docker Support**: Multi-stage Dockerfile with Docker Compose
- **Prometheus Metrics**: Built-in metrics endpoint
- **Memory Manager**: Thread-safe SQLite memory with run tracking

### Providers
- Claude (anthropic): `claude-opus-4-8`, `claude-sonnet-4-6`
- OpenAI: `gpt-4o`, `gpt-4o-mini`
- Azure AI Foundry: OpenAI models via Azure
- GCP Vertex AI: `gemini-1.5-pro`, `gemini-1.5-flash`
- Ollama: Local models (`llama3`, `mistral`, etc.)
- vLLM: Local OpenAI-compatible server

### Agent Patterns
1. ReAct (Reason + Act)
2. Chain-of-Thought
3. Tree-of-Thought
4. Multi-Agent Parliament
5. Critic-Actor
6. Memory-Augmented
7. Tool-Use Specialist
8. Code Agent
9. Document Analyst
10. Self-Refine
11. Planner-Executor
12. Supervisor-Worker
13. Reflection Agent
14. Constitutional Agent
15. Research Agent

### CLI Commands
- `agentcore run` - Execute agent pattern
- `agentcore benchmark` - Compare providers
- `agentcore pattern` - Search/list patterns
- `agentcore update-knowledge` - Run research crawler
- `agentcore cost-report` - Cost breakdown
- `agentcore serve` - Start API server

### API Endpoints
- `GET /health` - Health check
- `POST /run` - Execute pattern
- `POST /benchmark` - Compare providers
- `GET /patterns` - List all patterns
- `POST /patterns/search` - Semantic search
- `POST /knowledge/update` - Trigger crawler
- `GET /cost` - Cost report
- `GET /metrics` - Prometheus metrics

### Documentation
- README with quickstart guide
- Architecture documentation
- Pattern reference guide
- API documentation (OpenAPI)
- Docker deployment guide

### Testing
- 40+ unit tests
- Integration tests
- Provider adapter tests
- MCP manager tests
- Benchmark tests
- Pattern library tests

### Dependencies
- fastapi>=0.115.5
- anthropic>=0.40.0
- openai>=1.55.3
- sentence-transformers>=3.3.1
- transformers>=4.47.0
- torch>=2.5.1
- faiss-cpu>=1.9.0
- And more (see pyproject.toml)

## [0.1.0] - 2024-12-01

### Added
- Initial fork from awslabs/agentcore-samples
- Basic provider abstraction (Claude only)
- ReAct pattern implementation
- Simple CLI interface
- Basic Docker setup

[Unreleased]: https://github.com/yourusername/agentcore-enhanced/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/agentcore-enhanced/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/yourusername/agentcore-enhanced/releases/tag/v0.1.0
