"""agentcore-enhanced — CLI and FastAPI server entry point."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agent.orchestrator import AgentCoreOrchestrator

app = FastAPI(
    title="agentcore-enhanced",
    description="Multi-Cloud Agent Orchestrator — provider-portable, MCP-native, self-evaluating",
    version="1.0.0",
)

_orchestrator: Optional[AgentCoreOrchestrator] = None


def get_orchestrator() -> AgentCoreOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentCoreOrchestrator()
    return _orchestrator


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    pattern: str = Field(..., description="Pattern name or semantic query (e.g. 'react', 'chain-of-thought')")
    task: str = Field(..., description="Task description for the agent")
    provider: str = Field("claude", description="Provider: claude|openai|azure|gcp|ollama|vllm")
    max_steps: int = Field(10, ge=1, le=30)
    stream: bool = Field(False)


class RunResponse(BaseModel):
    run_id: str
    pattern_used: str
    provider_used: str
    final_answer: str
    tool_calls_count: int
    benchmark: dict
    cost_usd: float
    latency_ms: float
    report_markdown: str


class BenchmarkRequest(BaseModel):
    pattern: str
    task: str
    providers: list[str] = Field(default_factory=lambda: ["claude", "openai", "ollama"])
    max_steps: int = Field(5, ge=1, le=20)


class BenchmarkResponse(BaseModel):
    pattern: str
    task: str
    results: list[dict]
    best_provider: str
    comparison_markdown: str


class PatternSearchRequest(BaseModel):
    query: str
    provider_filter: Optional[str] = None
    top_k: int = Field(3, ge=1, le=10)


class KnowledgeUpdateResponse(BaseModel):
    papers_added: int
    next_scheduled: str
    log_entry: str


# ── FastAPI endpoints ─────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agentcore-enhanced"}


@app.post("/run", response_model=RunResponse)
async def run_pattern(req: RunRequest):
    orch = get_orchestrator()
    try:
        result = await orch.run_pattern(
            pattern_query=req.pattern,
            task=req.task,
            provider=req.provider,
            max_steps=req.max_steps,
        )
        return RunResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/benchmark", response_model=BenchmarkResponse)
async def benchmark_providers(req: BenchmarkRequest):
    orch = get_orchestrator()
    try:
        result = await orch.benchmark_all_providers(
            pattern_query=req.pattern,
            task=req.task,
            providers=req.providers,
            max_steps=req.max_steps,
        )
        return BenchmarkResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/patterns/search")
async def search_patterns(req: PatternSearchRequest):
    orch = get_orchestrator()
    try:
        patterns = await orch.pattern_search(
            query=req.query,
            provider_filter=req.provider_filter,
            top_k=req.top_k,
        )
        return {"query": req.query, "results": patterns}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/patterns")
async def list_patterns():
    orch = get_orchestrator()
    try:
        patterns = await orch.list_all_patterns()
        return {"count": len(patterns), "patterns": patterns}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/knowledge/update", response_model=KnowledgeUpdateResponse)
async def update_knowledge():
    orch = get_orchestrator()
    try:
        result = await orch.update_knowledge()
        return KnowledgeUpdateResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/cost")
async def cost_report():
    orch = get_orchestrator()
    try:
        report = await orch.get_cost_report()
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/metrics")
async def prometheus_metrics():
    orch = get_orchestrator()
    try:
        metrics_text = await orch.get_prometheus_metrics()
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(metrics_text, media_type="text/plain; version=0.0.4")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """agentcore-enhanced — Multi-Cloud Agent Orchestrator CLI"""


@cli.command()
@click.option("--pattern", "-p", required=True, help="Pattern name or search query")
@click.option("--task", "-t", required=True, help="Task for the agent to execute")
@click.option("--provider", default="claude", help="LLM provider (claude|openai|azure|gcp|ollama|vllm)")
@click.option("--max-steps", default=10, help="Maximum agent execution steps")
def run(pattern: str, task: str, provider: str, max_steps: int):
    """Execute an agent pattern against a task."""
    orch = get_orchestrator()
    result = asyncio.run(orch.run_pattern(
        pattern_query=pattern, task=task, provider=provider, max_steps=max_steps
    ))
    click.echo(result["report_markdown"])
    click.echo(f"\nBenchmark composite score: {result['benchmark'].get('composite_score', 0):.3f}")
    click.echo(f"Cost: ${result['cost_usd']:.4f} | Latency: {result['latency_ms']:.0f}ms")


@cli.command()
@click.option("--pattern", "-p", required=True, help="Pattern name or search query")
@click.option("--task", "-t", required=True, help="Task for the benchmark")
@click.option("--providers", default="claude,openai,ollama", help="Comma-separated providers to compare")
@click.option("--max-steps", default=5)
def benchmark(pattern: str, task: str, providers: str, max_steps: int):
    """Benchmark one pattern across multiple providers and compare results."""
    provider_list = [p.strip() for p in providers.split(",")]
    orch = get_orchestrator()
    result = asyncio.run(orch.benchmark_all_providers(
        pattern_query=pattern, task=task, providers=provider_list, max_steps=max_steps
    ))
    click.echo(result["comparison_markdown"])
    click.echo(f"\nBest provider: {result['best_provider']}")


@cli.command(name="pattern")
@click.argument("action", type=click.Choice(["search", "list", "info"]))
@click.option("--query", "-q", default="", help="Search query for semantic pattern lookup")
@click.option("--name", "-n", default="", help="Exact pattern name for info")
@click.option("--provider-filter", default=None, help="Filter by provider compatibility")
def pattern_cmd(action: str, query: str, name: str, provider_filter: str):
    """Search, list, or inspect agent patterns in the library."""
    orch = get_orchestrator()
    if action == "search":
        if not query:
            raise click.UsageError("--query required for search")
        results = asyncio.run(orch.pattern_search(query=query, provider_filter=provider_filter))
        for i, r in enumerate(results, 1):
            click.echo(f"\n[{i}] {r['name']} (similarity: {r.get('similarity', 0):.3f})")
            click.echo(f"    {r['description']}")
            click.echo(f"    Recommended providers: {', '.join(r.get('recommended_providers', []))}")
    elif action == "list":
        patterns = asyncio.run(orch.list_all_patterns())
        click.echo(f"{'#':<3} {'Name':<30} {'Tools Required':<25} {'Providers'}")
        click.echo("-" * 80)
        for i, p in enumerate(patterns, 1):
            tools = ", ".join(p.get("tools_required", [])[:2])
            providers = ", ".join(p.get("recommended_providers", [])[:3])
            click.echo(f"{i:<3} {p['name']:<30} {tools:<25} {providers}")
    elif action == "info":
        if not name:
            raise click.UsageError("--name required for info")
        results = asyncio.run(orch.pattern_search(query=name, top_k=1))
        if results:
            click.echo(json.dumps(results[0], indent=2))


@cli.command(name="update-knowledge")
def update_knowledge():
    """Run the research paper crawler and update SECOND-KNOWLEDGE-BRAIN.md."""
    orch = get_orchestrator()
    result = asyncio.run(orch.update_knowledge())
    click.echo(f"Papers added: {result['papers_added']}")
    click.echo(f"Next scheduled: {result['next_scheduled']}")
    click.echo(result["log_entry"])


@cli.command(name="cost-report")
@click.option("--days", default=30, help="Number of days to include in report")
def cost_report_cmd(days: int):
    """Print LLM cost breakdown for the last N days."""
    orch = get_orchestrator()
    report = asyncio.run(orch.get_cost_report(days=days))
    click.echo(f"\n=== Cost Report (last {days} days) ===")
    click.echo(f"Total: ${report.get('total_usd', 0):.4f}")
    click.echo("\nBy provider:")
    for provider, cost in report.get("by_provider", {}).items():
        click.echo(f"  {provider:<15} ${cost:.4f}")
    click.echo("\nBy pattern:")
    for pat, cost in report.get("by_pattern", {}).items():
        click.echo(f"  {pat:<30} ${cost:.4f}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=7865, help="Server port")
@click.option("--start-scheduler/--no-scheduler", default=True)
def serve(host: str, port: int, start_scheduler: bool):
    """Start the FastAPI server (with optional background scheduler)."""
    if start_scheduler:
        orch = get_orchestrator()
        asyncio.run(_start_with_scheduler(orch))
    uvicorn.run("agent.main:app", host=host, port=port, reload=False)


async def _start_with_scheduler(orch: AgentCoreOrchestrator):
    await orch.start_scheduler()


if __name__ == "__main__":
    cli()
