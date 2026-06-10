"""knowledge_updater.py — Research paper crawler for agentcore-enhanced.

Schedule: Daily at 06:00 (APScheduler CronTrigger)
Sources: ArXiv cs.AI/cs.MA/cs.LG/cs.SE, Semantic Scholar, GitHub Releases, Papers with Code
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

BRAIN_PATH = ROOT / "SECOND-KNOWLEDGE-BRAIN.md"
ARXIV_CATEGORIES = ["cs.AI", "cs.MA", "cs.LG", "cs.SE"]
GITHUB_REPOS = [
    "awslabs/agentcore-samples",
    "langchain-ai/langchain",
    "run-llama/llama_index",
    "crewAIInc/crewAI",
    "microsoft/autogen",
]
SEMANTIC_SCHOLAR_QUERIES = [
    "multi-agent LLM orchestration",
    "agent evaluation benchmark",
    "model context protocol MCP tools",
    "LLM tool use function calling",
    "autonomous agent architecture",
]
DOMAIN_KEYWORDS = [
    "agent", "orchestration", "multi-agent", "tool use", "function calling",
    "MCP", "evaluation", "benchmark", "ReAct", "chain-of-thought", "autonomous",
    "LLM reasoning", "agent framework", "memory augmented",
]
TOP_N_PER_SOURCE = 10


class KnowledgeUpdater:

    def __init__(self):
        from agent.memory.memory_manager import MemoryManager
        self.mem = MemoryManager()

    async def run_daily_update(self) -> dict:
        added = 0
        papers = []

        arxiv_papers = await self._crawl_arxiv()
        papers.extend(arxiv_papers)

        scholar_papers = await self._crawl_semantic_scholar()
        papers.extend(scholar_papers)

        github_entries = await self._crawl_github_releases()
        papers.extend(github_entries)

        scored = self._score_papers(papers)
        top_papers = scored[:TOP_N_PER_SOURCE * len(ARXIV_CATEGORIES)]

        for paper in top_papers:
            identifier = paper.get("doi") or paper.get("arxiv_id") or paper.get("url", "")
            if not identifier or self.mem.is_known_paper(identifier):
                continue
            self._append_to_brain(paper)
            self.mem.mark_paper_known(
                identifier,
                title=paper.get("title", ""),
                source=paper.get("source", ""),
            )
            added += 1

        log_entry = f"| {datetime.utcnow().date().isoformat()} | Crawled {len(papers)} entries, added {added} new | ArXiv+Scholar+GitHub | — |"
        next_scheduled = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d 06:00 UTC")

        return {
            "papers_added": added,
            "next_scheduled": next_scheduled,
            "log_entry": log_entry,
        }

    async def _crawl_arxiv(self) -> list[dict]:
        papers = []
        try:
            import aiohttp
        except ImportError:
            return papers

        for cat in ARXIV_CATEGORIES:
            try:
                url = (
                    f"https://export.arxiv.org/api/query?"
                    f"search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&max_results=25"
                )
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            continue
                        text = await resp.text()

                import xml.etree.ElementTree as ET
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                root = ET.fromstring(text)
                for entry in root.findall("atom:entry", ns):
                    title_el = entry.find("atom:title", ns)
                    abstract_el = entry.find("atom:summary", ns)
                    id_el = entry.find("atom:id", ns)
                    published_el = entry.find("atom:published", ns)
                    authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)
                               if a.find("atom:name", ns) is not None]

                    if title_el is None:
                        continue

                    arxiv_id = id_el.text.split("/")[-1] if id_el is not None else ""
                    papers.append({
                        "title": title_el.text.strip().replace("\n", " "),
                        "abstract": abstract_el.text.strip()[:400] if abstract_el is not None else "",
                        "arxiv_id": arxiv_id,
                        "url": id_el.text if id_el is not None else "",
                        "authors": ", ".join(authors[:3]),
                        "published": published_el.text[:10] if published_el is not None else "",
                        "source": f"ArXiv:{cat}",
                        "venue": f"arXiv {cat}",
                    })
            except Exception:
                continue

        return papers

    async def _crawl_semantic_scholar(self) -> list[dict]:
        papers = []
        try:
            import aiohttp
        except ImportError:
            return papers

        base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        fields = "title,authors,year,abstract,citationCount,externalIds,venue"

        for query in SEMANTIC_SCHOLAR_QUERIES:
            try:
                params = {"query": query, "fields": fields, "limit": 15}
                async with aiohttp.ClientSession() as session:
                    async with session.get(base_url, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()

                for paper in data.get("data", []):
                    doi = (paper.get("externalIds") or {}).get("DOI", "")
                    arxiv_id = (paper.get("externalIds") or {}).get("ArXiv", "")
                    authors = ", ".join(
                        a.get("name", "") for a in (paper.get("authors") or [])[:3]
                    )
                    papers.append({
                        "title": paper.get("title", ""),
                        "abstract": (paper.get("abstract") or "")[:400],
                        "authors": authors,
                        "doi": doi,
                        "arxiv_id": arxiv_id,
                        "url": f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                        "published": str(paper.get("year", "")),
                        "citations": paper.get("citationCount", 0),
                        "source": "SemanticScholar",
                        "venue": paper.get("venue", ""),
                    })
                await asyncio.sleep(0.5)
            except Exception:
                continue

        return papers

    async def _crawl_github_releases(self) -> list[dict]:
        entries = []
        try:
            import aiohttp
        except ImportError:
            return entries

        gh_token = os.getenv("GITHUB_TOKEN", "")
        headers = {"Authorization": f"token {gh_token}"} if gh_token else {}

        for repo in GITHUB_REPOS:
            try:
                url = f"https://api.github.com/repos/{repo}/releases/latest"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()

                tag = data.get("tag_name", "")
                body = data.get("body", "")[:300]
                published = data.get("published_at", "")[:10]
                entries.append({
                    "title": f"{repo} release {tag}",
                    "abstract": body,
                    "url": data.get("html_url", ""),
                    "published": published,
                    "source": "GitHub",
                    "venue": "GitHub Releases",
                    "authors": repo.split("/")[0],
                })
                await asyncio.sleep(0.3)
            except Exception:
                continue

        return entries

    def _score_papers(self, papers: list[dict]) -> list[dict]:
        now = datetime.utcnow().date()
        scored = []
        for p in papers:
            recency = 0.1
            try:
                pub_str = p.get("published", "")[:10]
                if pub_str:
                    pub_date = datetime.strptime(pub_str, "%Y-%m-%d").date()
                    days_old = (now - pub_date).days
                    if days_old <= 7:
                        recency = 1.0
                    elif days_old <= 30:
                        recency = 0.7
                    elif days_old <= 90:
                        recency = 0.4
            except Exception:
                pass

            text = f"{p.get('title', '')} {p.get('abstract', '')}".lower()
            keyword_hits = sum(1 for kw in DOMAIN_KEYWORDS if kw.lower() in text)
            relevance = min(1.0, keyword_hits / 5.0)

            p["_score"] = recency * relevance
            scored.append(p)

        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored

    def _append_to_brain(self, paper: dict):
        title = paper.get("title", "Untitled")
        authors = paper.get("authors", "Unknown")
        source = paper.get("source", "Unknown")
        url = paper.get("url", "")
        date = paper.get("published", datetime.utcnow().date().isoformat())
        abstract = paper.get("abstract", "")[:200].replace("|", "/").replace("\n", " ")

        entry = f"| {date} | {title[:80]} | {authors[:40]} | {source} | [{url[:60]}]({url}) | {abstract} |\n"

        if not BRAIN_PATH.exists():
            return

        content = BRAIN_PATH.read_text(encoding="utf-8")
        if "## Knowledge Update Log" in content:
            insert_pos = content.find("## Knowledge Update Log") + len("## Knowledge Update Log\n\n")
            header_end = content.find("\n", insert_pos)
            table_start = content.find("| Date |", insert_pos)
            if table_start == -1:
                new_content = (
                    content[:insert_pos]
                    + "| Date | Title | Authors | Source | Link | Key Finding |\n"
                    + "|------|-------|---------|--------|------|-------------|\n"
                    + entry
                    + content[insert_pos:]
                )
            else:
                first_row_end = content.find("\n", table_start)
                second_row_end = content.find("\n", first_row_end + 1)
                insert_at = second_row_end + 1
                new_content = content[:insert_at] + entry + content[insert_at:]
            BRAIN_PATH.write_text(new_content, encoding="utf-8")


async def _main():
    updater = KnowledgeUpdater()
    result = await updater.run_daily_update()
    print(f"Papers added: {result['papers_added']}")
    print(f"Next scheduled: {result['next_scheduled']}")


if __name__ == "__main__":
    asyncio.run(_main())
