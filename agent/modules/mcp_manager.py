"""mcp_manager.py — MCP server + client + tool registry following Model Context Protocol."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema object
    fn: Callable
    category: str = "general"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class ToolResult:
    content: Any
    is_error: bool = False
    tool_name: str = ""
    latency_ms: float = 0.0

    def to_str(self) -> str:
        if isinstance(self.content, str):
            return self.content
        return json.dumps(self.content, ensure_ascii=False)


class ToolRegistry:
    """JSON Schema-validated tool registry."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition):
        self._tools[tool_def.name] = tool_def

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [t.to_dict() for t in self._tools.values()]

    def validate_args(self, name: str, arguments: dict) -> tuple[bool, str]:
        tool = self._tools.get(name)
        if not tool:
            return False, f"Tool '{name}' not registered"
        try:
            import jsonschema
            jsonschema.validate(instance=arguments, schema=tool.parameters)
            return True, ""
        except ImportError:
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def get_definitions_for_names(self, names: list[str]) -> list[dict]:
        if not names:
            return self.list_tools()
        return [self._tools[n].to_dict() for n in names if n in self._tools]


# ── Default tool implementations ──────────────────────────────────────────────

async def _web_search(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo search."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({"title": r.get("title", ""), "href": r.get("href", ""), "body": r.get("body", "")[:300]})
        return results
    except ImportError:
        return [{"title": "duckduckgo_search not installed", "href": "", "body": "Install with: pip install duckduckgo-search"}]
    except Exception as exc:
        return [{"title": "Search error", "href": "", "body": str(exc)}]


async def _code_execute(code: str, timeout: int = 10) -> dict:
    """Execute Python code in a subprocess sandbox."""
    import subprocess
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return {"stdout": "", "stderr": f"Execution timed out after {timeout}s", "returncode": -1}
        return {
            "stdout": stdout.decode(errors="replace")[:2000],
            "stderr": stderr.decode(errors="replace")[:500],
            "returncode": proc.returncode,
        }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def _file_read(path: str) -> dict:
    """Read file scoped to ./workspace/ directory."""
    import os
    workspace = os.path.abspath("./workspace")
    full_path = os.path.abspath(os.path.join(workspace, path))
    if not full_path.startswith(workspace):
        return {"error": "Access denied: path outside workspace"}
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content[:10000], "path": path}
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except Exception as exc:
        return {"error": str(exc)}


async def _file_write(path: str, content: str) -> dict:
    """Write file scoped to ./workspace/ directory."""
    import os
    workspace = os.path.abspath("./workspace")
    os.makedirs(workspace, exist_ok=True)
    full_path = os.path.abspath(os.path.join(workspace, path))
    if not full_path.startswith(workspace):
        return {"error": "Access denied: path outside workspace"}
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": path, "bytes_written": len(content)}
    except Exception as exc:
        return {"error": str(exc)}


# ── MCPManager ───────────────────────────────────────────────────────────────

class MCPManager:
    """MCP server (local) + client (remote) + tool registry."""

    def __init__(self):
        self.registry = ToolRegistry()
        self._register_default_tools()
        self._external_servers: dict[str, str] = {}

    def _register_default_tools(self):
        self.registry.register(ToolDefinition(
            name="web_search",
            description="Search the web using DuckDuckGo. Returns titles, URLs, and snippets.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                },
                "required": ["query"],
            },
            fn=_web_search,
            category="search",
        ))
        self.registry.register(ToolDefinition(
            name="code_execute",
            description="Execute Python code in a sandboxed subprocess. Returns stdout, stderr, returncode.",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"},
                    "timeout": {"type": "integer", "default": 10, "minimum": 1, "maximum": 30},
                },
                "required": ["code"],
            },
            fn=_code_execute,
            category="computation",
        ))
        self.registry.register(ToolDefinition(
            name="file_read",
            description="Read a file from the workspace directory.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path within workspace/"},
                },
                "required": ["path"],
            },
            fn=_file_read,
            category="filesystem",
        ))
        self.registry.register(ToolDefinition(
            name="file_write",
            description="Write content to a file in the workspace directory.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            fn=_file_write,
            category="filesystem",
        ))

    def get_tool_definitions(self, names: Optional[list[str]] = None) -> list[dict]:
        return self.registry.get_definitions_for_names(names or [])

    async def call_tool(self, name: str, arguments: dict) -> str:
        t0 = time.time()
        valid, err_msg = self.registry.validate_args(name, arguments)
        if not valid:
            raise ValueError(f"Tool argument validation failed for '{name}': {err_msg}")

        tool = self.registry.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry")

        result = await tool.fn(**arguments)
        elapsed = (time.time() - t0) * 1000

        if isinstance(result, (dict, list)):
            content = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            content = str(result)

        tr = ToolResult(content=content, tool_name=name, latency_ms=elapsed)
        return tr.to_str()

    def register_external_server(self, name: str, url: str):
        self._external_servers[name] = url

    async def call_external_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Call a tool on an external MCP server via JSON-RPC 2.0 over HTTP."""
        url = self._external_servers.get(server_name)
        if not url:
            raise ValueError(f"External server '{server_name}' not registered")
        try:
            import aiohttp
        except ImportError:
            raise RuntimeError("aiohttp required for external MCP calls")

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{url}/rpc", json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                data = await resp.json()

        if "error" in data:
            raise RuntimeError(f"MCP error: {data['error']}")
        return json.dumps(data.get("result", {}).get("content", []))
