"""agentcore-enhanced — Core orchestrator (decision loop)."""

from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).parent.parent


class AgentCoreOrchestrator:
    """Lazy-init orchestrator for all agentcore-enhanced modules."""

    def __init__(self):
        self._provider_adapter = None
        self._mcp_manager = None
        self._eval_benchmark = None
        self._pattern_library = None
        self._memory: Optional[Any] = None
        self._llm_client = None
        self._scheduler = None
        self._prom_counters = _init_prometheus()

    # ── Lazy module accessors ─────────────────────────────────────────────────

    def _get_provider_adapter(self):
        if self._provider_adapter is None:
            from agent.modules.provider_adapter import ProviderAdapter
            self._provider_adapter = ProviderAdapter()
        return self._provider_adapter

    def _get_mcp_manager(self):
        if self._mcp_manager is None:
            from agent.modules.mcp_manager import MCPManager
            self._mcp_manager = MCPManager()
        return self._mcp_manager

    def _get_eval_benchmark(self):
        if self._eval_benchmark is None:
            from agent.modules.eval_benchmark import EvalBenchmark
            self._eval_benchmark = EvalBenchmark()
        return self._eval_benchmark

    def _get_pattern_library(self):
        if self._pattern_library is None:
            from agent.modules.pattern_library import PatternLibrary
            self._pattern_library = PatternLibrary()
        return self._pattern_library

    def _get_memory(self):
        if self._memory is None:
            from agent.memory.memory_manager import MemoryManager
            self._memory = MemoryManager()
        return self._memory

    def _get_llm(self):
        if self._llm_client is None:
            from tools.llm_client import UnifiedLLMClient
            self._llm_client = UnifiedLLMClient()
        return self._llm_client

    # ── Core run flow ─────────────────────────────────────────────────────────

    async def run_pattern(
        self,
        pattern_query: str,
        task: str,
        provider: str = "claude",
        max_steps: int = 10,
    ) -> dict:
        run_id = str(uuid.uuid4())[:8]
        t_start = time.time()
        mem = self._get_memory()
        pl = self._get_pattern_library()
        pa = self._get_provider_adapter()
        mcp = self._get_mcp_manager()
        ev = self._get_eval_benchmark()

        # Step 1: load pattern
        patterns = await pl.search(query=pattern_query, top_k=1)
        if not patterns:
            raise ValueError(f"No pattern found matching '{pattern_query}'")
        pattern_cfg = patterns[0]
        if pattern_cfg.get("similarity", 1.0) < 0.65:
            candidates = [p["name"] for p in patterns[:3]]
            raise ValueError(
                f"Pattern similarity {pattern_cfg.get('similarity', 0):.2f} < 0.65. "
                f"Closest: {candidates}"
            )

        # Step 2: register tools
        tools_required = pattern_cfg.get("tools_required", [])
        tool_definitions = mcp.get_tool_definitions(tools_required)

        # Step 3: build initial messages
        system_prompt = pattern_cfg.get("system_prompt", "You are a helpful assistant.")
        prompt_template = pattern_cfg.get("prompt_template", "{task}")
        user_message = prompt_template.replace("{task}", task).replace("{tools_list}", _format_tools(tool_definitions))

        messages = [{"role": "user", "content": user_message}]

        # Step 4: execution loop
        tool_calls_log = []
        errors_total = 0
        errors_recovered = 0
        step = 0

        while step < max_steps:
            result = await pa.complete(
                provider=provider,
                messages=messages,
                system=system_prompt,
                tools=tool_definitions if tool_definitions else None,
            )

            assistant_content = result.get("text", "")
            raw_tool_calls = result.get("tool_calls", [])

            if not raw_tool_calls:
                break

            messages.append({"role": "assistant", "content": assistant_content or "", "tool_calls": raw_tool_calls})

            tool_results = []
            for tc in raw_tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("arguments", {})
                try:
                    tr = await mcp.call_tool(tool_name, tool_args)
                    tool_calls_log.append({"tool": tool_name, "success": True, "result_preview": str(tr)[:100]})
                    tool_results.append({"tool_call_id": tc.get("id", ""), "content": str(tr)})
                except Exception as exc:
                    errors_total += 1
                    error_msg = f"Tool error: {exc}"
                    tool_calls_log.append({"tool": tool_name, "success": False, "error": str(exc)})
                    tool_results.append({"tool_call_id": tc.get("id", ""), "content": error_msg})
                    errors_recovered += 1  # agent gets to see error and can recover

            messages.append({"role": "tool", "tool_results": tool_results})
            step += 1

        elapsed_ms = (time.time() - t_start) * 1000
        final_answer = _extract_final_answer(messages)
        total_tokens = result.get("prompt_tokens", 0) + result.get("completion_tokens", 0)
        cost_usd = result.get("cost_usd", 0.0)
        provider_used = result.get("provider_used", provider)

        # Step 5: evaluate
        benchmark = await ev.score(
            run_id=run_id,
            pattern=pattern_cfg["name"],
            provider=provider_used,
            task_description=task,
            agent_output=final_answer,
            tool_calls=tool_calls_log,
            prompt_tokens=result.get("prompt_tokens", 0),
            completion_tokens=result.get("completion_tokens", 0),
            errors_total=errors_total,
            errors_recovered=errors_recovered,
            elapsed_ms=elapsed_ms,
        )

        # Step 6: persist
        mem.save_run({
            "run_id": run_id,
            "pattern": pattern_cfg["name"],
            "provider": provider_used,
            "task": task,
            "final_answer": final_answer,
            "tool_calls_count": len(tool_calls_log),
            "cost_usd": cost_usd,
            "latency_ms": elapsed_ms,
            "composite_score": benchmark.get("composite_score", 0),
        })
        mem.save_benchmark(benchmark)
        mem.log_llm_cost(provider_used, "run_pattern", total_tokens, cost_usd)

        # Prometheus
        self._prom_counters["runs_total"] += 1

        report = _render_run_report(
            run_id=run_id,
            pattern=pattern_cfg["name"],
            provider=provider_used,
            task=task,
            final_answer=final_answer,
            tool_calls=tool_calls_log,
            benchmark=benchmark,
            cost_usd=cost_usd,
            elapsed_ms=elapsed_ms,
        )

        return {
            "run_id": run_id,
            "pattern_used": pattern_cfg["name"],
            "provider_used": provider_used,
            "final_answer": final_answer,
            "tool_calls_count": len(tool_calls_log),
            "benchmark": benchmark,
            "cost_usd": cost_usd,
            "latency_ms": elapsed_ms,
            "report_markdown": report,
        }

    # ── Benchmark all providers ───────────────────────────────────────────────

    async def benchmark_all_providers(
        self,
        pattern_query: str,
        task: str,
        providers: list[str],
        max_steps: int = 5,
    ) -> dict:
        tasks_coro = [
            self.run_pattern(pattern_query=pattern_query, task=task, provider=p, max_steps=max_steps)
            for p in providers
        ]
        results = await asyncio.gather(*tasks_coro, return_exceptions=True)

        valid_results = []
        for p, r in zip(providers, results):
            if isinstance(r, Exception):
                valid_results.append({"provider": p, "error": str(r), "composite_score": 0.0})
            else:
                valid_results.append({
                    "provider": r["provider_used"],
                    "composite_score": r["benchmark"].get("composite_score", 0),
                    "cost_usd": r["cost_usd"],
                    "latency_ms": r["latency_ms"],
                    "task_success": r["benchmark"].get("task_success", 0),
                    "quality_score": r["benchmark"].get("quality_score", 0),
                })

        best = max(valid_results, key=lambda x: x.get("composite_score", 0))
        comparison = _render_comparison_report(
            pattern_query=pattern_query,
            task=task,
            results=valid_results,
            best_provider=best["provider"],
        )

        return {
            "pattern": pattern_query,
            "task": task,
            "results": valid_results,
            "best_provider": best["provider"],
            "comparison_markdown": comparison,
        }

    # ── Pattern search ────────────────────────────────────────────────────────

    async def pattern_search(
        self,
        query: str,
        provider_filter: Optional[str] = None,
        top_k: int = 3,
    ) -> list[dict]:
        pl = self._get_pattern_library()
        results = await pl.search(query=query, top_k=top_k, provider_filter=provider_filter)
        return results

    async def list_all_patterns(self) -> list[dict]:
        pl = self._get_pattern_library()
        return pl.list_all()

    # ── Knowledge update ──────────────────────────────────────────────────────

    async def update_knowledge(self) -> dict:
        from tools.knowledge_updater import KnowledgeUpdater
        ku = KnowledgeUpdater()
        return await ku.run_daily_update()

    # ── Cost report ───────────────────────────────────────────────────────────

    async def get_cost_report(self, days: int = 30) -> dict:
        mem = self._get_memory()
        return mem.get_cost_summary(days=days)

    # ── Prometheus metrics ────────────────────────────────────────────────────

    async def get_prometheus_metrics(self) -> str:
        mem = self._get_memory()
        stats = mem.get_run_stats()
        lines = [
            "# HELP agentcore_runs_total Total agent pattern runs",
            "# TYPE agentcore_runs_total counter",
            f"agentcore_runs_total {self._prom_counters['runs_total']}",
            "# HELP agentcore_benchmark_composite_score_avg Average composite benchmark score",
            "# TYPE agentcore_benchmark_composite_score_avg gauge",
            f"agentcore_benchmark_composite_score_avg {stats.get('avg_composite_score', 0):.4f}",
            "# HELP agentcore_cost_usd_total Total LLM cost in USD",
            "# TYPE agentcore_cost_usd_total counter",
            f"agentcore_cost_usd_total {stats.get('total_cost_usd', 0):.6f}",
        ]
        return "\n".join(lines) + "\n"

    # ── Scheduler ────────────────────────────────────────────────────────────

    async def start_scheduler(self):
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
            self._scheduler = AsyncIOScheduler()
            self._scheduler.add_job(
                self._daily_research_loop,
                CronTrigger(hour=6, minute=0),
                id="daily_research",
                replace_existing=True,
            )
            self._scheduler.start()
        except ImportError:
            pass

    async def _daily_research_loop(self):
        try:
            await self.update_knowledge()
        except Exception:
            pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _init_prometheus() -> dict:
    return {"runs_total": 0}


def _format_tools(tool_defs: list[dict]) -> str:
    if not tool_defs:
        return "No tools available."
    lines = []
    for t in tool_defs:
        lines.append(f"- {t['name']}: {t.get('description', '')}")
    return "\n".join(lines)


def _extract_final_answer(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if content:
                if "Final Answer:" in content:
                    return content.split("Final Answer:")[-1].strip()
                return content.strip()
    return "No final answer produced."


def _render_run_report(
    run_id: str,
    pattern: str,
    provider: str,
    task: str,
    final_answer: str,
    tool_calls: list[dict],
    benchmark: dict,
    cost_usd: float,
    elapsed_ms: float,
) -> str:
    lines = [
        f"# agentcore-enhanced Run Report — {run_id}",
        "",
        f"**Pattern:** {pattern}  |  **Provider:** {provider}  |  **Cost:** ${cost_usd:.4f}  |  **Latency:** {elapsed_ms:.0f}ms",
        "",
        f"## Task",
        f"{task}",
        "",
        f"## Final Answer",
        f"{final_answer}",
        "",
        f"## Tool Calls ({len(tool_calls)})",
    ]
    if tool_calls:
        lines.append("| # | Tool | Status | Preview |")
        lines.append("|---|------|--------|---------|")
        for i, tc in enumerate(tool_calls, 1):
            status = "✓" if tc.get("success") else "✗"
            preview = tc.get("result_preview", tc.get("error", ""))[:60]
            lines.append(f"| {i} | {tc['tool']} | {status} | {preview} |")
    else:
        lines.append("_No tool calls made._")

    b = benchmark
    lines += [
        "",
        "## Benchmark Scores",
        f"| Metric | Score |",
        f"|--------|-------|",
        f"| Task Success | {b.get('task_success', 0):.3f} |",
        f"| Token Efficiency | {b.get('token_efficiency', 0):.3f} |",
        f"| Error Recovery | {b.get('error_recovery', 0):.3f} |",
        f"| Quality Score (0-5) | {b.get('quality_score', 0):.2f} |",
        f"| Latency (ms) | {b.get('latency_ms', 0):.0f} |",
        f"| **Composite Score** | **{b.get('composite_score', 0):.3f}** |",
    ]

    if b.get("composite_score", 0) < 0.40:
        lines.append("")
        lines.append("> ⚠️  Composite score below 0.40 threshold. Consider switching provider or reviewing pattern choice.")

    return "\n".join(lines)


def _render_comparison_report(
    pattern_query: str,
    task: str,
    results: list[dict],
    best_provider: str,
) -> str:
    lines = [
        f"# Provider Comparison Report",
        "",
        f"**Pattern:** {pattern_query}",
        f"**Task:** {task[:80]}{'...' if len(task) > 80 else ''}",
        "",
        "## Results",
        "| Provider | Composite | Task Success | Quality (0-5) | Cost ($) | Latency (ms) |",
        "|----------|-----------|--------------|--------------|---------|-------------|",
    ]
    for r in sorted(results, key=lambda x: x.get("composite_score", 0), reverse=True):
        provider = r["provider"]
        flag = " ★" if provider == best_provider else ""
        if "error" in r:
            lines.append(f"| {provider}{flag} | ERROR | — | — | — | — |")
        else:
            lines.append(
                f"| {provider}{flag} | {r.get('composite_score', 0):.3f} "
                f"| {r.get('task_success', 0):.2f} "
                f"| {r.get('quality_score', 0):.1f} "
                f"| {r.get('cost_usd', 0):.4f} "
                f"| {r.get('latency_ms', 0):.0f} |"
            )
    lines.append("")
    lines.append(f"**Winner: {best_provider}**")
    return "\n".join(lines)
