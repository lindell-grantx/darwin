# Darwin — Literature & References

Compiled 2026-05-01 during hackathon brainstorm session.

---

## Theme 1: Prolonged Coordination

### Key Papers

**"Beyond pass@1" (arXiv 2603.29231, March 2026)**
Finding: Memory scaffolds universally HURT long-horizon reliability. Current persistence mechanisms introduce more noise than signal. Counterintuitive result — suggests the field's default approach (persist everything) is wrong.

**"The Long-Horizon Task Mirage" (arXiv 2604.11978, April 2026)**
Finding: Model scaling alone won't fix the dominant failure mechanisms in long-horizon tasks. The failures are structural, not capability-limited.

**"Sophia" (arXiv 2512.18202)**
Proposes a "System 3" meta-cognitive persistence layer — a third system beyond Kahneman's System 1/2 that handles long-term reasoning continuity.

**"Engram" (arXiv 2603.21321)**
Decouples long-horizon exploration via Archive + Research Digest handoffs. Closest thing to reasoning state persistence but still lossy.

**"From Static Templates to Dynamic Runtime Graphs" (arXiv 2603.22386, March 2026)**
Surveys mid-flight task modification approaches: Task-Decoupled Planning (confines replanning to active sub-tasks) and Graph Harness (immutable versioned plans with escalation). Both academic only.

### Industry Data

**VentureBeat (April 2026): "Context Decay, Orchestration Drift, and the Rise of Silent Failures"**
Reports ~2% accuracy degradation per reasoning step, compounding to ~40% failure rates by step 20. Systems show green on infra metrics while reasoning over stale data.

**Wire Blog: "Agent Drift: Why Long-Running AI Agents Lose the Plot"**
Taxonomizes six drift mechanisms: goal drift, context drift, role drift, tool-use drift, hallucination cascade, plan decay. Plan decay is the worst — plan is followed but became obsolete after earlier step results.

**Gemini 2.5 Pro at 1M tokens (dbreunig.com, June 2025)**
Bigger context windows make drift worse — starts repeating historical actions instead of reasoning.

### Framework Limitations

| Framework | Persists | Doesn't Persist | Key Limitation |
|-----------|----------|-----------------|----------------|
| LangGraph + MongoDB | Graph state, messages, tool results | Reasoning trace, plan versioning | Resumes only at super-step boundaries; checkpoint bloat |
| Letta/MemGPT | Core memory blocks, archival memory | Cross-agent reasoning coherence | High lock-in (2-6 week switch cost); blocking memory ops |
| Temporal | Full event history, deterministic replay | LLM reasoning state (treats LLM as opaque) | Best for durable orchestration, not cognitive persistence |
| AutoGen | Conversation history (in-memory) | Anything durable | Shifted to maintenance mode by Microsoft |
| CrewAI | Latest crew run replay | Reasoning traces, multi-run history | Silent failures; agents hallucinate tool use |

### Hackathon Intel

MongoDB Agentic Orchestration Hackathon (SF, January 2026): 350 attendees, 109 submissions across four themes including "Prolonged Coordination." Winners tackled healthcare pricing, database migration, smart-glasses orchestration. **None solved reasoning persistence.** Stack: MongoDB Atlas + Voyage AI + Fireworks AI + Claude.

---

## Theme 2: Multi-Agent Collaboration

### Key Papers

**"Why Do Multiagent Systems Fail?" (ICLR 2025, OpenReview)**
Analyzed 150+ tasks across 5 frameworks. Found 18 failure modes. Top category: specification ambiguity and misalignment. Decomposition errors are structural, not fixable by better prompts.

**"Theater of Mind" (arXiv 2604.08206, April 2026)**
Applies Global Workspace Theory from cognitive science to LLM agents. Replaces passive shared memory with an active event-driven broadcasting hub where agents compete for "consciousness" — the right to broadcast their results to all other agents. Brand new, genuinely novel. Maps directly to MongoDB change streams.

**LbMAS: Blackboard Multi-Agent System (arXiv 2507.01701, Han & Zhang)**
Replaces direct agent communication with shared blackboard. Achieved 13-57% improvement over master-slave and RAG baselines. Includes conflict-resolver and cleaner agents.

**ProtocolBench (arXiv 2510.17149)**
Benchmarks agent communication protocols across task success, latency, message overhead, robustness. Introduces ProtocolRouter for dynamic protocol selection.

**"Agent Discovery in Internet of Agents" (arXiv 2511.19113)**
Proposes semantic profiling via language model embeddings for agent capability discovery. Research prototype only.

**TokenDance (arXiv 2604.03143)**
Tackles multi-agent context sharing at the KV cache level. Achieves 2.7x more concurrent agents but requires inference infrastructure changes.

**ACON (arXiv 2510.00615)**
Adaptive compression reduces peak tokens 26-54%. Does NOT address the multi-agent variant (what to share with whom).

### Industry Data

**Lanham's 2026 production retrospective (Medium)**
Only orchestrated pipelines survived to production. Free-form agent loops remain confined to research.

**Credit assignment**: No framework implements principled credit assignment. Han et al. survey (arXiv 2402.03578) flags this explicitly.

### Untapped Mechanisms from Other Fields

| Mechanism | Source Field | Application to LLM Agents | Status |
|-----------|-------------|---------------------------|--------|
| Market-based task allocation | Economics (auction theory) | Agents bid on tasks based on self-assessed competence and cost | Well-studied in classical MAS, absent from LLM frameworks |
| Stigmergy | Biology (ant colonies) | Indirect coordination through environment modification; maps to blackboard pattern | Not formalized for LLM agents |
| Shapley value credit assignment | Cooperative game theory | Principled blame/credit attribution across agents | Computationally expensive, unattempted |
| Global Workspace Theory | Cognitive science | Active broadcasting hub for agent coordination | "Theater of Mind" paper (April 2026) — brand new |
| Byzantine fault tolerance | Distributed systems | Handling faulty/malicious agents in multi-agent systems | Underexplored (flagged in OpenReview research) |

### Tools & Frameworks

- AWS Strands "Arbiter Pattern": blackboard-inspired architecture
- `blackboard-core` Python SDK on PyPI
- MongoDB Store for LangGraph: checkpointing + long-term memory
- Hugging Face multi-agent tutorial: smolagents + MongoDB for order management

---

## Theme 3: Adaptive Retrieval

### Key Papers

**Adaptive-RAG (KAIST, 2024, arXiv 2501.09136)**
Routes queries by complexity. Static classifier at invocation time — never learns from outcomes. The closest to strategy selection but fundamentally non-adaptive.

**CRAG — Corrective RAG (arXiv 2401.15884)**
Lightweight evaluator (0.77B params) classifies retrieved docs as Correct/Incorrect/Ambiguous. Triggers web search fallback. Plug-and-play. Does not learn.

**Self-RAG (GitHub: AkariAsai/self-rag)**
Trains reflection tokens into the LM itself for on-demand retrieval. 7B model beats ChatGPT on open-domain QA. Novel but fixed behavior — no evolution.

**FLARE — Forward-Looking Active Retrieval**
Triggers retrieval when generation confidence drops. Reactive, not proactive. No learning.

**RAG-Fusion (arXiv 2402.03367)**
Multi-query generation + Reciprocal Rank Fusion. Simple, effective, no learning.

**RankRAG**
Instruction-fine-tuned LLM does both ranking and generation. Llama3-RankRAG matches GPT-4 on biomedical benchmarks without domain tuning.

**AIR-RAG (ScienceDirect, December 2025)**
Adaptive iterative retrieval with feedback between ranking and refinement across iterations. Closest to a feedback loop but within a single query, not across queries.

**FAIR-RAG (arXiv 2510.22344, October 2025)**
Addresses evidence gaps iteratively. Does NOT adapt chunk granularity.

**TG-RAG (arXiv 2510.13590)**
Temporal graph RAG with bi-level temporal representation and time-scoped evidence retrieval. Only paper directly addressing temporal-aware retrieval.

**Noise-Aware Verbal Confidence Calibration (arXiv 2601.11004, January 2025)**
First paper to explicitly model retrieval noise types for confidence estimation. Early-stage.

**SoK: Agentic RAG (arXiv 2603.07379, March 2026)**
Formalizes agentic retrieval as a POMDP. No implementation. Sets the theoretical frame.

**RobustRAG (Xiang et al., 2024) and ReliabilityRAG (Shen et al., 2025)**
Adversarial hardening via isolated evidence aggregation with certifiable robustness bounds. Taxonomy in arXiv 2604.08304.

### Evolutionary Computation (the gap Darwin fills)

**IR Using Evolutionary Algorithms (Springer, 2025)**
Evolutionary approaches exist for classical information retrieval. Have NOT been applied to modern RAG pipelines.

**NSCO Framework (Swarm and Evolutionary Computation journal, 2025)**
Integrates neural networks with evolutionary optimization. Could serve as template for evolving retrieval strategies. Nobody has connected it to RAG.

**Key gap: No paper treats a retrieval configuration (chunking params, embedding model, query transformation, reranking weights, source routing) as a mutable genome subject to selection pressure from downstream answer quality.** This is Darwin's contribution.

### Hackathon Intel

No standout adaptive-RAG hackathon projects found. Closest open-source demos:
- NirDiamant/RAG_Techniques (notebook collection, corrective/self-reflective/adaptive)
- Taha0229/self-reflective-RAG (multi-source with query rewriting loop)
Neither implements strategy evolution or learning from outcomes.

---

## MongoDB 2026 Capabilities

### Voyage AI Acquisition & Integration

MongoDB acquired Voyage AI in February 2025. Voyage 4 model family launched at MongoDB.local SF (January 2026):
- **voyage-4**: general purpose
- **voyage-4-large**: maximum accuracy
- **voyage-4-lite**: low latency
- **voyage-4-nano**: open-weights, local development
- **voyage-multimodal-3.5**: interleaved text, images, video, PDFs

MongoDB claims Voyage 4 outperforms Gemini and Cohere on the RTEB retrieval leaderboard.

**Automated Embedding**: vector embeddings generated automatically on ingest, update, or query. No external embedding API calls. This is the core differentiator — embeddings are native to the database.

**Atlas Embedding and Reranking API**: public preview. Handles embedding + reranking in a single API surface.

### Atlas Vector Search (2025-2026)

- Scalar and binary quantization GA (April 2025): 4x and 32x memory reduction
- Binary quantization with automatic rescoring using full-fidelity vectors
- Hybrid search (vector + keyword with unified results)
- Extended to Community Edition and Enterprise Server (September 2025, public preview)
- Pre-filtering on metadata fields within the same query framework

### MongoDB for Agent State

MongoDB positioning: **"Converged datastore for agentic AI"** — documents + vectors + streams + ACID in one system.

- MongoDB Store for LangGraph: long-term memory (cross-session) + checkpointing
- Atlas Stream Processing: triggers agent activation on data changes (event-driven)
- ACID transactions: protect agent state transitions
- MCP Server: agents interact with MongoDB directly via Model Context Protocol

**"Why Multi-Agent Systems Need Memory Engineering" (MongoDB blog)**: identifies four failure modes — context poisoning, distraction, confusion, clash. Positions MongoDB as the persistent memory layer.

### mongodb/agent-skills (GitHub)

Pre-built skill files for coding agents (Claude Code, Cursor, Gemini CLI, Codex, VS Code). Skills cover MCP server setup, connection optimization, schema design, indexing strategies, query patterns. Motivation: coding agents default to relational thinking that misuses MongoDB.

### Pete Johnson (Judge — Field CTO, AI)

Recent output centers on:
1. **Five embedding decisions**: chunking, similarity function, dimensions, quantization, reranking (MongoDB.local SF, January 2026)
2. **Human-in-the-loop AI**: AI as collaborator not job-killer (Stack Overflow podcast)
3. **Practical AI adoption**: cloud independence, embeddings moving the productivity needle
4. **Enterprise agentic AI**: moderated panel with Ford, MLS, Dow Jones

His five embedding decisions ARE the retrieval genome parameters. When he sees Darwin, he should see his own talk turned into a living system.

### Competitive Positioning vs. Alternatives

| Competitor | MongoDB's Counter |
|------------|-------------------|
| Postgres + pgvector | Converged platform (vectors + documents + streams + ACID) vs. bolting pgvector onto relational model |
| Pinecone | No separate vector DB needed; operational data and embeddings live together, eliminating sync. Pinecone counters with "Integrated Inference" and superior 100M+ scale. |
| Weaviate | Same converged-platform argument. MongoDB has broader adoption for operational workloads. |

MongoDB's unique angle: **the full loop** — ingest data, auto-embed, vector search, store agent memory, trigger agent actions via streams, all without leaving Atlas.

---

## Key Quotes for Pitch Framing

> "No production system feeds retrieval quality back into strategy selection in a closed loop." — confirmed across all surveyed frameworks

> "Memory scaffolds universally hurt long-horizon reliability." — Beyond pass@1 (arXiv 2603.29231)

> "Only orchestrated pipelines survived to production." — Lanham's 2026 retrospective

> "Specification ambiguity and misalignment" is the #1 multi-agent failure mode — ICLR 2025

> "~2% accuracy degradation per reasoning step, compounding to ~40% failure rates by step 20" — VentureBeat, April 2026
