# SECOND-KNOWLEDGE-BRAIN — agentcore-enhanced
**Domain:** Multi-Cloud LLM Agent Orchestration, MCP, Agent Evaluation, Multi-Agent Systems
**Self-Update Protocol:** Daily at 06:00 via `tools/knowledge_updater.py`
**Last Updated:** 2026-06-09

---

## Core Concepts & Frameworks

### Agent Architecture Primitives
- **ReAct (Reason + Act):** Yao et al. 2022. Interleaves chain-of-thought reasoning with grounded action execution. Outperforms CoT-only on HotpotQA, FEVER, ALFWorld.
- **Chain-of-Thought (CoT):** Wei et al. 2022. Prompting LLMs to emit intermediate reasoning steps improves accuracy on arithmetic, commonsense, and symbolic reasoning benchmarks.
- **Tree-of-Thought (ToT):** Yao et al. 2023. Generalizes CoT to a tree search over reasoning paths; backtracking enables better problem-solving on Game of 24, Mini Crosswords.
- **Self-Refine:** Madaan et al. 2023. Agent critiques its own output and iteratively refines. Effective for code generation, text revision, math reasoning.
- **Reflexion:** Shinn et al. 2023. Agent reflects on past failures using verbal reinforcement; stores reflections in episodic memory for future runs.

### Multi-Agent Coordination
- **AutoGen (Microsoft):** Conversational multi-agent framework. Agents communicate via structured messages. GroupChat enables parliament-style coordination.
- **CrewAI:** Role-based multi-agent orchestration. Agents have defined roles, goals, and backstories. Sequential and parallel task execution.
- **LangGraph:** Graph-based agent workflow orchestration. Nodes = agents; edges = transitions; state = shared memory. Supports cycles and conditional branching.
- **Supervisor-Worker:** One agent decomposes task → delegates to specialized workers → aggregates results. Common in hierarchical task networks.

### Model Context Protocol (MCP)
- **MCP Spec (Anthropic, 2024):** Open protocol for connecting LLM applications to data sources and tools. JSON-RPC 2.0 transport. Server exposes: tools, resources, prompts. Client connects and calls.
- **Key MCP operations:** `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`
- **MCP transports:** stdio (local subprocess), HTTP+SSE (network), WebSocket (bidirectional streaming)

### Agent Evaluation Frameworks
- **AgentBench (Liu et al. 2023):** 8-environment benchmark: OS, DB, KG, DHH, HH, Webarena, Mind2Web, AlfWorld. Evaluates: task success, efficiency, robustness.
- **HELM (Holistic Evaluation of Language Models, Stanford):** 42 scenarios, 7 metric groups: accuracy, calibration, robustness, fairness, bias, toxicity, efficiency.
- **MT-Bench:** 80 multi-turn questions, LLM-judged on a 1–10 scale. Tests: writing, roleplay, extraction, reasoning, math, coding, STEM.
- **WebArena:** 812 tasks across 4 realistic web environments. Tests autonomous web navigation.
- **ALFWorld:** Text-based embodied agent benchmark; 6 task types in simulated household environments.

---

## Key Research Papers

| Title | Authors | Year | Venue | Link | Key Finding | Relevance |
|-------|---------|------|-------|------|-------------|-----------|
| ReAct: Synergizing Reasoning and Acting in Language Models | Yao et al. | 2022 | ICLR 2023 | https://arxiv.org/abs/2210.03629 | ReAct outperforms CoT-only on HotpotQA (+9%) and ALFWorld (+34%); grounding reduces hallucination | Core pattern in pattern_library.py |
| Chain-of-Thought Prompting Elicits Reasoning in LLMs | Wei et al. | 2022 | NeurIPS 2022 | https://arxiv.org/abs/2201.11903 | CoT improves arithmetic +36pp on GSM8K with 540B model; emerges at ~100B params | CoT pattern baseline |
| Tree of Thoughts: Deliberate Problem Solving | Yao et al. | 2023 | NeurIPS 2023 | https://arxiv.org/abs/2305.10601 | ToT solves Game of 24 at 74% vs CoT 4%; backtracking is key | ToT pattern implementation |
| Self-Refine: Iterative Refinement with Self-Feedback | Madaan et al. | 2023 | NeurIPS 2023 | https://arxiv.org/abs/2303.17651 | Self-refine improves code generation +8 pass@1; diminishing returns after 3 iterations | Self-refine pattern; stopping criterion |
| Reflexion: Language Agents with Verbal Reinforcement | Shinn et al. | 2023 | NeurIPS 2023 | https://arxiv.org/abs/2303.11366 | Reflexion achieves 91% on HumanEval with episodic memory; outperforms GPT-4 zero-shot | Reflection agent pattern |
| AgentBench: Evaluating LLMs as Agents | Liu et al. | 2023 | ICLR 2024 | https://arxiv.org/abs/2308.03688 | GPT-4 leads; open-source models lag by 3–5× on task success; multi-task generalization poor | Benchmark design for eval_benchmark.py |
| AutoGen: Enabling Next-Gen LLM Applications | Wu et al. | 2023 | ICLR 2024 | https://arxiv.org/abs/2308.08155 | Conversational multi-agent achieves 89% on math problem solving; code exec crucial | Multi-agent parliament pattern |
| LLM Multi-Agent Systems: Challenges and Open Problems | Xu et al. | 2024 | arXiv | https://arxiv.org/abs/2402.03578 | Communication overhead; consensus failure; shared memory corruption; trust issues | Design decisions for multi-agent module |
| Gorilla: Large Language Model Connected with Massive APIs | Patil et al. | 2023 | arXiv | https://arxiv.org/abs/2305.15334 | Fine-tuned LLM reduces API hallucination from 26% to 1.3%; retrieval-augmented tool lookup | Tool-use specialist pattern |
| ToolBench: Facilitating Large Language Models for API Usage | Qin et al. | 2023 | ICLR 2024 | https://arxiv.org/abs/2307.16789 | 16,464 APIs; depth-first search with backtracking outperforms greedy tool selection | Tool orchestration strategy |
| HELM: Holistic Evaluation of Language Models | Liang et al. | 2022 | TMLR | https://arxiv.org/abs/2211.09110 | 42 scenarios; GPT-4 wins 16/42 but not all; efficiency and calibration often overlooked | Benchmark design; eval metrics |
| LLM-as-a-Judge: Scalable Evaluation for Open-Ended Tasks | Zheng et al. | 2023 | NeurIPS 2023 | https://arxiv.org/abs/2306.05685 | GPT-4 as judge: 85% agreement with humans; position bias exists; mitigation: swap positions | LLM-judged eval in eval_benchmark.py |
| Constitutional AI: Harmlessness from AI Feedback | Bai et al. | 2022 | arXiv | https://arxiv.org/abs/2212.08073 | RLAIF using AI-generated critiques; reduces harmful outputs by 3× without human labels | Constitutional agent pattern |
| Plan-and-Solve Prompting: Improving Zero-Shot CoT | Wang et al. | 2023 | ACL 2023 | https://arxiv.org/abs/2305.04091 | Explicit planning step before solving reduces math errors by 12pp vs vanilla CoT | Planner-executor pattern |
| Cognitive Architectures for Language Agents | Sumers et al. | 2024 | TMLR | https://arxiv.org/abs/2309.02427 | Survey of 10 cognitive architectures; memory (working/episodic/semantic) is critical differentiator | Memory-augmented pattern design |

---

## State-of-the-Art Models

| Task | Model | Benchmark Score | Score Date | Notes |
|------|-------|----------------|------------|-------|
| Text embedding (general) | `BAAI/bge-large-en-v1.5` | MTEB avg 64.23 | 2024-01 | #1 on MTEB English leaderboard at 1.3B params |
| Text embedding (fast) | `sentence-transformers/all-MiniLM-L6-v2` | MTEB avg 56.26 | 2023-12 | 5× faster than BGE-large; 80MB model |
| Code understanding | `Salesforce/codet5p-770m` | HumanEval 32.1 | 2023-09 | Best open encoder-decoder for code tasks |
| Cross-encoder reranking | `BAAI/bge-reranker-large` | BEIR avg +12 NDCG@10 | 2024-01 | Best open reranker; outperforms mono-T5 |
| LLM reasoning (primary) | `claude-opus-4-8` | MT-Bench 9.1 | 2025-04 | Best multi-step reasoning; 200K context |
| LLM reasoning (fast) | `claude-sonnet-4-6` | MT-Bench 8.9 | 2025-06 | 5× faster than Opus; used for eval judging |
| LLM multimodal | `gpt-4o` | MMMU 56.8 | 2024-05 | Best multimodal; preferred for vision tasks |
| Local LLM | `llama3:8b` (Ollama) | MT-Bench 7.1 | 2024-04 | Best offline option; fits 8GB VRAM |

---

## LLM Prompt Patterns

### ReAct System Prompt
```
You are an autonomous agent with access to tools.
Use the following format EXACTLY:

Thought: <reasoning about what to do>
Action: <tool_name>
Action Input: <JSON arguments for the tool>
Observation: <result returned by the tool>
... (Thought/Action/Action Input/Observation can repeat up to {max_steps} times)
Thought: I now know the final answer.
Final Answer: <comprehensive answer to the original question>

Available tools:
{tools_list}

Begin! Remember to think step by step.
```

### Multi-Agent Parliament Prompt
```
You are {agent_name}, a {role} in a multi-agent deliberation.

Task under discussion: {task}

Previous agent positions:
{positions_so_far}

Your responsibilities as {role}:
{role_description}

Provide your analysis in JSON:
{
  "position": "agree|disagree|abstain|propose_amendment",
  "confidence": 0.0-1.0,
  "key_arguments": ["arg1", "arg2", "arg3"],
  "proposed_amendment": "string or null"
}
```

### Benchmark Evaluation Prompt
```
Evaluate this agent's task completion. Return ONLY valid JSON.

Original task: {task_description}
Agent output: {agent_output}
Tool calls made: {tool_calls_summary}

Return:
{
  "task_success": 0.0-1.0,
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "quality_score": 0-5,
  "quality_reasoning": "what was good/bad"
}

Task success rubric: 1.0=fully complete, 0.7=mostly complete minor gaps, 0.4=partial, 0.1=attempted but failed, 0.0=no relevant output
Quality rubric: 5=expert-level, 4=good, 3=adequate, 2=poor, 1=very poor, 0=no output
```

### Pattern Synthesis Prompt
```
You are a research synthesizer specializing in AI agent architectures.

Recent papers on agent orchestration:
{paper_summaries}

Synthesize into a structured analysis covering:
1. Emerging patterns (not yet in mainstream frameworks)
2. Validated patterns (empirically confirmed to work)
3. Anti-patterns (approaches that consistently underperform)
4. Provider-specific recommendations (which patterns work best with which LLMs)
5. Open research questions

Format: JSON with keys: emerging_patterns, validated_patterns, anti_patterns, provider_recommendations, open_questions
Each pattern entry must include: name, description, evidence (paper citations), confidence (low/medium/high)
```

---

## Authoritative Data Sources

| Source | URL | Use |
|--------|-----|-----|
| ArXiv cs.AI | https://arxiv.org/list/cs.AI/recent | Daily agent papers |
| ArXiv cs.MA | https://arxiv.org/list/cs.MA/recent | Multi-agent systems |
| ArXiv cs.LG | https://arxiv.org/list/cs.LG/recent | LLM architecture papers |
| Semantic Scholar API | https://api.semanticscholar.org/graph/v1 | Citation data + paper search |
| Papers with Code | https://paperswithcode.com/sota/autonomous-agents | Agent benchmark leaderboards |
| AgentBench GitHub | https://github.com/THUDM/AgentBench | Benchmark dataset + results |
| MCP Specification | https://modelcontextprotocol.io/specification | Protocol reference |
| LangChain releases | https://github.com/langchain-ai/langchain/releases | Framework updates |
| LlamaIndex releases | https://github.com/run-llama/llama_index/releases | RAG/agent framework updates |
| CrewAI releases | https://github.com/crewAIInc/crewAI/releases | Multi-agent framework updates |
| AWS AgentCore | https://github.com/awslabs/agentcore-samples/releases | Upstream release tracking |
| Azure AI Agent Service | https://learn.microsoft.com/azure/ai-studio/concepts/agents | Azure patterns reference |

---

## Self-Update Protocol

```yaml
schedule: "0 6 * * *"  # Daily at 06:00
sources:
  arxiv:
    categories: [cs.AI, cs.MA, cs.LG, cs.SE]
    max_results_per_category: 50
    lookback_days: 7
  semantic_scholar:
    queries:
      - "multi-agent LLM orchestration"
      - "agent evaluation benchmark"
      - "model context protocol MCP"
      - "LLM tool use function calling"
      - "autonomous agent architecture"
    max_results_per_query: 20
    fields: [title, authors, year, abstract, citationCount, externalIds]
  github_releases:
    repos:
      - awslabs/agentcore-samples
      - langchain-ai/langchain
      - run-llama/llama_index
      - crewAIInc/crewAI
      - microsoft/autogen
  paperswithcode:
    leaderboards:
      - autonomous-agents
      - question-answering
      - code-generation
scoring:
  recency_weights:
    last_7_days: 1.0
    last_30_days: 0.7
    last_90_days: 0.4
    older: 0.1
  relevance_keywords:
    - agent
    - orchestration
    - multi-agent
    - tool use
    - function calling
    - MCP
    - evaluation
    - benchmark
    - ReAct
    - chain-of-thought
  top_n_per_source: 10
dedup:
  method: sha256_hash
  hash_fields: [doi, arxiv_id, url]
  storage: sqlite:knowledge_hashes_table
output:
  append_to: SECOND-KNOWLEDGE-BRAIN.md
  section: "## Knowledge Update Log"
  format: "| {date} | {title} | {authors} | {source} | {key_finding} |"
```

---

## Knowledge Update Log

| Date | Title | Authors | Source | Key Finding |
|------|-------|---------|--------|-------------|
| 2026-06-09 | Initial knowledge base seed — 15 foundational papers on agent architecture, MCP spec, evaluation frameworks | Various | Manual curation | Baseline knowledge base established. Daily crawl scheduled. |
