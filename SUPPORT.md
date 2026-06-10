# Support

Thank you for using agentcore-enhanced! This document outlines the various ways to get help and support.

## Table of Contents

- [Community Support](#community-support)
- [Documentation](#documentation)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)
- [Security Issues](#security-issues)
- [Professional Support](#professional-support)
- [Contributing](#contributing)

## Community Support

### GitHub Discussions

For questions, ideas, and general discussion:

- **GitHub Discussions**: [https://github.com/yourusername/agentcore-enhanced/discussions](https://github.com/yourusername/agentcore-enhanced/discussions)

Categories:
- `q&a`: Ask questions
- `ideas`: Share ideas and proposals
- `show-and-tell`: Share your projects
- `documentation`: Discuss documentation

### Discord / Slack (Coming Soon)

We're planning to launch a Discord server for real-time community support.

## Documentation

### Quick Links

- [README](README.md) - Project overview and quickstart
- [Architecture Documentation](docs/architecture.md) - System design and implementation
- [Pattern Reference](docs/patterns.md) - All 15 agent patterns detailed
- [API Documentation](https://agentcore-enhanced.readthedocs.io) - Full API reference
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute

### Common Issues

#### Installation Issues

**Problem**: `ModuleNotFoundError: No module named 'agent'`

**Solution**:
```bash
pip install -e .
# or
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Problem**: `anthropic package not installed`

**Solution**:
```bash
pip install anthropic
# or install all dependencies
pip install -e ".[dev]"
```

#### Configuration Issues

**Problem**: `ANTHROPIC_API_KEY not set`

**Solution**: Create `.env` file from `.env.example` and add your API key:
```bash
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-xxx
```

**Problem**: No providers configured

**Solution**: At minimum, set one provider API key. For local testing:
```bash
# Install and run Ollama
ollama pull llama3
# Then in .env:
OLLAMA_BASE_URL=http://localhost:11434
```

#### Runtime Issues

**Problem**: `AllProvidersExhausted: All providers failed`

**Solution**:
1. Check your API keys are valid
2. Check network connectivity
3. Verify provider is not rate-limited
4. Try with `PRIVACY_MODE=true` and Ollama

**Problem**: Docker container exits immediately

**Solution**:
```bash
# Check logs
docker compose logs agentcore-agent

# Common issue: Missing .env file
docker run --env-file .env agentcore-enhanced:latest
```

## Reporting Issues

### Bug Reports

Before reporting, please:

1. Search existing issues: [GitHub Issues](https://github.com/yourusername/agentcore-enhanced/issues)
2. Try the latest version: `pip install --upgrade agentcore-enhanced`
3. Create a minimal reproducible example

When reporting, use the bug report template and include:
- Version: `agentcore --version`
- Python version: `python --version`
- OS: `uname -a` (Linux/macOS) or system info (Windows)
- Minimal code to reproduce
- Full error traceback
- Configuration (with sensitive keys removed)

### Performance Issues

If experiencing slowness:

1. Check which provider you're using (Claude > OpenAI > local)
2. Monitor resource usage: `top` or `htop`
3. Check network latency to provider
4. Consider using `ollama` or `vllm` for local inference

Include metrics when reporting:
- Latency per provider (from `/cost` endpoint)
- Token counts (from benchmark report)
- Hardware specs

### Security Vulnerabilities

**Do not** report security issues via public GitHub issues.

Instead, email: [security@yourusername.com](mailto:security@yourusername.com)

See [SECURITY.md](SECURITY.md) for details.

## Feature Requests

We welcome feature requests! Please:

1. Check existing requests first
2. Use the feature request template
3. Provide use cases and examples
4. Consider if it fits the project scope

### Request Types

**High Priority**:
- Provider bugs/fallback issues
- Pattern improvements
- Performance optimizations

**Medium Priority**:
- New provider support
- New agent patterns
- Documentation improvements

**Lower Priority**:
- Nice-to-have features
- Opinionated changes
- Breaking changes

## Professional Support

### Enterprise Support (Coming Soon)

We're planning enterprise support options including:
- Priority bug fixes
- Custom integrations
- On-premises deployment support
- Training and consulting

### Consulting

For custom agent development, training, or architecture consulting, contact: [consulting@yourusername.com](mailto:consulting@yourusername.com)

## Contributing

We value all contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Contribution Areas

- **Code**: New features, bug fixes, optimizations
- **Patterns**: Share your agent patterns
- **Tests**: Improve test coverage
- **Docs**: Improve documentation
- **Reviews**: Review pull requests

### First-time Contributors

We welcome first-time contributors! Look for issues labeled `good first issue`.

## Getting Help Flowchart

```
Need help?
│
├─ Quick question?
│  └─→ GitHub Discussions
│
├─ Bug or error?
│  └─→ Check docs → Search issues → Create issue
│
├─ Feature idea?
│  └─→ GitHub Discussions → Feature request
│
├─ Security issue?
│  └─→ Email: security@yourusername.com
│
└─ Want to contribute?
   └─→ CONTRIBUTING.md → Look for issues → Submit PR
```

## Response Times

| Channel | Expected Response |
|---------|------------------|
| GitHub Discussions | 1-3 days |
| GitHub Issues | 2-7 days |
| Security Email | 48 hours |
| Pull Requests | 3-7 days |

*Note: These are volunteer-led efforts, so response times may vary.*

## Other Resources

### Similar Projects

- [LangChain](https://github.com/langchain-ai/langchain)
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)
- [CrewAI](https://github.com/joaomdmoura/crewAI)

### Learning Resources

- [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [MCP Specification](https://modelcontextprotocol.io)

## Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/agentcore-enhanced/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/agentcore-enhanced/discussions)
- **Security**: [security@yourusername.com](mailto:security@yourusername.com)
- **Consulting**: [consulting@yourusername.com](mailto:consulting@yourusername.com)

---

Thank you for being part of the agentcore-enhanced community!
