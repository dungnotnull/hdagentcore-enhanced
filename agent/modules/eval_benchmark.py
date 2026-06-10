"""eval_benchmark.py — 5-metric agent evaluation benchmark scorer."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BenchmarkResult:
    run_id: str
    pattern: str
    provider: str
    task_success: float        # 0..1 (LLM-judged)
    task_success_confidence: float  # 0..1
    token_efficiency: float    # 0..1
    error_recovery: float      # 0..1
    latency_ms: float
    quality_score: float       # 0..5
    composite_score: float     # 0..1
    eval_cost_usd: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "pattern": self.pattern,
            "provider": self.provider,
            "task_success": round(self.task_success, 4),
            "task_success_confidence": round(self.task_success_confidence, 4),
            "token_efficiency": round(self.token_efficiency, 4),
            "error_recovery": round(self.error_recovery, 4),
            "latency_ms": round(self.latency_ms, 1),
            "quality_score": round(self.quality_score, 2),
            "composite_score": round(self.composite_score, 4),
            "eval_cost_usd": round(self.eval_cost_usd, 6),
            "notes": self.notes,
        }


EVAL_SYSTEM_PROMPT = "You are a rigorous evaluator of AI agent outputs. Return ONLY valid JSON."

EVAL_PROMPT_TEMPLATE = """Evaluate this agent's task completion. Return ONLY valid JSON, no extra text.

Original task: {task_description}
Agent output: {agent_output}
Tool calls made: {tool_calls_summary}

Return this exact JSON structure:
{{
  "task_success": <float 0.0-1.0>,
  "confidence": <float 0.0-1.0>,
  "reasoning": "<brief explanation under 100 words>",
  "quality_score": <integer 0-5>,
  "quality_reasoning": "<brief explanation under 80 words>"
}}

Task success rubric:
1.0 = fully complete, all requirements met
0.7 = mostly complete, minor gaps or inaccuracies
0.4 = partial, key requirements missing
0.1 = attempted but failed to produce useful output
0.0 = no relevant output or completely wrong

Quality rubric:
5 = expert-level, accurate, well-structured, comprehensive
4 = good, mostly accurate, clear structure
3 = adequate, basic information present
2 = poor, significant inaccuracies or gaps
1 = very poor
0 = no output"""

# Latency normalization: 0ms=1.0, 30000ms=0.0 (linear)
LATENCY_MAX_MS = 30_000.0


class EvalBenchmark:
    """Score agent runs on 5 metrics. Uses a cheap judge model to minimize eval cost."""

    def __init__(self, judge_model: str = "claude-sonnet-4-6"):
        self.judge_model = judge_model

    async def score(
        self,
        run_id: str,
        pattern: str,
        provider: str,
        task_description: str,
        agent_output: str,
        tool_calls: list[dict],
        prompt_tokens: int,
        completion_tokens: int,
        errors_total: int,
        errors_recovered: int,
        elapsed_ms: float,
    ) -> dict:

        # Metric 1 + 5: Task success + quality (LLM-judged, async)
        llm_scores, eval_cost = await self._llm_judge(task_description, agent_output, tool_calls)
        task_success = llm_scores.get("task_success", 0.5)
        task_confidence = llm_scores.get("confidence", 0.5)
        quality_score = float(llm_scores.get("quality_score", 2))

        # Metric 2: Token efficiency
        token_efficiency = self._compute_token_efficiency(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            agent_output=agent_output,
        )

        # Metric 3: Error recovery
        error_recovery = self._compute_error_recovery(errors_total, errors_recovered)

        # Metric 4: Latency score (normalized 0..1, higher=faster)
        latency_score = max(0.0, 1.0 - (elapsed_ms / LATENCY_MAX_MS))

        # Composite: weighted average
        composite = (
            0.30 * task_success
            + 0.20 * token_efficiency
            + 0.20 * error_recovery
            + 0.15 * latency_score
            + 0.15 * (quality_score / 5.0)
        )

        notes = []
        if composite < 0.40:
            notes.append("WARNING: composite < 0.40 threshold")
        if quality_score < 2:
            notes.append("Low quality output — consider a stronger model")
        if token_efficiency < 0.20:
            notes.append("Low token efficiency — output may be too short or tokens wasted")

        result = BenchmarkResult(
            run_id=run_id,
            pattern=pattern,
            provider=provider,
            task_success=task_success,
            task_success_confidence=task_confidence,
            token_efficiency=token_efficiency,
            error_recovery=error_recovery,
            latency_ms=elapsed_ms,
            quality_score=quality_score,
            composite_score=composite,
            eval_cost_usd=eval_cost,
            notes=" | ".join(notes),
        )
        return result.to_dict()

    async def _llm_judge(
        self,
        task_description: str,
        agent_output: str,
        tool_calls: list[dict],
    ) -> tuple[dict, float]:
        tool_summary = _format_tool_calls_summary(tool_calls)
        prompt = EVAL_PROMPT_TEMPLATE.format(
            task_description=task_description[:500],
            agent_output=agent_output[:1500],
            tool_calls_summary=tool_summary,
        )

        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return _fallback_scores(agent_output), 0.0

            client = anthropic.AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model=self.judge_model,
                max_tokens=300,
                system=EVAL_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            import json
            text = response.content[0].text if response.content else "{}"
            scores = json.loads(text)
            pt = response.usage.input_tokens
            ct = response.usage.output_tokens
            cost = (pt / 1000) * 0.003 + (ct / 1000) * 0.015
            return scores, cost
        except Exception:
            return _fallback_scores(agent_output), 0.0

    @staticmethod
    def _compute_token_efficiency(prompt_tokens: int, completion_tokens: int, agent_output: str) -> float:
        if prompt_tokens == 0 and completion_tokens == 0:
            return 0.5
        total = prompt_tokens + completion_tokens
        if total == 0:
            return 0.5
        # Useful tokens = completion tokens that produced actual content
        output_len = len(agent_output.split())
        useful_tokens = min(completion_tokens, max(1, output_len * 1.3))
        return min(1.0, useful_tokens / total)

    @staticmethod
    def _compute_error_recovery(errors_total: int, errors_recovered: int) -> float:
        if errors_total == 0:
            return 1.0
        return min(1.0, errors_recovered / errors_total)

    async def compare_providers(
        self,
        results: list[dict],
    ) -> str:
        """Generate a Markdown comparison table from multiple benchmark results."""
        if not results:
            return "_No benchmark results to compare._"
        lines = [
            "## Provider Benchmark Comparison",
            "| Provider | Composite | Task✓ | Tokens | Errors | Quality | Latency(ms) |",
            "|----------|-----------|-------|--------|--------|---------|------------|",
        ]
        for r in sorted(results, key=lambda x: x.get("composite_score", 0), reverse=True):
            lines.append(
                f"| {r.get('provider', '?')} "
                f"| {r.get('composite_score', 0):.3f} "
                f"| {r.get('task_success', 0):.2f} "
                f"| {r.get('token_efficiency', 0):.2f} "
                f"| {r.get('error_recovery', 0):.2f} "
                f"| {r.get('quality_score', 0):.1f}/5 "
                f"| {r.get('latency_ms', 0):.0f} |"
            )
        return "\n".join(lines)


def _fallback_scores(agent_output: str) -> dict:
    """Heuristic scoring when LLM judge unavailable."""
    length = len(agent_output.strip())
    if length == 0:
        return {"task_success": 0.0, "confidence": 0.3, "quality_score": 0}
    if length < 50:
        return {"task_success": 0.3, "confidence": 0.3, "quality_score": 1}
    if length < 200:
        return {"task_success": 0.6, "confidence": 0.4, "quality_score": 2}
    return {"task_success": 0.7, "confidence": 0.4, "quality_score": 3}


def _format_tool_calls_summary(tool_calls: list[dict]) -> str:
    if not tool_calls:
        return "No tool calls."
    lines = []
    for tc in tool_calls[:10]:
        status = "SUCCESS" if tc.get("success") else "ERROR"
        preview = tc.get("result_preview", tc.get("error", ""))[:80]
        lines.append(f"- {tc['tool']} [{status}]: {preview}")
    return "\n".join(lines)
