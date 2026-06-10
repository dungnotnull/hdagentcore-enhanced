# Contributing to agentcore-enhanced

Thank you for your interest in contributing to agentcore-enhanced! This document provides guidelines and instructions for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Git
- Docker (optional, for containerized testing)

### Development Setup

1. Fork the repository on GitHub

2. Clone your fork locally:

```bash
git clone https://github.com/yourusername/agentcore-enhanced.git
cd agentcore-enhanced
```

3. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

4. Install development dependencies:

```bash
pip install -e ".[dev]"
```

Or using uv (faster):

```bash
pip install uv
uv pip install -e ".[dev]"
```

5. Install pre-commit hooks:

```bash
pre-commit install
```

6. Copy environment configuration:

```bash
cp .env.example .env
```

7. Edit `.env` and add your API keys for testing

### Verify Installation

```bash
# Run tests
pytest tests/ -v

# Run linting
ruff check agent/ tools/ tests/

# Check formatting
black --check agent/ tools/ tests/
```

## Development Workflow

### Branch Naming

Use descriptive branch names:

- `feature/add-new-pattern`
- `fix/provider-timeout-issue`
- `docs/update-api-guide`
- `refactor/improve-benchmark-scoring`
- `test/add-integration-tests`

### Commit Messages

Follow conventional commits:

```
feat: add new self-critique agent pattern
fix: resolve Azure API timeout on large prompts
docs: update README with Docker instructions
refactor: simplify provider fallback logic
test: add integration tests for MCP tools
chore: upgrade dependencies to latest versions
```

Format: `<type>: <description>`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Development Workflow

1. Create a new branch from `main`:

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

2. Make your changes

3. Run tests and linting:

```bash
pytest tests/ -v
ruff check agent/ tools/ tests/
black agent/ tools/ tests/
```

4. Commit your changes:

```bash
git add .
git commit -m "feat: description of your changes"
```

5. Push to your fork:

```bash
git push origin feature/your-feature-name
```

6. Create a pull request on GitHub

## Coding Standards

### Python Style

We follow PEP 8 with these tools:

- **Black**: Code formatting
- **Ruff**: Fast linting
- **isort**: Import sorting (handled by Black)

```bash
# Format code
black agent/ tools/ tests/

# Check linting
ruff check agent/ tools/ tests/

# Auto-fix linting issues
ruff check --fix agent/ tools/ tests/
```

### Type Hints

All new code should include type hints:

```python
from typing import Optional, List

def run_agent(
    pattern: str,
    task: str,
    provider: str = "claude",
    max_steps: int = 10,
) -> dict:
    """Execute an agent pattern."""
    ...
```

### Documentation

All modules, classes, and functions should have docstrings:

```python
def calculate_composite_score(
    task_success: float,
    token_efficiency: float,
    error_recovery: float,
    latency_score: float,
    quality_score: float,
) -> float:
    """Calculate weighted composite benchmark score.

    Args:
        task_success: LLM-judged task completion (0.0-1.0)
        token_efficiency: Useful token ratio (0.0-1.0)
        error_recovery: Error recovery rate (0.0-1.0)
        latency_score: Normalized latency score (0.0-1.0)
        quality_score: Output quality score (0.0-5.0)

    Returns:
        Composite score between 0.0 and 1.0
    """
    weights = (0.30, 0.20, 0.20, 0.15, 0.15)
    return (
        weights[0] * task_success
        + weights[1] * token_efficiency
        + weights[2] * error_recovery
        + weights[3] * latency_score
        + weights[4] * (quality_score / 5.0)
    )
```

### Error Handling

Use specific exceptions and include helpful messages:

```python
# Good
if not api_key:
    raise ValueError(f"{provider_name}_API_KEY not set in environment")

# Avoid
if not api_key:
    raise Exception("No API key")
```

Use async/await consistently for I/O operations:

```python
async def fetch_paper(arxiv_id: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ARXIV_API}/{arxiv_id}") as resp:
            return await resp.json()
```

### Constants

Use UPPER_CASE for module-level constants:

```python
# Good
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
BENCHMARK_WEIGHTS = (0.30, 0.20, 0.20, 0.15, 0.15)

# Avoid
max_retries = 3
```

## Testing Guidelines

### Test Structure

Tests are organized by module:

```
tests/
├── test_provider_adapter.py
├── test_mcp_manager.py
├── test_eval_benchmark.py
├── test_pattern_library.py
├── test_orchestrator.py
└── test_integration.py
```

### Writing Tests

Use `unittest` or `pytest`. Mock external API calls:

```python
import unittest
from unittest.mock import AsyncMock, patch

class TestProviderAdapter(unittest.TestCase):
    @patch('agent.modules.provider_adapter.anthropic.AsyncAnthropic')
    async def test_claude_completion(self, mock_client):
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Hello")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_response

        adapter = ClaudeAdapter()
        result = await adapter.complete(
            messages=[{"role": "user", "content": "Hi"}],
        )

        self.assertEqual(result.text, "Hello")
        self.assertEqual(result.provider_used, "claude")
```

### Test Coverage

Aim for >80% coverage on new code. Check coverage:

```bash
pytest --cov=agent --cov=tools --cov-report=html
```

### Integration Tests

Add integration tests for end-to-end workflows:

```python
class TestIntegration(unittest.TestCase):
    def test_full_agent_run(self):
        orch = AgentCoreOrchestrator()
        result = asyncio.run(orch.run_pattern(
            pattern_query="react",
            task="Simple task",
            provider="ollama",
            max_steps=3,
        ))
        self.assertIn("composite_score", result["benchmark"])
```

## Documentation Standards

### Code Documentation

- All public APIs must have docstrings
- Use Google style docstrings (preferred)
- Include examples for complex functions

### README Documentation

Update README.md when:
- Adding new patterns
- Adding new providers
- Changing configuration
- Adding new CLI commands
- Breaking changes

### API Documentation

API documentation is auto-generated from type hints and docstrings via FastAPI's OpenAPI.

### Pattern Documentation

When adding new patterns:

1. Update `agent/modules/pattern_library.py`
2. Add pattern to README.md table
3. Add usage example in docs/patterns.md

## Pull Request Process

### Before Submitting

1. **Code Quality**:
   - Run tests: `pytest tests/ -v`
   - Check linting: `ruff check agent/ tools/ tests/`
   - Format code: `black agent/ tools/ tests/`
   - Run pre-commit: `pre-commit run --all-files`

2. **Documentation**:
   - Update docstrings for new/modified functions
   - Update README.md if user-facing changes
   - Add tests for new functionality

3. **Commits**:
   - Squash related commits
   - Use conventional commit messages
   - Remove fixup commits

### Pull Request Description

Use this template:

```markdown
## Description
Brief description of changes

## Type
- [ ] Bug fix
- [ ] Feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project standards
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] No merge conflicts
- [ ] Commit messages follow conventions

## Related Issues
Fixes #123
Related to #456
```

### Review Process

1. Automated checks must pass (CI/CD)
2. At least one maintainer approval required
3. Address all review comments
4. Update PR title to match conventional commit

### After Merging

- Delete your branch (or keep it updated)
- Update related issues
- Celebrate! 🎉

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.x.x`
4. Push tag: `git push origin v1.x.x`
5. GitHub Actions automatically builds and publishes to PyPI

### Version Bumping

We follow Semantic Versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

## Getting Help

- GitHub Issues: Bug reports, feature requests
- GitHub Discussions: Questions, ideas
- Discord/Slack: (if available)

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to agentcore-enhanced!
