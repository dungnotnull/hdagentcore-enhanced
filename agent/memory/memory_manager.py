"""memory_manager.py — SQLite-backed persistent memory for agentcore-enhanced."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "agentcore.db"


class MemoryManager:
    """Thread-safe SQLite memory manager."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    pattern TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    task TEXT NOT NULL,
                    final_answer TEXT,
                    tool_calls_count INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0,
                    latency_ms REAL DEFAULT 0,
                    composite_score REAL DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_runs_pattern ON runs(pattern);
                CREATE INDEX IF NOT EXISTS idx_runs_provider ON runs(provider);
                CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);

                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    task_success REAL,
                    token_efficiency REAL,
                    error_recovery REAL,
                    latency_ms REAL,
                    quality_score REAL,
                    composite_score REAL,
                    eval_cost_usd REAL DEFAULT 0,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_bench_provider ON benchmark_results(provider);
                CREATE INDEX IF NOT EXISTS idx_bench_pattern ON benchmark_results(pattern);

                CREATE TABLE IF NOT EXISTS pattern_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    task_type TEXT,
                    success INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS llm_cost_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    task_type TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS knowledge_hashes (
                    hash TEXT PRIMARY KEY,
                    title TEXT,
                    source TEXT,
                    added_at TEXT DEFAULT (datetime('now'))
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Runs ──────────────────────────────────────────────────────────────────

    def save_run(self, run: dict):
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO runs
                       (run_id, pattern, provider, task, final_answer, tool_calls_count,
                        cost_usd, latency_ms, composite_score)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run.get("run_id", ""),
                        run.get("pattern", ""),
                        run.get("provider", ""),
                        run.get("task", "")[:500],
                        run.get("final_answer", "")[:2000],
                        run.get("tool_calls_count", 0),
                        run.get("cost_usd", 0),
                        run.get("latency_ms", 0),
                        run.get("composite_score", 0),
                    ),
                )

    def get_run(self, run_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            return dict(row) if row else None

    def get_recent_runs(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_run_stats(self) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as total, AVG(composite_score) as avg_score, SUM(cost_usd) as total_cost FROM runs"
            ).fetchone()
            return {
                "total_runs": row["total"] or 0,
                "avg_composite_score": row["avg_score"] or 0,
                "total_cost_usd": row["total_cost"] or 0,
            }

    # ── Benchmark ─────────────────────────────────────────────────────────────

    def save_benchmark(self, result: dict):
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT INTO benchmark_results
                       (run_id, pattern, provider, task_success, token_efficiency,
                        error_recovery, latency_ms, quality_score, composite_score,
                        eval_cost_usd, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        result.get("run_id", ""),
                        result.get("pattern", ""),
                        result.get("provider", ""),
                        result.get("task_success", 0),
                        result.get("token_efficiency", 0),
                        result.get("error_recovery", 0),
                        result.get("latency_ms", 0),
                        result.get("quality_score", 0),
                        result.get("composite_score", 0),
                        result.get("eval_cost_usd", 0),
                        result.get("notes", ""),
                    ),
                )

    def get_benchmark_history(self, provider: Optional[str] = None, pattern: Optional[str] = None, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            query = "SELECT * FROM benchmark_results WHERE 1=1"
            params: list[Any] = []
            if provider:
                query += " AND provider = ?"
                params.append(provider)
            if pattern:
                query += " AND pattern = ?"
                params.append(pattern)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_provider_benchmark_summary(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT provider,
                          COUNT(*) as total_runs,
                          AVG(composite_score) as avg_composite,
                          AVG(task_success) as avg_task_success,
                          AVG(quality_score) as avg_quality,
                          AVG(latency_ms) as avg_latency_ms,
                          SUM(eval_cost_usd) as total_eval_cost
                   FROM benchmark_results
                   GROUP BY provider
                   ORDER BY avg_composite DESC"""
            ).fetchall()
            return [dict(r) for r in rows]

    # ── LLM Cost ──────────────────────────────────────────────────────────────

    def log_llm_cost(self, provider: str, task_type: str, tokens: int, cost_usd: float):
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO llm_cost_log (provider, task_type, tokens_used, cost_usd) VALUES (?, ?, ?, ?)",
                    (provider, task_type, tokens, cost_usd),
                )

    def get_cost_summary(self, days: int = 30) -> dict:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            total_row = conn.execute(
                "SELECT SUM(cost_usd) as total FROM llm_cost_log WHERE created_at >= ?", (since,)
            ).fetchone()

            by_provider = {}
            for row in conn.execute(
                "SELECT provider, SUM(cost_usd) as cost FROM llm_cost_log WHERE created_at >= ? GROUP BY provider",
                (since,),
            ).fetchall():
                by_provider[row["provider"]] = round(row["cost"] or 0, 6)

            by_task = {}
            for row in conn.execute(
                "SELECT task_type, SUM(cost_usd) as cost FROM llm_cost_log WHERE created_at >= ? GROUP BY task_type",
                (since,),
            ).fetchall():
                by_task[row["task_type"]] = round(row["cost"] or 0, 6)

        return {
            "total_usd": round(total_row["total"] or 0, 6),
            "days": days,
            "by_provider": by_provider,
            "by_pattern": by_task,
        }

    # ── Knowledge hashes ──────────────────────────────────────────────────────

    def is_known_paper(self, identifier: str) -> bool:
        h = hashlib.sha256(identifier.encode()).hexdigest()
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM knowledge_hashes WHERE hash = ?", (h,)).fetchone()
            return row is not None

    def mark_paper_known(self, identifier: str, title: str = "", source: str = ""):
        h = hashlib.sha256(identifier.encode()).hexdigest()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO knowledge_hashes (hash, title, source) VALUES (?, ?, ?)",
                    (h, title[:200], source[:100]),
                )

    def count_known_papers(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) as c FROM knowledge_hashes").fetchone()
            return row["c"] if row else 0
