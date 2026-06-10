"""config.py — Configuration management with validation and helpful error messages."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal, Optional


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ProviderConfig:
    """Configuration for a specific LLM provider."""

    name: str
    api_key_env: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    project_id: Optional[str] = None
    location: str = "us-central1"
    default_model: str = ""
    available: bool = False

    def __post_init__(self):
        self.api_key = os.getenv(self.api_key_env, "")
        self.available = bool(self.api_key) or self.name in {"ollama", "vllm"}


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 7865
    workers: int = 1
    reload: bool = False
    enable_metrics: bool = True
    metrics_path: str = "/metrics"


@dataclass
class SecurityConfig:
    """Security configuration."""

    cors_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    cors_allow_headers: str = "*"
    max_request_size: int = 10485760  # 10MB
    max_tool_result_size: int = 1048576  # 1MB


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""

    judge_model: str = "claude-sonnet-4-6"
    composite_score_threshold: float = 0.40
    latency_max_ms: float = 30000.0
    enable_pattern_reranking: bool = True
    enable_knowledge_dedup: bool = True
    enable_cost_tracking: bool = True
    enable_error_recovery_tracking: bool = True


@dataclass
class ToolConfig:
    """Tool configuration."""

    code_exec_timeout: int = 10
    workspace_path: str = "/app/workspace"
    mcp_server_port: int = 8765


@dataclass
class HuggingFaceConfig:
    """HuggingFace configuration."""

    home: str = "/app/models"
    hub_cache: str = "/app/models/hub"
    datasets_cache: str = "/app/models/datasets"
    force_cpu: bool = False


@dataclass
class CrawlerConfig:
    """Knowledge crawler configuration."""

    github_token: Optional[str] = None
    enable_daily_crawl: bool = True
    crawl_schedule: str = "06:00"
    max_papers_per_day: int = 10


@dataclass
class AppConfig:
    """Main application configuration."""

    debug: bool = False
    dev_mode: bool = False
    log_level: LogLevel = LogLevel.INFO
    log_format: Literal["json", "text"] = "text"
    database_path: str = "/app/data/agentcore.db"
    privacy_mode: bool = False

    provider: dict[str, ProviderConfig] = field(default_factory=dict)
    server: ServerConfig = field(default_factory=ServerConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    huggingface: HuggingFaceConfig = field(default_factory=HuggingFaceConfig)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)


class ConfigurationError(Exception):
    """Configuration error with helpful message."""

    def __init__(self, message: str, fix: str):
        self.message = message
        self.fix = fix
        super().__init__(f"{message}\n\nFix: {fix}")


class ConfigManager:
    """Load and validate configuration from environment variables."""

    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._load_called = False

    def load(self, *, raise_on_error: bool = False) -> AppConfig:
        """Load configuration from environment.

        Args:
            raise_on_error: If True, raise ConfigurationError for missing required config.
                            If False, print warnings and continue with defaults.

        Returns:
            AppConfig instance

        Raises:
            ConfigurationError: If raise_on_error=True and required config is missing.
        """
        self._load_called = True

        config = AppConfig(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            dev_mode=os.getenv("DEV_MODE", "false").lower() == "true",
            log_level=LogLevel(os.getenv("LOG_LEVEL", "INFO")),
            log_format=os.getenv("LOG_FORMAT", "text"),
            database_path=os.getenv("DATABASE_PATH", "/app/data/agentcore.db"),
            privacy_mode=os.getenv("PRIVACY_MODE", "false").lower() == "true",
        )

        config.server = ServerConfig(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "7865")),
            workers=int(os.getenv("WORKERS", "1")),
            reload=os.getenv("RELOAD", "false").lower() == "true",
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
            metrics_path=os.getenv("METRICS_PATH", "/metrics"),
        )

        config.security = SecurityConfig(
            cors_origins=os.getenv("CORS_ORIGINS", "*"),
            cors_allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
            cors_allow_methods=os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS"),
            cors_allow_headers=os.getenv("CORS_ALLOW_HEADERS", "*"),
            max_request_size=int(os.getenv("MAX_REQUEST_SIZE", "10485760")),
            max_tool_result_size=int(os.getenv("MAX_TOOL_RESULT_SIZE", "1048576")),
        )

        config.benchmark = BenchmarkConfig(
            judge_model=os.getenv("BENCHMARK_JUDGE_MODEL", "claude-sonnet-4-6"),
            composite_score_threshold=float(os.getenv("COMPOSITE_SCORE_THRESHOLD", "0.40")),
            latency_max_ms=float(os.getenv("LATENCY_MAX_MS", "30000")),
            enable_pattern_reranking=os.getenv("ENABLE_PATTERN_RERANKING", "true").lower() == "true",
            enable_knowledge_dedup=os.getenv("ENABLE_KNOWLEDGE_DEDUP", "true").lower() == "true",
            enable_cost_tracking=os.getenv("ENABLE_COST_TRACKING", "true").lower() == "true",
            enable_error_recovery_tracking=os.getenv("ENABLE_ERROR_RECOVERY_TRACKING", "true").lower() == "true",
        )

        config.tools = ToolConfig(
            code_exec_timeout=int(os.getenv("CODE_EXEC_TIMEOUT", "10")),
            workspace_path=os.getenv("WORKSPACE_PATH", "/app/workspace"),
            mcp_server_port=int(os.getenv("MCP_SERVER_PORT", "8765")),
        )

        config.huggingface = HuggingFaceConfig(
            home=os.getenv("HF_HOME", "/app/models"),
            hub_cache=os.getenv("HF_HUB_CACHE", "/app/models/hub"),
            datasets_cache=os.getenv("HF_DATASETS_CACHE", "/app/models/datasets"),
            force_cpu=os.getenv("HF_FORCE_CPU", "false").lower() == "true",
        )

        config.crawler = CrawlerConfig(
            github_token=os.getenv("GITHUB_TOKEN"),
            enable_daily_crawl=os.getenv("ENABLE_DAILY_CRAWL", "true").lower() == "true",
            crawl_schedule=os.getenv("CRAWL_SCHEDULE", "06:00"),
            max_papers_per_day=int(os.getenv("MAX_PAPERS_PER_DAY", "10")),
        )

        config.provider = {
            "claude": ProviderConfig(
                name="claude",
                api_key_env="ANTHROPIC_API_KEY",
                default_model=os.getenv("CLAUDE_DEFAULT_MODEL", "claude-opus-4-8"),
            ),
            "openai": ProviderConfig(
                name="openai",
                api_key_env="OPENAI_API_KEY",
                default_model=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o"),
            ),
            "azure": ProviderConfig(
                name="azure",
                api_key_env="AZURE_OPENAI_API_KEY",
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                default_model=os.getenv("AZURE_DEFAULT_MODEL", "gpt-4o"),
            ),
            "gcp": ProviderConfig(
                name="gcp",
                api_key_env="N/A",
                project_id=os.getenv("GCP_PROJECT_ID"),
                location=os.getenv("GCP_LOCATION", "us-central1"),
                default_model=os.getenv("GCP_DEFAULT_MODEL", "gemini-1.5-pro"),
            ),
            "ollama": ProviderConfig(
                name="ollama",
                api_key_env="N/A",
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                default_model=os.getenv("OLLAMA_DEFAULT_MODEL", "llama3"),
            ),
            "vllm": ProviderConfig(
                name="vllm",
                api_key_env="VLLM_API_KEY",
                base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
                default_model=os.getenv("VLLM_DEFAULT_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct"),
            ),
        }

        self._config = config
        self._validate(raise_on_error=raise_on_error)
        return config

    def _validate(self, raise_on_error: bool):
        """Validate configuration and print warnings or raise errors."""

        if not self._config:
            return

        available_providers = [name for name, p in self._config.provider.items() if p.available]
        warnings = []
        errors = []

        if not available_providers:
            msg = "No LLM provider configured"
            fix = (
                "Set at least one provider API key in .env:\n"
                "  - ANTHROPIC_API_KEY (recommended)\n"
                "  - OPENAI_API_KEY\n"
                "  - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT\n"
                "  - GCP_PROJECT_ID\n"
                "Or use local providers:\n"
                "  - OLLAMA_BASE_URL (requires Ollama running)\n"
                "  - VLLM_BASE_URL (requires vLLM running)\n"
                "\nCopy .env.example to .env and fill in your keys."
            )
            errors.append((msg, fix))
        elif "claude" not in available_providers:
            msg = "Claude API key not set"
            fix = "Fallback providers: " + ", ".join(available_providers)
            warnings.append((msg, fix))

        for name, provider in self._config.provider.items():
            if name == "claude" and provider.available and not provider.api_key.startswith("sk-ant-"):
                msg = f"ANTHROPIC_API_KEY format looks incorrect"
                fix = "API key should start with 'sk-ant-'"
                warnings.append((msg, fix))

            if name == "openai" and provider.available and not provider.api_key.startswith("sk-"):
                msg = f"OPENAI_API_KEY format looks incorrect"
                fix = "API key should start with 'sk-'"
                warnings.append((msg, fix))

            if name == "azure" and provider.available and not provider.endpoint:
                msg = "Azure configured but AZURE_OPENAI_ENDPOINT not set"
                fix = "Set AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/ in .env"
                warnings.append((msg, fix))

            if name == "gcp" and provider.available and not provider.project_id:
                msg = "GCP selected but GCP_PROJECT_ID not set"
                fix = "Set GCP_PROJECT_ID=your-project-id in .env"
                warnings.append((msg, fix))

        db_path = Path(self._config.database_path)
        if not db_path.parent.exists():
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                msg = f"Cannot create database directory: {db_path.parent}"
                fix = "Check permissions or set DATABASE_PATH to a writable location"
                errors.append((msg, fix))

        workspace_path = Path(self._config.tools.workspace_path)
        if not workspace_path.exists():
            try:
                workspace_path.mkdir(parents=True, exist_ok=True)
            except OSError:
                msg = f"Cannot create workspace directory: {workspace_path}"
                fix = "Check permissions or set WORKSPACE_PATH to a writable location"
                errors.append((msg, fix))

        if self._config.benchmark.composite_score_threshold < 0 or self._config.benchmark.composite_score_threshold > 1:
            msg = "COMPOSITE_SCORE_THRESHOLD must be between 0 and 1"
            fix = "Set COMPOSITE_SCORE_THRESHOLD=0.40 in .env"
            errors.append((msg, fix))

        if self._config.tools.code_exec_timeout < 1 or self._config.tools.code_exec_timeout > 300:
            msg = "CODE_EXEC_TIMEOUT must be between 1 and 300 seconds"
            fix = "Set CODE_EXEC_TIMEOUT=10 in .env"
            errors.append((msg, fix))

        for msg, fix in warnings:
            print(f"\n⚠️  WARNING: {msg}", file=sys.stderr)

        if errors and raise_on_error:
            for msg, fix in errors:
                raise ConfigurationError(msg, fix)
        elif errors:
            for msg, fix in errors:
                print(f"\n❌ ERROR: {msg}", file=sys.stderr)
                print(f"   Fix: {fix}", file=sys.stderr)
            print("\n⚠️  Continuing with default configuration. Some features may not work.", file=sys.stderr)

    @property
    def config(self) -> AppConfig:
        """Get current configuration.

        Raises:
            RuntimeError: If load() has not been called.
        """
        if not self._load_called:
            raise RuntimeError("ConfigManager.load() must be called before accessing config")
        if self._config is None:
            raise RuntimeError("Configuration not loaded")
        return self._config

    def get_available_providers(self) -> list[str]:
        """Get list of configured and available providers."""
        if not self._config:
            return []
        return [name for name, p in self._config.provider.items() if p.available]

    def get_provider_config(self, name: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider."""
        if not self._config:
            return None
        return self._config.provider.get(name)

    def is_privacy_mode(self) -> bool:
        """Check if running in privacy mode (no external API calls)."""
        if not self._config:
            return False
        return self._config.privacy_mode

    def get_fallback_chain(self, preferred: str) -> list[str]:
        """Get fallback provider chain starting with preferred provider.

        In privacy mode, only local providers (ollama, vllm) are included.
        """
        if not self._config:
            return []

        available = self.get_available_providers()

        if self._config.privacy_mode:
            local_only = [p for p in available if p in {"ollama", "vllm"}]
            if preferred in local_only:
                return [preferred] + [p for p in local_only if p != preferred]
            return local_only

        if preferred not in available:
            return available

        return [preferred] + [p for p in available if p != preferred]


_global_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global ConfigManager singleton."""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def load_config(*, raise_on_error: bool = False) -> AppConfig:
    """Load and return configuration.

    Convenience function that loads config via global ConfigManager.

    Args:
        raise_on_error: If True, raise ConfigurationError for missing required config.

    Returns:
        AppConfig instance
    """
    return get_config_manager().load(raise_on_error=raise_on_error)


def get_config() -> AppConfig:
    """Get current configuration.

    Raises:
        RuntimeError: If load_config() has not been called.
    """
    return get_config_manager().config
