Roadmap: AI Agents — Beginner → Practitioner

# Roadmap: AI Agents — Beginner → Practitioner
0. Environment + Ops hygiene
 - Python 3.10+; UV package manager; Git; pre-commit; .env management; logging; simple tests.
 - GPU basics optional; Docker; Makefile; VS Code; Jupyter/Quarto.

1. Math + CS primitives (Optional)
 - Linear algebra (vectors, matrices, norms), calculus (gradients), probability (Bayes, entropy), optimization (SGD/Adam), complAssignmenty (big-O intuition).

2. Foundations of ML (Optional)
 - Supervised vs unsupervised; bias-variance; regularization; train/val/test; metrics; leakage.
 - Trees, ensembles; k-means; PCA; split strategies.

3. Foundations of DL (Optional)
 - Autograd; computation graphs; initialization; activation functions; normalization; overfitting control.

4. What is a Transformer (Optional)
 - Tokenization; embeddings; self-attention; positional encodings; encoder/decoder; masking; causal LM.
 - Inference vs training; kv-cache; context windows; throughput vs latency.

5. What is an LLM
 - Pretraining vs SFT vs RLHF/DPO; capabilities vs limitations; hallucinations; jailbreaks; safety.
 - Provider ecosystem; local vs hosted; quantization; LoRA/PEFT; latency/cost tradeoffs.

6. Call LLM API
 - REST/SDK; streaming; timeouts; retries; exponential backoff; idempotency keys; request logging.
- **Task 1**: Create (or sign in for) a Gemini (Google AI Studio) account and generate an API key. Write it into a `.env` file as `GEMINI_API_KEY=...` (never commit the key).
- **Task 2**: Use either curl, Python, or Node to send ONE prompt: "List 3 healthy breakfast ideas in JSON array form (just the dish names)." Save the raw response as `first_llm.json`.
- **Task 3**: Remove the JSON instruction and re-run—observe difference. Add a one-line note: "Structured instruction changed output shape." 
- - Done Signal: You have `first_llm.json` on disk AND you can explain how you authenticated.

7. Play with API parameters
 - temperature/top-p/top-k/repetition penalty; max tokens; stop sequences; system/instructions; JSON mode.
Important Parameters (write these into your notes):
- temperature (creativity / randomness)
- top_p (nucleus sampling breadth)
- max_output_tokens (length cap)
- presence_penalty (discourage repeating topics)
- frequency_penalty (discourage repeating exact tokens)
- stop_sequences (where to stop generation)
- response_format / JSON setting (structured output mode)
- system / safety settings (tone + blocked content)
- **Task 1**: Pick ONE prompt: "Give a 20-word motivational tip about consistent learning." Run with temperature=0 then 1; highlight changed words.
- **Task 2**: Same prompt with max_output_tokens=30 vs 10; observe truncation.
- **Task 3**: Add a stop sequence like `STOPHERE` at the end of your prompt and ensure model stops before it.
Mini Table: Record (run_id, temperature, max_tokens, notable difference).
- Done Signal: You can state what temperature and max_output_tokens did in your own words.

8. Create an agent
 - Core loop: perceive → decide → act → reflect → summarize.
 - State design: scratchpad, memory, tool results; deterministic scaffolding.
Core Pattern (write in notes):
- Receive user input
- Plan (decide if a tool or direct answer)
- Call tool(s)
- Draft answer
- Reflect / correct
- Return final answer
Concrete Example:
User Question: "What is 12% of 350 rounded to the nearest whole number?"
Tool (you implement): `percentage(amount: float, pct: float) -> float`
Manual Walk:
Plan: Need a calculation.
Tool Call: percentage(350, 12) = 42.0
Reflect: 42 already whole; final answer = 42.
You write a 10‑line pseudocode:
    ```
    read question
    if question has '%' pattern -> parse pct & base
    result = percentage(base, pct)
    answer_text = f"{round(result)}"
    return answer_text
    ```
- **Task 1**: Perform the above with TWO different inputs (change numbers).
- **Task 2**: Add a reflect step: if answer_text not digits -> raise fix.
- Done Signal: You can explain the 6 steps AND have a pseudocode block.

9. Create a custom system prompt
- Role, constraints, format; anti-patterns to avoid; deterministic scaffolds; few-shot style.
- **Task 1**: Draft a system prompt for your agent that clearly defines its role, constraints, and expected output format. Example: "You are a helpful assistant. Always answer in JSON."
- **Task 2**: Identify and write down at least two anti-patterns (e.g., vague instructions, ambiguous roles) and how to avoid them.
- **Task 3**: Add a few-shot example to your prompt (showing input and ideal output).
- Done Signal: You have a versioned prompt file with comments explaining each part and a changelog entry for any edits.

10. Dynamic system prompts
- Templates (Jinja/format strings); variable guards; context injection; safety filters; persona switching.
- **Task 1**: Refactor your system prompt into a template (Jinja or Python format string) with variables for user, task, and context.
- **Task 2**: Implement guards to check variable types/values before injecting into the prompt.
- **Task 3**: Add a safety filter that blocks unsafe or ambiguous context from being injected.
- **Task 4**: Add persona switching (e.g., "expert", "beginner") and show how the prompt changes.
- Done Signal: You have a prompt factory function/class with schema checks and at least two personas.

11. Structured responses
- JSON Schema; function arguments; Pydantic validation; repair loops; strict JSON.
- **Task 1**: Define a JSON schema for your agent’s output (e.g., {"answer": str, "sources": [str]}).
- **Task 2**: Use Pydantic (or similar) to validate the LLM output against the schema.
- **Task 3**: Implement a repair loop: if output is invalid, automatically retry with a clarifying instruction.
- **Task 4**: Test with at least three different prompts and show validation results.
- Done Signal: You have a validation script and logs showing retries and successful schema validation.

12. Tool calling with an agent
- Tool registry; input schema; deterministic tool selection; sandboxing; rate limits; error taxonomy.
- **Task 1**: Build a registry of at least three tools (search, math, file I/O) with input schemas.
- **Task 2**: Implement deterministic tool selection logic in your agent (e.g., based on keywords or intent).
- **Task 3**: Add retries, timeouts, and a circuit breaker for tool calls.
- **Task 4**: Log errors with taxonomy (e.g., timeout, invalid input, permission denied).
- Done Signal: You have a tool registry file, agent code with selection logic, and error logs for at least five tool calls.

13. Embeddings + Retrieval
- Tokenization vs embedding models; chunking; overlap; metadata; ANN indexes; re-ranking; citations.

- **Task 1**: Choose an embedding model (e.g., OpenAI, HuggingFace) and generate embeddings for a small document set.
- **Task 2**: Implement chunking with overlap and attach metadata (e.g., source, timestamp).
- **Task 3**: Build a simple ANN (approximate nearest neighbor) index for retrieval.
- **Task 4**: Add a re-ranking step and citation tracking for retrieved results.
- **Task 5**: Integrate retrieval into your agent’s answer flow (RAG).
- Done Signal: You have a script that retrieves and cites relevant chunks for at least three queries.
---
14. Memory for agents
- Short-term scratchpad vs episodic vs semantic memory; eviction; summarization; privacy.
- **Task 1**: Implement a memory layer for your agent with short-term (scratchpad), episodic (session), and semantic (knowledge) storage.
- **Task 2**: Add TTL (time-to-live) and compression for memory entries.
- **Task 3**: Implement retrieval hooks for agent to access memory during reasoning.
- **Task 4**: Add privacy controls (e.g., redact sensitive info before storage).
- Done Signal: You have a memory module with tests for eviction, compression, and privacy.

15. Evaluation + Observability
- Golden sets; rubric prompts; LLM-as-judge pitfalls; statistical tests; drift detection.
- Tracing (spans for model/tool), token metering, cost dashboards.
- **Task 1**: Create a golden set of test queries and expected answers for your agent.
- **Task 2**: Write rubric prompts for LLM-based evaluation and note pitfalls (e.g., bias, inconsistency).
- **Task 3**: Implement statistical tests (e.g., accuracy, precision, recall) and drift detection over time.
- **Task 4**: Add tracing for model/tool spans, token metering, and a simple cost dashboard.
- Done Signal: You have nightly eval logs, trace files, and a dashboard screenshot.

16. Safety + Security
- Prompt injection defenses; content filters; PII handling; policy checks; least privilege for tools.
- Sandboxes for code exec; SSRF/file exfiltration guards; audit logs.
- **Task 1**: Implement prompt injection detection and mitigation in your agent.
- **Task 2**: Add content filters for unsafe or unwanted outputs.
- **Task 3**: Integrate PII detection and redaction before logging or storage.
- **Task 4**: Enforce least privilege for tool access and sandbox code execution.
- **Task 5**: Add SSRF/file exfiltration guards and audit logging for all tool calls.
- Done Signal: You have a security checklist and logs showing blocked/filtered events.

17. Make an MCP tool call
- Function calling vs MCP; transport; schemas; capabilities; statelessness; errors.
- **Task 1**: Research and document the difference between standard function calling and MCP (Model Context Protocol).
- **Task 2**: Integrate MCP tool calling into your agent, using a provided schema and transport.
- **Task 3**: Log all streamed events and error cases during MCP calls.
- **Task 4**: Test with at least two MCP tools and document results.
- Done Signal: You have agent logs and a summary of MCP tool call outcomes.

18. Setup an MCP server and call it
- Define tools; auth; configuration; streaming; backpressure.
- **Task 1**: Set up a local MCP server wrapping a real system (e.g., Jira, Git).
- **Task 2**: Define at least two tools with schemas and authentication.
- **Task 3**: Implement streaming and backpressure handling in your agent-server communication.
- **Task 4**: Demonstrate end-to-end calls from agent to MCP server and back.
- Done Signal: You have a running MCP server, agent integration, and logs/screenshots of successful calls.

19. AG-UI
- Event protocol; rendering partials; tool progress; human-in-the-loop inputs; cancel/abort.
- **Task 1**: Design a UI that streams agent tokens and tool run events in real time.
- **Task 2**: Implement rendering of partial outputs and tool progress indicators.
- **Task 3**: Add human-in-the-loop controls for corrective input, cancel, or abort during agent runs.
- **Task 4**: Test with at least two agent tasks and document user interactions.
- Done Signal: You have a UI demo video or screenshots showing streaming and human input.

20. Multi-Agent Orchestration
- Topologies: manager-worker, planner-executor, debate/critique, router-specialist.
- Shared state; blackboard vs message bus; deadlock/loop prevention; credit assignment.
- **Task 1**: Implement a multi-agent pipeline (e.g., planner → retrieval-executor → reviewer) using RAG and MCP tools.
- **Task 2**: Design shared state (blackboard or message bus) for agent communication.
- **Task 3**: Add deadlock/loop prevention and credit assignment logic.
- **Task 4**: Test rollback on low confidence and document the workflow.
- Done Signal: You have a pipeline diagram and logs/screenshots of multi-agent runs.

21. Productionization
- Deployment: FastAPI/async, queueing, batching; serverless vs GPU workers; autoscaling; cold-start mitigation.
- Caching: prompt/response cache; vector cache; TTL and invalidation.
- Versioning: prompts, tools, datasets; canary; feature flags; rollout/rollback.
- **Task 1**: Deploy your agent system using FastAPI (or similar), with async endpoints and queueing.
- **Task 2**: Implement batching, autoscaling, and cold-start mitigation strategies.
- **Task 3**: Add caching layers (prompt/response, vector) with TTL and invalidation logic.
- **Task 4**: Set up versioning for prompts, tools, and datasets; implement canary releases and feature flags.
- Done Signal: You have deployment scripts, cache stats, and a changelog for versioned releases.
---
22. Cost/Latency Engineering
- Batching, kv-cache reuse, compress context, selective tool use, model routing, quantized locals for cheap steps.
- **Task 1**: Profile your system to identify cost and latency bottlenecks.
- **Task 2**: Implement batching, kv-cache reuse, and context compression.
- **Task 3**: Add selective tool use and model routing for cheap steps.
- **Task 4**: Test with a baseline and show a 30% reduction in p95 latency and cost.
- Done Signal: You have before/after metrics and a summary of optimizations.
---
23. Capstone
- Deliver a real agent with: dynamic prompts, structured output, tools, RAG, MCP integration, AG-UI, evals, safety, tracing, deployment.
- **Task 1**: Assemble all previous modules into a single repo: agent, tools, RAG, MCP, UI, evals, safety, tracing, deployment.
- **Task 2**: Record a demo video showing the agent in action across multiple tasks.
- **Task 3**: Write an eval report and ops dashboard summarizing performance, cost, and safety.
- Done Signal: You have a public repo, demo video, eval report, and dashboard screenshot.