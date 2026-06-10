"""pattern_library.py — Catalog of 15 reusable agent patterns with semantic search."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PatternConfig:
    name: str
    description: str
    system_prompt: str
    prompt_template: str
    tools_required: list[str]
    recommended_providers: list[str]
    requires_function_calling: bool = False
    example_tasks: list[str] = field(default_factory=list)
    benchmark_scores: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "prompt_template": self.prompt_template,
            "tools_required": self.tools_required,
            "recommended_providers": self.recommended_providers,
            "requires_function_calling": self.requires_function_calling,
            "example_tasks": self.example_tasks,
            "benchmark_scores": self.benchmark_scores,
        }


PATTERNS: list[PatternConfig] = [
    PatternConfig(
        name="react",
        description="ReAct (Reason + Act): Iterative thought/action/observation loop. Grounds reasoning in tool results to reduce hallucination.",
        system_prompt=(
            "You are an autonomous agent. Think step by step using this exact format:\n\n"
            "Thought: <reasoning about what to do next>\n"
            "Action: <tool_name>\n"
            "Action Input: <JSON arguments>\n"
            "Observation: <tool result>\n"
            "...(repeat Thought/Action/Action Input/Observation as needed)\n"
            "Thought: I now know the final answer.\n"
            "Final Answer: <comprehensive answer>"
        ),
        prompt_template="Task: {task}\n\nAvailable tools:\n{tools_list}\n\nBegin!",
        tools_required=["web_search", "code_execute", "file_read"],
        recommended_providers=["claude", "openai", "azure"],
        requires_function_calling=False,
        example_tasks=["Research the latest MCP papers", "Find and summarize top AI agent frameworks"],
        benchmark_scores={"hotpotqa": 0.71, "alfworld": 0.86, "fever": 0.78},
    ),
    PatternConfig(
        name="chain_of_thought",
        description="Chain-of-Thought (CoT): Step-by-step reasoning before final answer. No tools required. Best for complex reasoning without external data.",
        system_prompt="Think step by step. Show your reasoning explicitly before giving the final answer.",
        prompt_template="Task: {task}\n\nThink through this carefully step by step, then provide your Final Answer.",
        tools_required=[],
        recommended_providers=["claude", "openai", "gcp", "ollama"],
        requires_function_calling=False,
        example_tasks=["Solve multi-step math problems", "Analyze logical arguments", "Explain complex concepts"],
        benchmark_scores={"gsm8k": 0.95, "math": 0.68},
    ),
    PatternConfig(
        name="tree_of_thought",
        description="Tree-of-Thought (ToT): Branching reasoning with backtracking. Explores multiple solution paths and selects the best.",
        system_prompt=(
            "Explore multiple reasoning paths for this task. For each path:\n"
            "1. Generate 3 candidate next steps\n"
            "2. Evaluate each step (promising/not promising)\n"
            "3. Continue the most promising path\n"
            "4. Backtrack if stuck\n"
            "Final Answer: <best solution found>"
        ),
        prompt_template="Task: {task}\n\nExplore this problem using tree-of-thought reasoning.",
        tools_required=[],
        recommended_providers=["claude", "openai"],
        requires_function_calling=False,
        example_tasks=["Game of 24 puzzle", "Mini crossword", "Strategic planning problems"],
        benchmark_scores={"game_of_24": 0.74, "mini_crossword": 0.60},
    ),
    PatternConfig(
        name="multi_agent_parliament",
        description="Multi-Agent Parliament: N specialized agents debate a task, majority vote, moderator synthesizes. Best for high-stakes decisions.",
        system_prompt=(
            "You are {agent_name}, a {role} in a multi-agent deliberation panel.\n\n"
            "Task: {task}\n\n"
            "Previous positions:\n{positions_so_far}\n\n"
            "Provide your analysis as JSON: "
            '{"position": "agree|disagree|abstain|propose_amendment", '
            '"confidence": 0.0-1.0, "key_arguments": [...], "proposed_amendment": null}'
        ),
        prompt_template="{task}",
        tools_required=["web_search"],
        recommended_providers=["claude", "openai"],
        requires_function_calling=False,
        example_tasks=["Evaluate architecture decisions", "Risk assessment", "Policy recommendation"],
        benchmark_scores={"decision_quality": 0.82},
    ),
    PatternConfig(
        name="critic_actor",
        description="Critic-Actor: Actor drafts output, Critic evaluates and suggests improvements, iterate until quality gate passes.",
        system_prompt=(
            "You are alternating between Actor and Critic roles.\n"
            "Actor turn: Produce your best response to the task.\n"
            "Critic turn: Identify specific weaknesses and suggest improvements.\n"
            "Repeat until Critic approves or max iterations reached.\n"
            "Final Answer: <approved response>"
        ),
        prompt_template="Task: {task}\n\nBegin with the Actor role.",
        tools_required=[],
        recommended_providers=["claude", "openai"],
        requires_function_calling=False,
        example_tasks=["Code review and improvement", "Essay writing", "API design"],
        benchmark_scores={"output_quality": 0.79},
    ),
    PatternConfig(
        name="memory_augmented",
        description="Memory-Augmented: Vector store retrieval injected into every prompt. Agent builds persistent context over multi-turn interactions.",
        system_prompt=(
            "You are an agent with access to a persistent memory store.\n"
            "Relevant memories retrieved for this task:\n{retrieved_memories}\n\n"
            "Use these memories to inform your response. Update your memory with new insights."
        ),
        prompt_template="Task: {task}",
        tools_required=["file_read", "file_write"],
        recommended_providers=["claude", "openai", "azure"],
        requires_function_calling=True,
        example_tasks=["Long-running research projects", "Personal assistant", "Knowledge base building"],
        benchmark_scores={"multi_turn_coherence": 0.85},
    ),
    PatternConfig(
        name="tool_use_specialist",
        description="Tool-Use Specialist: Agent optimized for rich tool libraries. Uses structured function calling for precise tool invocation.",
        system_prompt=(
            "You are a tool-use specialist. You have access to a comprehensive set of tools.\n"
            "Always use tools to gather information rather than relying on memory.\n"
            "Available tools:\n{tools_list}"
        ),
        prompt_template="Task: {task}\n\nUse the available tools to complete this task accurately.",
        tools_required=["web_search", "code_execute", "file_read", "file_write"],
        recommended_providers=["claude", "openai", "azure"],
        requires_function_calling=True,
        example_tasks=["Data collection and analysis", "API integration testing", "Information lookup"],
        benchmark_scores={"toolbench": 0.67, "gorilla": 0.78},
    ),
    PatternConfig(
        name="code_agent",
        description="Code Agent: Writes Python code → executes in sandbox → debugs → iterates. Best for programming and data analysis tasks.",
        system_prompt=(
            "You are an expert Python programmer. Your workflow:\n"
            "1. Write Python code to solve the task\n"
            "2. Execute it using code_execute tool\n"
            "3. Debug any errors and re-execute\n"
            "4. Return the final working code and output\n"
            "Always execute code before reporting results."
        ),
        prompt_template="Programming task: {task}\n\nWrite and test Python code to solve this.",
        tools_required=["code_execute", "file_read", "file_write"],
        recommended_providers=["claude", "openai"],
        requires_function_calling=True,
        example_tasks=["Data analysis with pandas", "Write and test a sorting algorithm", "Parse and transform data"],
        benchmark_scores={"humaneval": 0.82, "mbpp": 0.79},
    ),
    PatternConfig(
        name="document_analyst",
        description="Document Analyst: Chunk → embed → RAG over uploaded documents. Best for long document Q&A and synthesis.",
        system_prompt=(
            "You are a document analysis expert.\n"
            "Retrieved document sections:\n{retrieved_sections}\n\n"
            "Answer based on the document content. Cite section numbers."
        ),
        prompt_template="Document query: {task}",
        tools_required=["file_read"],
        recommended_providers=["claude", "openai"],
        requires_function_calling=False,
        example_tasks=["Summarize a research paper", "Extract key findings", "Answer questions about a document"],
        benchmark_scores={"qasper": 0.58, "narrativeqa": 0.72},
    ),
    PatternConfig(
        name="self_refine",
        description="Self-Refine: Agent critiques its own output and iterates until quality threshold met or max iterations reached.",
        system_prompt=(
            "You refine outputs iteratively.\n"
            "Iteration {iteration}: Produce or improve your response.\n"
            "After producing output, critique it:\n"
            "- Accuracy issues?\n"
            "- Missing information?\n"
            "- Clarity problems?\n"
            "If satisfied (score >= 4/5), output: FINAL: <response>\n"
            "Otherwise, improve and repeat."
        ),
        prompt_template="Task: {task}\n\nProduce your best response, then self-critique and refine.",
        tools_required=[],
        recommended_providers=["claude", "openai", "gcp"],
        requires_function_calling=False,
        example_tasks=["Writing improvement", "Code refactoring", "Report generation"],
        benchmark_scores={"code_quality": 0.75, "text_revision": 0.71},
    ),
    PatternConfig(
        name="planner_executor",
        description="Planner-Executor: Separate planning phase (decompose task) from execution phase (execute sub-tasks). Best for complex multi-step tasks.",
        system_prompt=(
            "Phase 1 — PLANNING:\n"
            "Decompose the task into 3-7 concrete sub-tasks. Number each step.\n"
            "Format: PLAN:\n1. <sub-task>\n2. <sub-task>...\n\n"
            "Phase 2 — EXECUTION:\n"
            "Execute each sub-task in order. Mark completed steps with ✓.\n"
            "Final Answer: <synthesized result from all sub-tasks>"
        ),
        prompt_template="Complex task: {task}\n\nBegin with the planning phase.",
        tools_required=["web_search", "code_execute"],
        recommended_providers=["claude", "openai"],
        requires_function_calling=True,
        example_tasks=["Multi-step research project", "Software architecture design", "Data pipeline creation"],
        benchmark_scores={"webgpt": 0.69, "plan_solve": 0.77},
    ),
    PatternConfig(
        name="supervisor_worker",
        description="Supervisor-Worker: Supervisor decomposes task, delegates to specialized workers, aggregates results. Best for parallelizable tasks.",
        system_prompt=(
            "You are the Supervisor agent.\n"
            "Your workers: {worker_list}\n"
            "Workflow:\n"
            "1. Decompose task into sub-tasks\n"
            "2. Assign each to the most appropriate worker\n"
            "3. Synthesize worker results\n"
            "4. Final Answer: <aggregated result>"
        ),
        prompt_template="Supervisor task: {task}\n\nDecompose and delegate.",
        tools_required=[],
        recommended_providers=["claude", "openai"],
        requires_function_calling=False,
        example_tasks=["Parallel research across domains", "Multi-source data aggregation"],
        benchmark_scores={"autogen_math": 0.89},
    ),
    PatternConfig(
        name="reflection_agent",
        description="Reflection Agent: Agent reflects on past run failures and stores verbal reinforcement for future improvement. Implements Reflexion.",
        system_prompt=(
            "You are a reflective agent.\n"
            "Past reflections:\n{past_reflections}\n\n"
            "Current task: Attempt, then reflect on your approach.\n"
            "After completing, write a reflection:\n"
            "REFLECTION: <what worked, what failed, what to do differently>"
        ),
        prompt_template="Task: {task}\n\nUse past reflections to improve your approach.",
        tools_required=["file_read", "file_write"],
        recommended_providers=["claude", "openai"],
        requires_function_calling=True,
        example_tasks=["Iterative code improvement", "Learning from failed attempts", "Self-improving agents"],
        benchmark_scores={"humaneval_reflexion": 0.91},
    ),
    PatternConfig(
        name="constitutional_agent",
        description="Constitutional Agent: Output checked against a set of principles/rules. Revise if any rule violated. Implements Constitutional AI.",
        system_prompt=(
            "You are a constitutional agent. Your output must comply with these principles:\n"
            "{constitution}\n\n"
            "After generating a response, check each principle:\n"
            "- Principle N: [PASS/FAIL] <reason>\n"
            "If any FAIL, revise the response. Output final compliant response as:\n"
            "APPROVED: <response>"
        ),
        prompt_template="Task: {task}",
        tools_required=[],
        recommended_providers=["claude", "openai"],
        requires_function_calling=False,
        example_tasks=["Safe content generation", "Policy-compliant output", "Guardrailed responses"],
        benchmark_scores={"harmlessness": 0.94, "helpfulness": 0.82},
    ),
    PatternConfig(
        name="research_agent",
        description="Research Agent: ArXiv/web search → read sources → synthesize → structured report. Best for research and knowledge synthesis tasks.",
        system_prompt=(
            "You are a research agent. Workflow:\n"
            "1. Search for relevant sources using web_search\n"
            "2. Read and extract key findings\n"
            "3. Synthesize into a structured report:\n"
            "   - Executive Summary\n"
            "   - Key Findings (with citations)\n"
            "   - Gaps & Open Questions\n"
            "   - Recommendations\n"
            "Final Answer: <complete research report>"
        ),
        prompt_template="Research task: {task}",
        tools_required=["web_search", "file_write"],
        recommended_providers=["claude", "openai"],
        requires_function_calling=True,
        example_tasks=["Survey AI agent frameworks", "Research MCP adoption", "Find SOTA models for a task"],
        benchmark_scores={"webgpt_factuality": 0.74},
    ),
]

_PATTERN_INDEX: dict[str, PatternConfig] = {p.name: p for p in PATTERNS}


class PatternLibrary:
    """15-pattern catalog with BGE-large semantic search and BGE-reranker reranking."""

    def __init__(self):
        self._faiss_index = None
        self._faiss_descriptions: list[str] = []
        self._faiss_names: list[str] = []

    def _ensure_index(self):
        if self._faiss_index is not None:
            return
        try:
            import sys
            from pathlib import Path
            ROOT = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(ROOT))
            from tools.hf_model_manager import HFModelManager
            import faiss
            import numpy as np

            mgr = HFModelManager.instance()
            texts = [f"{p.name}: {p.description}" for p in PATTERNS]
            embeddings = mgr.encode(texts, model_key="bge_large")
            embeddings = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings)
            dim = embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(embeddings)
            self._faiss_index = index
            self._faiss_descriptions = texts
            self._faiss_names = [p.name for p in PATTERNS]
        except Exception:
            self._faiss_index = None

    async def search(
        self,
        query: str,
        top_k: int = 3,
        provider_filter: Optional[str] = None,
    ) -> list[dict]:
        self._ensure_index()
        results = self._vector_search(query, top_k * 2)
        if not results:
            results = self._keyword_search(query, top_k * 2)

        # Filter by provider compatibility
        if provider_filter:
            results = [
                r for r in results
                if provider_filter in r.get("recommended_providers", [])
            ]

        # Rerank top results
        if len(results) > 1:
            results = self._rerank(query, results, top_k)
        else:
            results = results[:top_k]

        return results

    def _vector_search(self, query: str, top_k: int) -> list[dict]:
        if self._faiss_index is None:
            return []
        try:
            import sys
            from pathlib import Path
            ROOT = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(ROOT))
            from tools.hf_model_manager import HFModelManager
            import faiss
            import numpy as np

            mgr = HFModelManager.instance()
            q_emb = mgr.encode([query], model_key="bge_large")
            q_arr = np.array(q_emb, dtype=np.float32)
            faiss.normalize_L2(q_arr)
            scores, indices = self._faiss_index.search(q_arr, min(top_k, len(PATTERNS)))
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    continue
                name = self._faiss_names[idx]
                cfg = _PATTERN_INDEX.get(name)
                if cfg:
                    d = cfg.to_dict()
                    d["similarity"] = float(score)
                    results.append(d)
            return results
        except Exception:
            return []

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        query_lower = query.lower().replace("-", "_").replace(" ", "_")
        scored = []
        for p in PATTERNS:
            score = 0
            name_lower = p.name.lower().replace("-", "_")
            if query_lower in name_lower or name_lower in query_lower:
                score = 0.9
            elif any(w in p.description.lower() for w in query_lower.split("_") if len(w) > 3):
                score = 0.6
            else:
                score = 0.3
            d = p.to_dict()
            d["similarity"] = score
            scored.append(d)
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]

    def _rerank(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        try:
            import sys
            from pathlib import Path
            ROOT = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(ROOT))
            from tools.hf_model_manager import HFModelManager
            mgr = HFModelManager.instance()
            texts = [f"{c['name']}: {c['description']}" for c in candidates]
            scores = mgr.rerank(query, texts, model_key="bge_reranker")
            for c, s in zip(candidates, scores):
                c["rerank_score"] = float(s)
            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        except Exception:
            pass
        return candidates[:top_k]

    def list_all(self) -> list[dict]:
        return [p.to_dict() for p in PATTERNS]

    def get_by_name(self, name: str) -> Optional[dict]:
        cfg = _PATTERN_INDEX.get(name)
        if cfg:
            return cfg.to_dict()
        # Fuzzy match
        name_lower = name.lower()
        for pname, cfg in _PATTERN_INDEX.items():
            if name_lower in pname or pname in name_lower:
                return cfg.to_dict()
        return None
