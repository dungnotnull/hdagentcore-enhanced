"""llm_client.py — Unified LLM client (Claude / OpenAI / Ollama) for agentcore-enhanced."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any, AsyncIterator, Optional

COST_PER_1K: dict[str, tuple[float, float]] = {
    "claude-opus-4-8":    (0.015,  0.075),
    "claude-sonnet-4-6":  (0.003,  0.015),
    "claude-haiku-4-5-20251001": (0.001, 0.005),
    "gpt-4o":             (0.005,  0.015),
    "gpt-4o-mini":        (0.00015, 0.0006),
    "llama3":             (0.0,    0.0),
    "mistral:7b":         (0.0,    0.0),
}

PROVIDER_PRIORITY = ["claude", "openai", "ollama"]


class UnifiedLLMClient:
    """Claude-primary, OpenAI-fallback, Ollama-offline LLM client."""

    def __init__(self):
        self._mem = None

    def _get_mem(self):
        if self._mem is None:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from agent.memory.memory_manager import MemoryManager
            self._mem = MemoryManager()
        return self._mem

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        provider: str = "claude",
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        privacy_mode = os.getenv("PRIVACY_MODE", "").lower() == "true"
        if privacy_mode:
            provider = "ollama"

        chain = _build_chain(provider)
        last_exc: Optional[Exception] = None

        for prov in chain:
            try:
                result, tokens_in, tokens_out = await self._call_with_retry(
                    prov, prompt, system=system, model=model,
                    max_tokens=max_tokens, temperature=temperature, json_mode=json_mode,
                )
                cost = _calc_cost(model or _default_model(prov), tokens_in, tokens_out)
                self._get_mem().log_llm_cost(prov, "complete", tokens_in + tokens_out, cost)
                return result
            except Exception as exc:
                last_exc = exc
                continue

        raise RuntimeError(f"All providers failed. Last: {last_exc}")

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        provider: str = "claude",
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        chain = _build_chain(provider)
        for prov in chain:
            try:
                async for chunk in self._stream_provider(prov, prompt, system=system, model=model):
                    yield chunk
                return
            except Exception:
                continue

    def complete_sync(self, prompt: str, **kwargs) -> str:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.complete(prompt, **kwargs))
        finally:
            loop.close()

    async def _call_with_retry(
        self,
        provider: str,
        prompt: str,
        system: Optional[str],
        model: Optional[str],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
        retries: int = 3,
    ) -> tuple[str, int, int]:
        delays = [1, 2, 4]
        last_exc: Optional[Exception] = None
        for attempt in range(retries):
            try:
                return await self._call_provider(
                    provider, prompt, system=system, model=model,
                    max_tokens=max_tokens, temperature=temperature, json_mode=json_mode,
                )
            except Exception as exc:
                last_exc = exc
                if attempt < retries - 1:
                    await asyncio.sleep(delays[attempt])
        raise last_exc  # type: ignore

    async def _call_provider(
        self,
        provider: str,
        prompt: str,
        system: Optional[str],
        model: Optional[str],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> tuple[str, int, int]:
        if provider == "claude":
            return await self._call_claude(prompt, system, model, max_tokens, temperature)
        elif provider == "openai":
            return await self._call_openai(prompt, system, model, max_tokens, temperature, json_mode)
        elif provider == "ollama":
            return await self._call_ollama(prompt, system, model, max_tokens)
        raise ValueError(f"Unknown provider: {provider}")

    async def _call_claude(self, prompt, system, model, max_tokens, temperature):
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        client = anthropic.AsyncAnthropic(api_key=api_key)
        mdl = model or "claude-opus-4-8"
        kwargs: dict[str, Any] = {
            "model": mdl,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        resp = await client.messages.create(**kwargs)
        text = resp.content[0].text if resp.content else ""
        return text, resp.usage.input_tokens, resp.usage.output_tokens

    async def _call_openai(self, prompt, system, model, max_tokens, temperature, json_mode):
        from openai import AsyncOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        client = AsyncOpenAI(api_key=api_key)
        mdl = model or "gpt-4o"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs: dict[str, Any] = {
            "model": mdl,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content or ""
        pt = resp.usage.prompt_tokens if resp.usage else 0
        ct = resp.usage.completion_tokens if resp.usage else 0
        return text, pt, ct

    async def _call_ollama(self, prompt, system, model, max_tokens):
        import aiohttp
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        mdl = model or "llama3"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": mdl, "messages": messages, "stream": False}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/chat", json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama {resp.status}")
                data = await resp.json()
        text = data.get("message", {}).get("content", "")
        return text, 0, 0

    async def _stream_provider(self, provider, prompt, system, model) -> AsyncIterator[str]:
        if provider == "claude":
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
            mdl = model or "claude-opus-4-8"
            kwargs: dict[str, Any] = {
                "model": mdl, "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            async with client.messages.stream(**kwargs) as stream_ctx:
                async for text in stream_ctx.text_stream:
                    yield text
        elif provider == "openai":
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
            msgs = [{"role": "user", "content": prompt}]
            if system:
                msgs.insert(0, {"role": "system", "content": system})
            stream = await client.chat.completions.create(
                model=model or "gpt-4o", messages=msgs, stream=True
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        else:
            text, _, _ = await self._call_ollama(prompt, system, model, 2048)
            yield text


def _build_chain(preferred: str) -> list[str]:
    chain = [preferred]
    for p in PROVIDER_PRIORITY:
        if p != preferred:
            chain.append(p)
    return chain


def _default_model(provider: str) -> str:
    return {"claude": "claude-opus-4-8", "openai": "gpt-4o", "ollama": "llama3"}.get(provider, "unknown")


def _calc_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    rates = COST_PER_1K.get(model, (0.0, 0.0))
    return (tokens_in / 1000) * rates[0] + (tokens_out / 1000) * rates[1]
