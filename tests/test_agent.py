"""test_agent.py — Automated tests for agentcore-enhanced."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ── ProviderAdapter tests ─────────────────────────────────────────────────────

class TestProviderAdapter(unittest.TestCase):

    def setUp(self):
        from agent.modules.provider_adapter import ProviderAdapter, CompletionResult
        self.ProviderAdapter = ProviderAdapter
        self.CompletionResult = CompletionResult

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_completion_result_to_dict(self):
        from agent.modules.provider_adapter import CompletionResult
        r = CompletionResult(
            text="hello",
            provider_used="claude",
            model_used="claude-opus-4-8",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=1200.0,
            cost_usd=0.005,
        )
        d = r.to_dict()
        self.assertEqual(d["text"], "hello")
        self.assertEqual(d["provider_used"], "claude")
        self.assertIn("cost_usd", d)

    def test_fallback_chain_ordering(self):
        from agent.modules.provider_adapter import _build_fallback_chain
        chain = _build_fallback_chain("openai")
        self.assertEqual(chain[0], "openai")
        self.assertIn("claude", chain)
        self.assertIn("ollama", chain)

    def test_to_claude_tools_format(self):
        from agent.modules.provider_adapter import _to_claude_tools
        tools = [{"name": "web_search", "description": "Search", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}]
        claude_tools = _to_claude_tools(tools)
        self.assertEqual(claude_tools[0]["name"], "web_search")
        self.assertIn("input_schema", claude_tools[0])

    def test_to_openai_tools_format(self):
        from agent.modules.provider_adapter import _to_openai_tools
        tools = [{"name": "code_execute", "description": "Run Python", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}}}]
        openai_tools = _to_openai_tools(tools)
        self.assertEqual(openai_tools[0]["type"], "function")
        self.assertEqual(openai_tools[0]["function"]["name"], "code_execute")

    def test_all_providers_exhausted(self):
        from agent.modules.provider_adapter import AllProvidersExhausted
        exc = AllProvidersExhausted("all failed")
        self.assertIn("all failed", str(exc))

    def test_cost_computation(self):
        from agent.modules.provider_adapter import ClaudeAdapter
        adapter = ClaudeAdapter()
        cost = adapter._compute_cost("claude-opus-4-8", 1000, 500)
        self.assertAlmostEqual(cost, 0.015 + 0.0375, places=4)

    def test_ollama_adapter_no_key_needed(self):
        from agent.modules.provider_adapter import OllamaAdapter
        adapter = OllamaAdapter()
        self.assertEqual(adapter.provider_name, "ollama")


# ── MCPManager tests ──────────────────────────────────────────────────────────

class TestMCPManager(unittest.TestCase):

    def setUp(self):
        from agent.modules.mcp_manager import MCPManager
        self.mcp = MCPManager()

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_default_tools_registered(self):
        tools = self.mcp.registry.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("web_search", names)
        self.assertIn("code_execute", names)
        self.assertIn("file_read", names)
        self.assertIn("file_write", names)

    def test_tool_definitions_by_name(self):
        defs = self.mcp.get_tool_definitions(["web_search"])
        self.assertEqual(len(defs), 1)
        self.assertEqual(defs[0]["name"], "web_search")

    def test_tool_schema_validation_valid(self):
        ok, msg = self.mcp.registry.validate_args("web_search", {"query": "test"})
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_code_execute_sandbox(self):
        result_str = self._run(self.mcp.call_tool("code_execute", {"code": "print('hello world')"}))
        self.assertIn("hello world", result_str)

    def test_code_execute_timeout_handled(self):
        result_str = self._run(self.mcp.call_tool("code_execute", {"code": "import time; time.sleep(60)", "timeout": 2}))
        self.assertIn("timeout", result_str.lower())

    def test_external_server_registration(self):
        self.mcp.register_external_server("my-server", "http://localhost:9000")
        self.assertIn("my-server", self.mcp._external_servers)


# ── EvalBenchmark tests ───────────────────────────────────────────────────────

class TestEvalBenchmark(unittest.TestCase):

    def setUp(self):
        from agent.modules.eval_benchmark import EvalBenchmark
        self.ev = EvalBenchmark()

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_token_efficiency_no_tokens(self):
        from agent.modules.eval_benchmark import EvalBenchmark
        eff = EvalBenchmark._compute_token_efficiency(0, 0, "output")
        self.assertEqual(eff, 0.5)

    def test_token_efficiency_valid_range(self):
        from agent.modules.eval_benchmark import EvalBenchmark
        eff = EvalBenchmark._compute_token_efficiency(1000, 200, "This is a good output with meaningful content.")
        self.assertGreaterEqual(eff, 0.0)
        self.assertLessEqual(eff, 1.0)

    def test_error_recovery_no_errors(self):
        from agent.modules.eval_benchmark import EvalBenchmark
        rate = EvalBenchmark._compute_error_recovery(0, 0)
        self.assertEqual(rate, 1.0)

    def test_error_recovery_all_recovered(self):
        from agent.modules.eval_benchmark import EvalBenchmark
        rate = EvalBenchmark._compute_error_recovery(3, 3)
        self.assertEqual(rate, 1.0)

    def test_error_recovery_partial(self):
        from agent.modules.eval_benchmark import EvalBenchmark
        rate = EvalBenchmark._compute_error_recovery(4, 2)
        self.assertAlmostEqual(rate, 0.5)

    @patch("agent.modules.eval_benchmark.EvalBenchmark._llm_judge")
    def test_score_produces_valid_result(self, mock_judge):
        mock_judge.return_value = asyncio.coroutine(lambda: (
            {"task_success": 0.85, "confidence": 0.9, "quality_score": 4},
            0.002
        ))()

        async def _run():
            with patch.object(self.ev, "_llm_judge", new_callable=AsyncMock,
                              return_value=({"task_success": 0.85, "confidence": 0.9, "quality_score": 4}, 0.002)):
                return await self.ev.score(
                    run_id="test-001",
                    pattern="react",
                    provider="claude",
                    task_description="Find papers on agents",
                    agent_output="I found 3 papers: ...",
                    tool_calls=[{"tool": "web_search", "success": True, "result_preview": "results"}],
                    prompt_tokens=500,
                    completion_tokens=200,
                    errors_total=0,
                    errors_recovered=0,
                    elapsed_ms=3000,
                )
        result = self._run(_run())
        self.assertIn("composite_score", result)
        self.assertGreaterEqual(result["composite_score"], 0.0)
        self.assertLessEqual(result["composite_score"], 1.0)

    def test_fallback_scores_empty_output(self):
        from agent.modules.eval_benchmark import _fallback_scores
        s = _fallback_scores("")
        self.assertEqual(s["task_success"], 0.0)

    def test_fallback_scores_long_output(self):
        from agent.modules.eval_benchmark import _fallback_scores
        s = _fallback_scores("word " * 100)
        self.assertGreater(s["task_success"], 0.5)


# ── PatternLibrary tests ──────────────────────────────────────────────────────

class TestPatternLibrary(unittest.TestCase):

    def setUp(self):
        from agent.modules.pattern_library import PatternLibrary
        self.pl = PatternLibrary()

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_list_all_returns_15_patterns(self):
        patterns = self.pl.list_all()
        self.assertEqual(len(patterns), 15)

    def test_get_by_name_exact(self):
        cfg = self.pl.get_by_name("react")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["name"], "react")

    def test_get_by_name_partial(self):
        cfg = self.pl.get_by_name("chain")
        self.assertIsNotNone(cfg)
        self.assertIn("chain", cfg["name"])

    def test_keyword_search_react(self):
        results = self.pl._keyword_search("react reason act", 3)
        names = [r["name"] for r in results]
        self.assertIn("react", names)

    def test_keyword_search_code(self):
        results = self.pl._keyword_search("code execute python", 3)
        self.assertGreater(len(results), 0)

    def test_pattern_has_required_fields(self):
        patterns = self.pl.list_all()
        for p in patterns:
            self.assertIn("name", p)
            self.assertIn("description", p)
            self.assertIn("system_prompt", p)
            self.assertIn("tools_required", p)
            self.assertIn("recommended_providers", p)

    def test_all_patterns_have_recommended_providers(self):
        patterns = self.pl.list_all()
        for p in patterns:
            self.assertGreater(len(p["recommended_providers"]), 0)

    @patch.object(sys.modules.get("agent.modules.pattern_library", MagicMock()), "_PATTERN_INDEX", {})
    def test_search_returns_results(self):
        async def _run():
            return await self.pl.search("reasoning tool use", top_k=3)
        results = self._run(_run())
        self.assertGreater(len(results), 0)


# ── MemoryManager tests ───────────────────────────────────────────────────────

class TestMemoryManager(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()
        from agent.memory.memory_manager import MemoryManager
        self.mem = MemoryManager(db_path=Path(self.tmpdir) / "test.db")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_get_run(self):
        self.mem.save_run({
            "run_id": "r001",
            "pattern": "react",
            "provider": "claude",
            "task": "test task",
            "final_answer": "test answer",
            "composite_score": 0.75,
        })
        run = self.mem.get_run("r001")
        self.assertIsNotNone(run)
        self.assertEqual(run["pattern"], "react")

    def test_save_benchmark(self):
        self.mem.save_benchmark({
            "run_id": "r001",
            "pattern": "react",
            "provider": "claude",
            "task_success": 0.8,
            "token_efficiency": 0.6,
            "error_recovery": 1.0,
            "latency_ms": 2000,
            "quality_score": 4.0,
            "composite_score": 0.72,
        })
        history = self.mem.get_benchmark_history(provider="claude")
        self.assertEqual(len(history), 1)

    def test_llm_cost_log_and_summary(self):
        self.mem.log_llm_cost("claude", "run_pattern", 1500, 0.025)
        self.mem.log_llm_cost("openai", "benchmark", 800, 0.008)
        summary = self.mem.get_cost_summary(days=30)
        self.assertGreater(summary["total_usd"], 0)
        self.assertIn("claude", summary["by_provider"])

    def test_knowledge_hash_dedup(self):
        self.mem.mark_paper_known("arxiv:2210.03629", title="ReAct", source="ArXiv")
        self.assertTrue(self.mem.is_known_paper("arxiv:2210.03629"))
        self.assertFalse(self.mem.is_known_paper("arxiv:9999.99999"))

    def test_run_stats(self):
        self.mem.save_run({"run_id": "r002", "pattern": "cot", "provider": "openai", "task": "t", "composite_score": 0.80})
        stats = self.mem.get_run_stats()
        self.assertGreaterEqual(stats["total_runs"], 1)


# ── LLMClient tests ───────────────────────────────────────────────────────────

class TestLLMClient(unittest.TestCase):

    def setUp(self):
        from tools.llm_client import UnifiedLLMClient
        self.client = UnifiedLLMClient()

    def test_build_chain_preferred_first(self):
        from tools.llm_client import _build_chain
        chain = _build_chain("openai")
        self.assertEqual(chain[0], "openai")

    def test_default_model(self):
        from tools.llm_client import _default_model
        self.assertEqual(_default_model("claude"), "claude-opus-4-8")
        self.assertEqual(_default_model("openai"), "gpt-4o")
        self.assertEqual(_default_model("ollama"), "llama3")

    def test_calc_cost_claude(self):
        from tools.llm_client import _calc_cost
        cost = _calc_cost("claude-opus-4-8", 1000, 500)
        self.assertAlmostEqual(cost, 0.015 + 0.0375, places=4)


# ── HFModelManager tests ──────────────────────────────────────────────────────

class TestHFModelManager(unittest.TestCase):

    def setUp(self):
        from tools.hf_model_manager import HFModelManager
        self.mgr = HFModelManager()

    def test_tfidf_fallback_returns_vectors(self):
        from tools.hf_model_manager import HFModelManager
        vecs = HFModelManager._tfidf_fallback(["hello world", "foo bar"])
        self.assertEqual(len(vecs), 2)
        self.assertEqual(len(vecs[0]), 64)

    def test_heuristic_rerank_overlap(self):
        from tools.hf_model_manager import HFModelManager
        scores = HFModelManager._heuristic_rerank(
            "agent orchestration", ["agent systems", "database query", "agent orchestration framework"]
        )
        self.assertEqual(len(scores), 3)
        self.assertGreater(scores[2], scores[1])

    def test_model_registry_has_all_keys(self):
        from tools.hf_model_manager import MODEL_REGISTRY
        for key in ["bge_large", "minilm", "codet5p", "bge_reranker"]:
            self.assertIn(key, MODEL_REGISTRY)


# ── Integration tests ─────────────────────────────────────────────────────────

class TestIntegration(unittest.TestCase):

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_orchestrator_initializes(self):
        from agent.orchestrator import AgentCoreOrchestrator
        orch = AgentCoreOrchestrator()
        self.assertIsNotNone(orch)

    def test_pattern_library_search_integration(self):
        from agent.modules.pattern_library import PatternLibrary
        pl = PatternLibrary()
        async def _run():
            return await pl.search("multi-agent debate vote", top_k=3)
        results = self._run(_run())
        self.assertGreater(len(results), 0)
        self.assertIn("name", results[0])

    def test_mcp_file_write_and_read_roundtrip(self):
        from agent.modules.mcp_manager import MCPManager
        import os, tempfile, shutil
        tmpdir = tempfile.mkdtemp()
        orig_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            os.makedirs("workspace", exist_ok=True)
            mcp = MCPManager()
            write_result = self._run(mcp.call_tool("file_write", {"path": "test.txt", "content": "hello agentcore"}))
            self.assertIn("success", write_result)
            read_result = self._run(mcp.call_tool("file_read", {"path": "test.txt"}))
            self.assertIn("hello agentcore", read_result)
        finally:
            os.chdir(orig_cwd)
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_benchmark_composite_range(self):
        from agent.modules.eval_benchmark import EvalBenchmark
        async def _run():
            with patch.object(EvalBenchmark, "_llm_judge", new_callable=AsyncMock,
                              return_value=({"task_success": 0.9, "confidence": 0.85, "quality_score": 4}, 0.001)):
                ev = EvalBenchmark()
                return await ev.score(
                    run_id="int-001", pattern="cot", provider="claude",
                    task_description="explain gravity",
                    agent_output="Gravity is a fundamental force..." * 5,
                    tool_calls=[], prompt_tokens=200, completion_tokens=150,
                    errors_total=0, errors_recovered=0, elapsed_ms=1500,
                )
        from unittest.mock import AsyncMock, patch
        result = self._run(_run())
        self.assertGreaterEqual(result["composite_score"], 0.0)
        self.assertLessEqual(result["composite_score"], 1.0)


# ── CLI smoke tests ───────────────────────────────────────────────────────────

class TestCLISmoke(unittest.TestCase):

    def test_cli_module_importable(self):
        import agent.main
        self.assertTrue(hasattr(agent.main, "cli"))

    def test_app_has_health_route(self):
        from agent.main import app
        routes = [r.path for r in app.routes]
        self.assertIn("/health", routes)

    def test_app_has_run_route(self):
        from agent.main import app
        routes = [r.path for r in app.routes]
        self.assertIn("/run", routes)

    def test_app_has_patterns_route(self):
        from agent.main import app
        routes = [r.path for r in app.routes]
        self.assertIn("/patterns", routes)

    def test_app_has_metrics_route(self):
        from agent.main import app
        routes = [r.path for r in app.routes]
        self.assertIn("/metrics", routes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
