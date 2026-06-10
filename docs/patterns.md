# Agent Patterns Reference

This document provides detailed reference information for all 15 agent patterns in agentcore-enhanced.

## Pattern Overview

| Pattern | Category | Complexity | Tools Required | Function Calling |
|---------|----------|------------|----------------|-----------------|
| react | Reasoning | Medium | web_search, code_execute, file_read | No |
| chain_of_thought | Reasoning | Low | - | No |
| tree_of_thought | Reasoning | High | - | No |
| multi_agent_parliament | Multi-Agent | High | web_search | No |
| critic_actor | Refinement | Medium | - | No |
| memory_augmented | Memory | High | file_read, file_write | Yes |
| tool_use_specialist | Tools | Medium | web_search, code_execute, files | Yes |
| code_agent | Code | Medium | code_execute, files | Yes |
| document_analyst | RAG | Medium | file_read | No |
| self_refine | Refinement | Low | - | No |
| planner_executor | Planning | High | web_search, code_execute | Yes |
| supervisor_worker | Multi-Agent | High | - | No |
| reflection_agent | Learning | High | file_read, file_write | Yes |
| constitutional_agent | Safety | Medium | - | No |
| research_agent | Research | High | web_search, file_write | Yes |

## ReAct (Reason + Act)

**Best for**: Research, fact-finding, multi-step reasoning with external data

**Description**: ReAct alternates between Thought (reasoning), Action (tool use), and Observation (tool result) to ground reasoning in actual tool outputs rather than hallucinations.

**System Prompt**:
```
You are an autonomous agent. Think step by step using this exact format:

Thought: <reasoning about what to do next>
Action: <tool_name>
Action Input: <JSON arguments>
Observation: <tool result>
...(repeat Thought/Action/Action Input/Observation as needed)
Thought: I now know the final answer.
Final Answer: <comprehensive answer>
```

**Example Usage**:
```bash
agentcore run --pattern react \
  --task "What is the population of Tokyo and what percentage of Japan's total population is it?"
```

**Benchmark Scores**: HotpotQA (0.71), ALFWorld (0.86), FEVER (0.78)

**Recommended Providers**: Claude, OpenAI, Azure

---

## Chain-of-Thought (CoT)

**Best for**: Math problems, logical reasoning, step-by-step analysis

**Description**: CoT requires the model to show its reasoning explicitly before producing a final answer. No tools required.

**System Prompt**:
```
Think step by step. Show your reasoning explicitly before giving the final answer.
```

**Example Usage**:
```bash
agentcore run --pattern chain_of_thought \
  --task "Solve: If 3x + 7 = 22, what is x?"
```

**Benchmark Scores**: GSM8K (0.95), Math (0.68)

**Recommended Providers**: Claude, OpenAI, GCP, Ollama

---

## Tree-of-Thought (ToT)

**Best for**: Puzzles, games, strategic planning, problems with multiple solution paths

**Description**: ToT explores multiple reasoning branches in parallel, evaluates each, backtracks if stuck, and selects the best path.

**System Prompt**:
```
Explore multiple reasoning paths for this task. For each path:
1. Generate 3 candidate next steps
2. Evaluate each step (promising/not promising)
3. Continue the most promising path
4. Backtrack if stuck
Final Answer: <best solution found>
```

**Example Usage**:
```bash
agentcore run --pattern tree_of_thought \
  --task "Solve the Game of 24: Given numbers 3, 8, 8, 14, combine them with + - * / to reach 24"
```

**Benchmark Scores**: Game of 24 (0.74), Mini Crossword (0.60)

**Recommended Providers**: Claude, OpenAI

---

## Multi-Agent Parliament

**Best for**: High-stakes decisions, policy evaluation, architectural trade-offs

**Description**: Multiple specialized agents (optimist, pessimist, risk-analyst, etc.) debate and vote. Moderator synthesizes final position.

**System Prompt**:
```
You are {agent_name}, a {role} in a multi-agent deliberation panel.

Task: {task}

Previous positions:
{positions_so_far}

Provide your analysis as JSON:
{
  "position": "agree|disagree|abstain|propose_amendment",
  "confidence": 0.0-1.0,
  "key_arguments": [...],
  "proposed_amendment": null
}
```

**Example Usage**:
```bash
agentcore run --pattern multi_agent_parliament \
  --task "Should our company adopt microservices architecture or stay with monolith?"
```

**Benchmark Scores**: Decision Quality (0.82)

**Recommended Providers**: Claude, OpenAI

---

## Critic-Actor

**Best for**: Code review, writing improvement, iterative refinement

**Description**: Actor drafts output, Critic identifies weaknesses and suggests improvements, iterate until quality gate passes.

**System Prompt**:
```
You are alternating between Actor and Critic roles.

Actor turn: Produce your best response to the task.
Critic turn: Identify specific weaknesses and suggest improvements.
Repeat until Critic approves or max iterations reached.

Final Answer: <approved response>
```

**Example Usage**:
```bash
agentcore run --pattern critic_actor \
  --task "Review and improve this Python function for performance and readability"
```

**Benchmark Scores**: Output Quality (0.79)

**Recommended Providers**: Claude, OpenAI

---

## Memory-Augmented

**Best for**: Long-running projects, personal assistant, knowledge base building

**Description**: Vector store retrieval injects relevant past context into every prompt. Agent builds persistent context across interactions.

**System Prompt**:
```
You are an agent with access to a persistent memory store.

Relevant memories retrieved for this task:
{retrieved_memories}

Use these memories to inform your response. Update your memory with new insights.
```

**Example Usage**:
```bash
agentcore run --pattern memory_augmented \
  --task "Continue working on the Python data analysis script from yesterday"
```

**Benchmark Scores**: Multi-turn Coherence (0.85)

**Recommended Providers**: Claude, OpenAI, Azure

**Requires**: Function calling support

---

## Tool-Use Specialist

**Best for**: Data collection, API integration, information lookup

**Description**: Agent optimized for rich tool libraries. Uses structured function calling for precise tool invocation and parameter passing.

**System Prompt**:
```
You are a tool-use specialist. You have access to a comprehensive set of tools.

Always use tools to gather information rather than relying on memory.

Available tools:
{tools_list}
```

**Example Usage**:
```bash
agentcore run --pattern tool_use_specialist \
  --task "Find the current stock price of AAPL, fetch company news, and summarize sentiment"
```

**Benchmark Scores**: ToolBench (0.67), Gorilla (0.78)

**Recommended Providers**: Claude, OpenAI, Azure

**Requires**: Function calling support

---

## Code Agent

**Best for**: Programming tasks, data analysis, debugging

**Description**: Writes Python code, executes in sandboxed subprocess, debugs errors, iterates until solution works.

**System Prompt**:
```
You are an expert Python programmer. Your workflow:
1. Write Python code to solve the task
2. Execute it using code_execute tool
3. Debug any errors and re-execute
4. Return the final working code and output

Always execute code before reporting results.
```

**Example Usage**:
```bash
agentcore run --pattern code_agent \
  --task "Write a function to calculate Fibonacci numbers efficiently and test it"
```

**Benchmark Scores**: HumanEval (0.82), MBPP (0.79)

**Recommended Providers**: Claude, OpenAI

**Requires**: Function calling support

---

## Document Analyst

**Best for**: Long document Q&A, summarization, information extraction

**Description**: Chunks documents, embeds with sentence-transformers, performs RAG retrieval for relevant sections, cites sources.

**System Prompt**:
```
You are a document analysis expert.

Retrieved document sections:
{retrieved_sections}

Answer based on the document content. Cite section numbers.
```

**Example Usage**:
```bash
agentcore run --pattern document_analyst \
  --task "Summarize the key findings from the uploaded research paper"
```

**Benchmark Scores**: QASPER (0.58), NarrativeQA (0.72)

**Recommended Providers**: Claude, OpenAI

---

## Self-Refine

**Best for**: Writing improvement, code quality, report generation

**Description**: Agent critiques its own output, identifies issues, iterates until quality threshold met or max iterations.

**System Prompt**:
```
You refine outputs iteratively.

Iteration {iteration}: Produce or improve your response.

After producing output, critique it:
- Accuracy issues?
- Missing information?
- Clarity problems?

If satisfied (score >= 4/5), output: FINAL: <response>
Otherwise, improve and repeat.
```

**Example Usage**:
```bash
agentcore run --pattern self_refine \
  --task "Write a professional email to a client about a project delay"
```

**Benchmark Scores**: Code Quality (0.75), Text Revision (0.71)

**Recommended Providers**: Claude, OpenAI, GCP

---

## Planner-Executor

**Best for**: Multi-step projects, complex workflows, task decomposition

**Description**: Separate planning phase (decompose into 3-7 sub-tasks) from execution phase (execute in order with checkpoint verification).

**System Prompt**:
```
Phase 1 — PLANNING:
Decompose the task into 3-7 concrete sub-tasks. Number each step.
Format: PLAN:
1. <sub-task>
2. <sub-task>...

Phase 2 — EXECUTION:
Execute each sub-task in order. Mark completed steps with ✓.
Final Answer: <synthesized result from all sub-tasks>
```

**Example Usage**:
```bash
agentcore run --pattern planner_executor \
  --task "Research and summarize best practices for API authentication in 2025"
```

**Benchmark Scores**: WebGPT (0.69), Plan & Solve (0.77)

**Recommended Providers**: Claude, OpenAI

**Requires**: Function calling support

---

## Supervisor-Worker

**Best for**: Parallel research, multi-source aggregation, specialized sub-tasks

**Description**: Supervisor decomposes task, delegates to specialized workers (coder, researcher, analyst), aggregates results.

**System Prompt**:
```
You are the Supervisor agent.

Your workers: {worker_list}

Workflow:
1. Decompose task into sub-tasks
2. Assign each to the most appropriate worker
3. Synthesize worker results
4. Final Answer: <aggregated result>
```

**Example Usage**:
```bash
agentcore run --pattern supervisor_worker \
  --task "Research and compare pricing strategies across 3 competitors"
```

**Benchmark Scores**: AutoGen Math (0.89)

**Recommended Providers**: Claude, OpenAI

---

## Reflection Agent

**Best for**: Iterative improvement, learning from failure, self-debugging

**Description**: Agent reflects on past run failures, stores verbal reinforcement for future improvement. Implements Reflexion pattern.

**System Prompt**:
```
You are a reflective agent.

Past reflections:
{past_reflections}

Current task: Attempt, then reflect on your approach.

After completing, write a reflection:
REFLECTION: <what worked, what failed, what to do differently>
```

**Example Usage**:
```bash
agentcore run --pattern reflection_agent \
  --task "Debug why the previous code attempt failed and fix it"
```

**Benchmark Scores**: HumanEval+Reflexion (0.91)

**Recommended Providers**: Claude, OpenAI

**Requires**: Function calling support

---

## Constitutional Agent

**Best for**: Safe content generation, policy-compliant output, guardrailed responses

**Description**: Output checked against a set of principles/rules. Revise if any rule violated. Implements Constitutional AI principles.

**System Prompt**:
```
You are a constitutional agent. Your output must comply with these principles:
{constitution}

After generating a response, check each principle:
- Principle N: [PASS/FAIL] <reason>

If any FAIL, revise the response.

Output final compliant response as:
APPROVED: <response>
```

**Example Usage**:
```bash
agentcore run --pattern constitutional_agent \
  --task "Explain how to hack a WiFi network (should refuse)"
```

**Benchmark Scores**: Harmlessness (0.94), Helpfulness (0.82)

**Recommended Providers**: Claude, OpenAI

---

## Research Agent

**Best for**: Academic research, knowledge synthesis, literature review

**Description**: ArXiv/web search → read sources → synthesize → structured report with citations. Optimized for research workflows.

**System Prompt**:
```
You are a research agent. Workflow:
1. Search for relevant sources using web_search
2. Read and extract key findings
3. Synthesize into a structured report:
   - Executive Summary
   - Key Findings (with citations)
   - Gaps & Open Questions
   - Recommendations

Final Answer: <complete research report>
```

**Example Usage**:
```bash
agentcore run --pattern research_agent \
  --task "Survey recent advances in multi-agent reinforcement learning for robotics"
```

**Benchmark Scores**: WebGPT Factuality (0.74)

**Recommended Providers**: Claude, OpenAI

**Requires**: Function calling support

---

## Pattern Selection Guide

### By Task Type

| Task | Recommended Pattern |
|------|---------------------|
| Simple reasoning | chain_of_thought |
| Multi-step with tools | react |
| Code writing/debugging | code_agent |
| Research | research_agent |
| Writing improvement | self_refine |
| Complex project | planner_executor |
| Quality critical | critic_actor |
| Safety critical | constitutional_agent |

### By Tool Availability

| Tools Available | Patterns |
|----------------|----------|
| No tools | chain_of_thought, tree_of_thought, self_refine, multi_agent_parliament |
| Web search only | react, research_agent |
| Code execution | code_agent, planner_executor, tool_use_specialist |
| File I/O | memory_augmented, document_analyst, reflection_agent |
| All tools | tool_use_specialist, code_agent |

### By Provider Support

| Provider | Best Patterns |
|----------|---------------|
| Claude | All patterns (best tool calling) |
| OpenAI | All patterns |
| Azure | All patterns with tools |
| GCP | chain_of_thought, tree_of_thought, self_refine |
| Ollama | chain_of_thought, self_refine (no tool calling) |
| vLLM | chain_of_thought, self_refine (no tool calling) |

For more examples, see the [examples/](../examples/) directory.
