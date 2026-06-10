"""provider_adapter.py — Unified LLM completion across 6 providers with auto-fallback."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

# Cost per 1K tokens (input, output) USD
COST_PER_1K: dict[str, tuple[float, float]] = {
    "claude-opus-4-8":       (0.015,  0.075),
    "claude-sonnet-4-6":     (0.003,  0.015),
    "gpt-4o":                (0.005,  0.015),
    "gpt-4o-mini":           (0.00015, 0.0006),
    "azure/gpt-4o":          (0.005,  0.015),
    "gemini-1.5-pro":        (0.00125, 0.005),
    "llama3:8b":             (0.0,    0.0),
    "mistral:7b":            (0.0,    0.0),
}

FALLBACK_CHAIN = ["claude", "openai", "azure", "gcp", "ollama"]


@dataclass
class CompletionResult:
    text: str
    provider_used: str
    model_used: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    tool_calls: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "tool_calls": self.tool_calls,
        }


class AllProvidersExhausted(Exception):
    pass


# ── Base adapter ──────────────────────────────────────────────────────────────

class BaseProviderAdapter:
    provider_name: str = "base"
    default_model: str = ""

    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        system: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> CompletionResult:
        raise NotImplementedError

    async def stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        system: Optional[str] = None,
    ) -> AsyncIterator[str]:
        raise NotImplementedError

    def _compute_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = COST_PER_1K.get(model, (0.0, 0.0))
        return (prompt_tokens / 1000) * rates[0] + (completion_tokens / 1000) * rates[1]


# ── Claude adapter ────────────────────────────────────────────────────────────

class ClaudeAdapter(BaseProviderAdapter):
    provider_name = "claude"
    default_model = "claude-opus-4-8"

    async def complete(self, messages, model=None, system=None, tools=None, max_tokens=2048, temperature=0.7) -> CompletionResult:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        client = anthropic.AsyncAnthropic(api_key=api_key)
        mdl = model or self.default_model
        t0 = time.time()

        kwargs: dict[str, Any] = {
            "model": mdl,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = _to_claude_tools(tools)

        response = await client.messages.create(**kwargs)
        elapsed = (time.time() - t0) * 1000

        text = ""
        tool_calls = []
        for block in response.content:
            if hasattr(block, "text"):
                text = block.text
            elif hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })

        pt = response.usage.input_tokens
        ct = response.usage.output_tokens
        return CompletionResult(
            text=text,
            provider_used="claude",
            model_used=mdl,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_ms=elapsed,
            cost_usd=self._compute_cost(mdl, pt, ct),
            tool_calls=tool_calls,
        )

    async def stream(self, messages, model=None, system=None) -> AsyncIterator[str]:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed")
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        mdl = model or self.default_model
        kwargs: dict[str, Any] = {"model": mdl, "max_tokens": 2048, "messages": messages}
        if system:
            kwargs["system"] = system
        async with client.messages.stream(**kwargs) as stream_ctx:
            async for text in stream_ctx.text_stream:
                yield text


# ── OpenAI adapter ────────────────────────────────────────────────────────────

class OpenAIAdapter(BaseProviderAdapter):
    provider_name = "openai"
    default_model = "gpt-4o"

    def __init__(self, base_url: Optional[str] = None, api_key_env: str = "OPENAI_API_KEY"):
        self.base_url = base_url
        self.api_key_env = api_key_env

    async def complete(self, messages, model=None, system=None, tools=None, max_tokens=2048, temperature=0.7) -> CompletionResult:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeError("openai package not installed")

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"{self.api_key_env} not set")

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = AsyncOpenAI(**client_kwargs)
        mdl = model or self.default_model

        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}] + msgs

        t0 = time.time()
        kwargs: dict[str, Any] = {
            "model": mdl,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = _to_openai_tools(tools)
            kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**kwargs)
        elapsed = (time.time() - t0) * 1000

        msg = response.choices[0].message
        text = msg.content or ""
        tool_calls = []
        if msg.tool_calls:
            import json as _json
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": _json.loads(tc.function.arguments or "{}"),
                })

        pt = response.usage.prompt_tokens if response.usage else 0
        ct = response.usage.completion_tokens if response.usage else 0
        return CompletionResult(
            text=text,
            provider_used=self.provider_name,
            model_used=mdl,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_ms=elapsed,
            cost_usd=self._compute_cost(mdl, pt, ct),
            tool_calls=tool_calls,
        )

    async def stream(self, messages, model=None, system=None) -> AsyncIterator[str]:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeError("openai package not installed")
        client = AsyncOpenAI(api_key=os.getenv(self.api_key_env, ""))
        mdl = model or self.default_model
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}] + msgs
        stream = await client.chat.completions.create(model=mdl, messages=msgs, stream=True)
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# ── Azure adapter ─────────────────────────────────────────────────────────────

class AzureAdapter(OpenAIAdapter):
    provider_name = "azure"
    default_model = "gpt-4o"

    def __init__(self):
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource.openai.azure.com/")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        super().__init__(
            base_url=f"{endpoint.rstrip('/')}/openai/deployments/",
            api_key_env="AZURE_OPENAI_API_KEY",
        )
        self.api_version = api_version


# ── GCP Vertex adapter ────────────────────────────────────────────────────────

class GCPAdapter(BaseProviderAdapter):
    provider_name = "gcp"
    default_model = "gemini-1.5-pro"

    async def complete(self, messages, model=None, system=None, tools=None, max_tokens=2048, temperature=0.7) -> CompletionResult:
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel, Content, Part
        except ImportError:
            raise RuntimeError("google-cloud-aiplatform package not installed")

        project = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GCP_LOCATION", "us-central1")
        if not project:
            raise RuntimeError("GCP_PROJECT_ID not set")

        vertexai.init(project=project, location=location)
        mdl = model or self.default_model
        t0 = time.time()

        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append(Content(role=role, parts=[Part.from_text(m["content"])]))

        gen_model = GenerativeModel(mdl, system_instruction=system or "")
        response = gen_model.generate_content(contents)
        elapsed = (time.time() - t0) * 1000
        text = response.text if hasattr(response, "text") else ""

        return CompletionResult(
            text=text,
            provider_used="gcp",
            model_used=mdl,
            latency_ms=elapsed,
            cost_usd=self._compute_cost(mdl, 0, 0),
        )

    async def stream(self, messages, model=None, system=None) -> AsyncIterator[str]:
        result = await self.complete(messages, model=model, system=system)
        yield result.text


# ── Ollama adapter ────────────────────────────────────────────────────────────

class OllamaAdapter(BaseProviderAdapter):
    provider_name = "ollama"
    default_model = "llama3"

    async def complete(self, messages, model=None, system=None, tools=None, max_tokens=2048, temperature=0.7) -> CompletionResult:
        try:
            import aiohttp
        except ImportError:
            raise RuntimeError("aiohttp package not installed")

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        mdl = model or self.default_model
        t0 = time.time()

        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}] + msgs

        payload = {"model": mdl, "messages": msgs, "stream": False}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}/api/chat", json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama returned {resp.status}")
                data = await resp.json()

        elapsed = (time.time() - t0) * 1000
        text = data.get("message", {}).get("content", "")
        return CompletionResult(
            text=text,
            provider_used="ollama",
            model_used=mdl,
            latency_ms=elapsed,
        )

    async def stream(self, messages, model=None, system=None) -> AsyncIterator[str]:
        try:
            import aiohttp
        except ImportError:
            raise RuntimeError("aiohttp not installed")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        mdl = model or self.default_model
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}] + msgs
        payload = {"model": mdl, "messages": msgs, "stream": True}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}/api/chat", json=payload) as resp:
                async for line in resp.content:
                    import json as _json
                    try:
                        data = _json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                    except Exception:
                        pass


# ── vLLM adapter (OpenAI-compatible) ─────────────────────────────────────────

class VLLMAdapter(OpenAIAdapter):
    provider_name = "vllm"
    default_model = "meta-llama/Meta-Llama-3-8B-Instruct"

    def __init__(self):
        base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        super().__init__(base_url=base_url, api_key_env="VLLM_API_KEY")


# ── Provider router ───────────────────────────────────────────────────────────

_ADAPTERS: dict[str, BaseProviderAdapter] = {
    "claude": ClaudeAdapter(),
    "openai": OpenAIAdapter(),
    "azure":  AzureAdapter(),
    "gcp":    GCPAdapter(),
    "ollama": OllamaAdapter(),
    "vllm":   VLLMAdapter(),
}


class ProviderAdapter:
    """Routes requests with auto-fallback. Thread-safe singleton."""

    async def complete(
        self,
        provider: str,
        messages: list[dict],
        model: Optional[str] = None,
        system: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        chain = _build_fallback_chain(provider)
        last_exc: Optional[Exception] = None
        for prov in chain:
            adapter = _ADAPTERS.get(prov)
            if adapter is None:
                continue
            try:
                result = await adapter.complete(
                    messages=messages,
                    model=model,
                    system=system,
                    tools=tools,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return result.to_dict()
            except Exception as exc:
                last_exc = exc
                continue
        raise AllProvidersExhausted(f"All providers failed. Last error: {last_exc}")

    async def stream(
        self,
        provider: str,
        messages: list[dict],
        model: Optional[str] = None,
        system: Optional[str] = None,
    ) -> AsyncIterator[str]:
        chain = _build_fallback_chain(provider)
        for prov in chain:
            adapter = _ADAPTERS.get(prov)
            if adapter is None:
                continue
            try:
                async for chunk in adapter.stream(messages=messages, model=model, system=system):
                    yield chunk
                return
            except Exception:
                continue


def _build_fallback_chain(preferred: str) -> list[str]:
    chain = [preferred]
    for p in FALLBACK_CHAIN:
        if p != preferred:
            chain.append(p)
    return chain


def _to_claude_tools(tools: list[dict]) -> list[dict]:
    result = []
    for t in tools:
        result.append({
            "name": t.get("name", ""),
            "description": t.get("description", ""),
            "input_schema": t.get("parameters", {"type": "object", "properties": {}}),
        })
    return result


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    result = []
    for t in tools:
        result.append({
            "type": "function",
            "function": {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {"type": "object", "properties": {}}),
            },
        })
    return result
