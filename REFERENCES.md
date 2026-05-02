# Darwin — Papers, URLs, and Implementation References

Compiled 2026-05-01. Organized by research dimension.

---

## 1. Evolutionary Computation for IR and RAG

### Core Gap (Darwin's novelty claim)
Population-based evolutionary computation applied to modern RAG pipeline optimization is a genuinely sparse niche. Most "evolutionary RAG" papers use "evolution" metaphorically (feedback-driven adaptation) rather than implementing population-based search with crossover, mutation, and fitness selection.

### Classical IR + Evolutionary Algorithms

- **Evolutionary Algorithms Approach for Search Based on Semantic Document Similarity** (2025)
  [https://arxiv.org/html/2502.19437v1](https://arxiv.org/html/2502.19437v1)
  GA and Differential Evolution with Universal Sentence Encoder embeddings outperform traditional ranking on SQuAD.

- **Information Retrieval in Big Data Using Evolutionary Computation: A Survey** (2016)
  [https://www.researchgate.net/publication/312560114](https://www.researchgate.net/publication/312560114)
  Broad survey: GA, Differential Evolution, PSO, ACO applied to IR tasks.

- **An Efficient Information Retrieval System Using Evolutionary Algorithms** (2022, MDPI)
  [https://www.mdpi.com/2673-8732/2/4/34](https://www.mdpi.com/2673-8732/2/4/34)
  Modified GA with culture-algorithm integration for document indexing.

- **Information Retrieval Using Evolutionary Algorithms** (Springer, ICDSM 2024 proceedings, pub. 2026)
  [https://link.springer.com/chapter/10.1007/978-981-95-1320-8_18](https://link.springer.com/chapter/10.1007/978-981-95-1320-8_18)
  Compares Modified GA, Cultural Algorithm, ACO, PSO, Bee Swarm on WebKB dataset.

### Genetic Programming for Ranking Functions

- **ARRANGER: Ranking Function Discovery by GP for Robust Retrieval** (TREC)
  [https://trec.nist.gov/pubs/trec12/papers/vatech.robust.pdf](https://trec.nist.gov/pubs/trec12/papers/vatech.robust.pdf)
  GP discovers ranking functions that replace BM25; 16% improvement in average precision.

- **RankGP: Learning to Rank for IR Using Genetic Programming**
  [https://www.researchgate.net/publication/228351691](https://www.researchgate.net/publication/228351691)
  Evolves ranking functions from content, structure, and query-independent features; competitive with RankSVM.

- **Generic Ranking Function Discovery Framework by GP** (Fan, Gordon, Pathak)
  [https://www.sciencedirect.com/science/article/abs/pii/S016792360900089X](https://www.sciencedirect.com/science/article/abs/pii/S016792360900089X)
  Two-stage: GP discovers ranking functions, then GA optimizes score combination.

- **Multi-Objective GP for Topic-Based Search with Diversity and Recall** (PeerJ CS, 2023)
  [https://peerj.com/articles/cs-1710/](https://peerj.com/articles/cs-1710/)
  Multi-objective GP generates query populations maximizing precision, recall, and diversity.

### Multi-Objective Evolutionary Optimization

- **Topic Relevance and Diversity in IR: A Multi-Objective EA Approach** (Applied Soft Computing, 2018)
  [https://www.sciencedirect.com/science/article/abs/pii/S1568494617306798](https://www.sciencedirect.com/science/article/abs/pii/S1568494617306798)
  MOEA for relevance-vs-diversity tradeoff; evolves query populations avoiding genotypic convergence.

- **Evolutionary Multi-Objective Diversity Optimization** (PPSN 2024)
  [https://arxiv.org/abs/2401.07454](https://arxiv.org/abs/2401.07454)
  Frames quality-diversity as bi-objective (quality vs. diversity) with NSGA-II and SPEA2. Not IR-specific but directly applicable.

- **Faster, Cheaper, Better: Multi-Objective HPO for LLM and RAG Systems** (ICLR 2025 Workshop)
  [https://arxiv.org/abs/2502.18635](https://arxiv.org/abs/2502.18635)
  First paper on multi-objective optimization (cost, latency, safety, quality) across entire RAG pipelines. Bayesian optimization for Pareto-optimal configs.

- **An Analysis of Hyper-Parameter Optimization Methods for RAG** (May 2025)
  [https://arxiv.org/abs/2505.03452](https://arxiv.org/abs/2505.03452)
  Largest RAG HPO search space to date. Greedy and random search surprisingly effective; optimizing model selection first beats pipeline order.

### Evolving/Adaptive RAG (closest conceptual neighbors)

- **EvoRAG: Making KG-based RAG Automatically Evolve through Feedback-driven Backpropagation** (April 2025)
  [https://arxiv.org/abs/2604.15676](https://arxiv.org/abs/2604.15676)
  Self-evolving KG-RAG propagating feedback utility scores back to KG triplets. Not population-based but implements evolution-by-selection. 7.34% improvement over GraphRAG/LightRAG.

- **EvoR: Evolving Retrieval for Code Generation** (2024)
  [https://arxiv.org/html/2402.12317](https://arxiv.org/html/2402.12317)
  Synchronously evolves queries and knowledge base in RAG for code. "Evolution" as adaptive iteration, not population-based.

### NSCO Framework (general evolutionary optimization)

- **Learning-Infused Optimization for Evolutionary Computation (NSCO)** (Swarm and Evolutionary Computation, Vol. 95, 2025)
  [https://www.sciencedirect.com/science/article/abs/pii/S2210650225000884](https://www.sciencedirect.com/science/article/abs/pii/S2210650225000884)
  Neural-Synergized Co-evolutionary Optimization. General optimization, not IR — but the framework pattern (neural networks learning from evolutionary trajectories) could template Darwin's fitness-guided evolution.

### Coevolution and Adversarial Training

- **Competitive Coevolution as Adversarial Approach to Dynamic Optimization** (2019)
  [https://arxiv.org/abs/1907.13529](https://arxiv.org/abs/1907.13529)
  Two coevolving populations adversarially search in dynamic environments. Directly relevant to Darwin's adversarial retrieval hardening.

- **Runtime Analysis of Competitive Co-evolutionary Algorithms for Maximin** (Algorithmica, 2024)
  [https://link.springer.com/article/10.1007/s00453-024-01218-3](https://link.springer.com/article/10.1007/s00453-024-01218-3)
  First rigorous runtime analysis of competitive coevolution. Addresses pathologies (relative over-generalization, mediocre objective stasis).

- **GECCO 2025 Tutorial: Coevolutionary Computation for Adversarial Deep Learning**
  [https://gecco-2025.sigevo.org/Tutorial?itemId=5116](https://gecco-2025.sigevo.org/Tutorial?itemId=5116)
  Tutorial on two-population coevolution for adversarial robustness using Lipizzaner framework.

### GitHub Repos

- **ALFA-group/lipizzaner-gan** — Distributed coevolutionary GAN training
  [https://github.com/ALFA-group/lipizzaner-gan](https://github.com/ALFA-group/lipizzaner-gan)
  Grid-based spatial coevolution of generator and discriminator populations. Code reference for two-population adversarial coevolution.

- **hengzhe-zhang/RAG-SR** — Retrieval-Augmented Generation for Symbolic Regression (ICLR 2025)
  [https://github.com/hengzhe-zhang/RAG-SR](https://github.com/hengzhe-zhang/RAG-SR)
  **The only open-source repo that genuinely merges evolutionary algorithms with a RAG paradigm.** Population-based search with `n_pop` parameter.

- **Quality-Diversity algorithms resource hub**
  [https://quality-diversity.github.io/](https://quality-diversity.github.io/)
  Comprehensive paper list for MAP-Elites and related algorithms. Not yet applied to IR but the framework could inform Darwin's diversity-preserving selection.

---

## 2. Adaptive RAG and Self-Improving Retrieval

### Foundational Adaptive RAG Papers

- **CRAG: Corrective Retrieval Augmented Generation**
  [https://arxiv.org/abs/2401.15884](https://arxiv.org/abs/2401.15884)
  Lightweight evaluator (0.77B params) classifies docs as Correct/Incorrect/Ambiguous; triggers web search fallback.

- **Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection** (ICLR 2024 Oral)
  [https://arxiv.org/abs/2310.11511](https://arxiv.org/abs/2310.11511)
  Trains LM to decide on-demand whether to retrieve, self-critiques via learned reflection tokens.
  GitHub: [https://github.com/AkariAsai/self-rag](https://github.com/AkariAsai/self-rag) (~2.2k stars)

- **Adaptive-RAG: Learning to Adapt RAG through Question Complexity** (KAIST, NAACL 2024)
  [https://arxiv.org/abs/2403.14403](https://arxiv.org/abs/2403.14403)
  Trains classifier to route queries to no-retrieval / single-step / multi-step RAG based on complexity. Static — never learns from outcomes.

- **FLARE: Active Retrieval Augmented Generation** (EMNLP 2023)
  [https://arxiv.org/abs/2305.06983](https://arxiv.org/abs/2305.06983)
  Iteratively generates tentative next sentence; low-confidence tokens trigger retrieval.

- **RAG-Fusion**
  [https://arxiv.org/abs/2402.03367](https://arxiv.org/abs/2402.03367)
  Multi-query generation + reciprocal rank fusion to merge document sets.

- **RankRAG: Unifying Context Ranking with RAG** (NeurIPS 2024)
  [https://arxiv.org/abs/2407.02485](https://arxiv.org/abs/2407.02485)
  Single LLM does both ranking and generation; mutually reinforcing.

- **AIR-RAG: Adaptive Iterative Retrieval** (Neurocomputing, Dec 2025)
  [https://www.sciencedirect.com/science/article/pii/S0925231225029443](https://www.sciencedirect.com/science/article/pii/S0925231225029443)
  Adaptive feedback between ranking and refinement across iterations without retraining.

- **FAIR-RAG: Faithful Adaptive Iterative Refinement**
  [https://arxiv.org/abs/2510.22344](https://arxiv.org/abs/2510.22344)
  Decomposes queries into evidence checklists; iteratively refines sub-queries until coverage sufficient.

- **TG-RAG: RAG Meets Temporal Graphs**
  [https://arxiv.org/abs/2510.13590](https://arxiv.org/abs/2510.13590)
  Bi-level temporal knowledge graphs with time-scoped retrieval. Only paper on temporal-aware retrieval.

### Surveys and Frameworks

- **SoK: Agentic RAG — Taxonomy, Architectures, Evaluation** (March 2026)
  [https://arxiv.org/abs/2603.07379](https://arxiv.org/abs/2603.07379)
  Formalizes agentic retrieval as POMDP. Five-component taxonomy. Identifies learned retrieval policies as key open direction.

- **Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG**
  [https://arxiv.org/abs/2501.09136](https://arxiv.org/abs/2501.09136)
  Evolution from Naive RAG through Modular and Graph RAG to Agentic RAG.

- **NirDiamant/RAG_Techniques** — GitHub (~24.5k stars)
  [https://github.com/NirDiamant/RAG_Techniques](https://github.com/NirDiamant/RAG_Techniques)
  20+ advanced RAG technique tutorials as Jupyter notebooks.

- **Awesome RAG Reasoning** (EMNLP 2025 resource list)
  [https://github.com/DavidZWZ/Awesome-RAG-Reasoning](https://github.com/DavidZWZ/Awesome-RAG-Reasoning)
  Curated list: RL-based retrieval, process supervision, agentic approaches.

### RL for Retrieval (gradient-based alternatives to Darwin's population-based approach)

- **Search-R1: Training LLMs to Reason and Leverage Search Engines with RL** (COLM 2025)
  [https://arxiv.org/abs/2503.09516](https://arxiv.org/abs/2503.09516)
  RL (GRPO/PPO) for interleaved multi-turn search in chain-of-thought. 41% improvement over RAG baselines.
  GitHub: [https://github.com/PeterGriffinJin/Search-R1](https://github.com/PeterGriffinJin/Search-R1)

- **ReSearch: Learning to Reason with Search via RL**
  [https://arxiv.org/abs/2503.19470](https://arxiv.org/abs/2503.19470)
  No supervised data; LLMs learn when/how to invoke search. Emergent self-correction.

- **RAG-RL: Advancing RAG via RL and Curriculum Learning**
  [https://arxiv.org/abs/2503.12759](https://arxiv.org/abs/2503.12759)
  First reasoning LM explicitly trained for RAG using GRPO. SOTA on HotpotQA and MuSiQue.

- **R3: Optimizing Retrieval for RAG via RL**
  [https://arxiv.org/abs/2510.24652](https://arxiv.org/abs/2510.24652)
  RL applied directly to the retriever (not generator). 5.2% improvement over base retrievers.

- **R3-RAG: Learning Step-by-Step Reasoning and Retrieval via RL**
  [https://arxiv.org/abs/2505.23794](https://arxiv.org/abs/2505.23794)
  Dual-reward RL (answer correctness + document relevance). Cross-retriever transfer demonstrated.

- **Stop-RAG: Value-Based Retrieval Control for Iterative RAG**
  [https://arxiv.org/abs/2510.14337](https://arxiv.org/abs/2510.14337)
  Casts iterative RAG as finite-horizon MDP. Value-based controller decides when to stop retrieving.

- **ProRAG: Process-Supervised RL for RAG** (Jan 2026)
  [https://arxiv.org/abs/2601.21912](https://arxiv.org/abs/2601.21912)
  MCTS-based process reward model with dual-granularity advantage estimation. Solves credit assignment in multi-hop RAG.

- **AutoSearch: Adaptive Search Depth for Efficient Agentic RAG** (April 2026)
  [https://arxiv.org/abs/2604.17337](https://arxiv.org/abs/2604.17337)
  "Minimal sufficient search depth" concept. RL agent finds optimal accuracy-efficiency tradeoff.

### Adversarial RAG Robustness

- **RobustRAG: Certifiably Robust RAG against Retrieval Corruption**
  [https://arxiv.org/abs/2405.15556](https://arxiv.org/abs/2405.15556)
  Isolate-then-aggregate defense with formal certified robustness guarantees.

- **ReliabilityRAG: Effective and Provably Robust Defense for RAG** (NeurIPS 2025)
  [https://arxiv.org/abs/2509.23519](https://arxiv.org/abs/2509.23519)
  Graph-theoretic "consistent majority" approach with provable robustness bounds.

- **Towards More Robust RAG: Evaluating RAG Under Adversarial Poisoning Attacks**
  [https://arxiv.org/abs/2412.16708](https://arxiv.org/abs/2412.16708)
  Systematic evaluation of RAG vulnerability to corpus poisoning across multiple attack strategies.

### Retrieval Confidence

- **Noise-Aware Verbal Confidence Calibration for Robust LLMs in RAG**
  [https://arxiv.org/abs/2601.11004](https://arxiv.org/abs/2601.11004)
  First paper modeling retrieval noise types for confidence estimation. Improves ECE by 10.9% in-domain.

---

## 3. Multi-Agent Collaboration and Coordination

### Key Architecture Papers

- **"Theater of Mind": Global Workspace Agents (GWA)** (April 2026)
  [https://arxiv.org/abs/2604.08206](https://arxiv.org/abs/2604.08206)
  Event-driven cognitive architecture with entropy-based deadlock breaking and dual-layer memory. Global Workspace Theory for LLM agents. Brand new.

- **LbMAS: Blackboard-Based LLM Multi-Agent System**
  [https://arxiv.org/abs/2507.01701](https://arxiv.org/abs/2507.01701)
  Public/private shared memory, dynamic agent selection. 13-57% improvement over master-slave and RAG baselines.

- **Why Do Multiagent Systems Fail?** (ICLR 2025)
  [https://openreview.net/forum?id=wM521FqPvI](https://openreview.net/forum?id=wM521FqPvI)
  Taxonomy of 18 failure modes across 150+ tasks and 5 frameworks. Top category: specification ambiguity.

- **ProtocolBench: Which LLM Multi-Agent Protocol to Choose?**
  [https://arxiv.org/abs/2510.17149](https://arxiv.org/abs/2510.17149)
  Benchmarks A2A, ACP, ANP, Agora protocols. Introduces ProtocolRouter for per-scenario selection.

- **Agentifying Agentic AI** (AAAI Bridge Program)
  [https://arxiv.org/abs/2511.17332](https://arxiv.org/abs/2511.17332)
  Critiques single-agent orientation; argues for proper multi-agent coordination with incentive structures.

### Context and Communication

- **TokenDance: Multi-Agent KV Cache Sharing**
  [https://arxiv.org/abs/2604.03143](https://arxiv.org/abs/2604.03143)
  All-Gather pattern; 17.5x KV cache compression; 2.7x more concurrent agents.

- **ACON: Optimizing Context Compression for Long-horizon Agents**
  [https://arxiv.org/abs/2510.00615](https://arxiv.org/abs/2510.00615)
  Failure-driven compression; 26-54% token reduction. Does NOT address multi-agent variant.

- **Agent Discovery in Internet of Agents**
  [https://arxiv.org/abs/2511.19113](https://arxiv.org/abs/2511.19113)
  Semantic profiling via embeddings for agent capability discovery.

- **LLM Multi-Agent Systems: Challenges and Open Problems** (Han et al. survey)
  [https://arxiv.org/abs/2402.03578](https://arxiv.org/abs/2402.03578)
  Broad survey: task allocation, iterative debate, layered context, memory design.

### Credit Assignment (unsolved)

- **SHARP: Shapley Credit-based Optimization for Multi-Agent System**
  [https://arxiv.org/abs/2602.08335](https://arxiv.org/abs/2602.08335)
  RLHF framework with Shapley-based marginal credit + tool-process components. 23.66% improvement over single-agent.

- **Shapley-Coop: Credit Assignment for Emergent Cooperation**
  [https://arxiv.org/abs/2506.07388](https://arxiv.org/abs/2506.07388)
  Shapley chain-of-thought reasoning with negotiation protocols for fair reward redistribution.

### Stigmergy and Decentralized Coordination

- **Emergent Collective Memory in Decentralized Multi-Agent AI Systems**
  [https://arxiv.org/abs/2512.10166](https://arxiv.org/abs/2512.10166)
  Formalizes stigmergic coordination for decentralized agents. 36-41% improvement at high agent densities.

- **Decentralized Adaptive Task Allocation for Dynamic Multi-Agent Systems** (Nature Scientific Reports)
  [https://www.nature.com/articles/s41598-025-21709-9](https://www.nature.com/articles/s41598-025-21709-9)
  Two-layer architecture with adaptive controllers and relevance-based task broadcasting.

### Market-Based and Auction Mechanisms

- **PolySwarm: Multi-Agent LLM Framework for Prediction Market Trading**
  [https://arxiv.org/abs/2604.03888](https://arxiv.org/abs/2604.03888)
  Diverse LLM agents with distinct personas; market-based coordination via statistical ensemble.

### Byzantine Fault Tolerance for Agents

- **Rethinking MAS Reliability: Byzantine Fault Tolerance Perspective** (AAAI)
  [https://arxiv.org/abs/2511.10400](https://arxiv.org/abs/2511.10400)
  CP-WBFT consensus mechanism; maintains stability under 85.7% Byzantine fault rates.

- **DecentLLMs: Byzantine-Robust Decentralized Coordination**
  [https://arxiv.org/abs/2507.14928](https://arxiv.org/abs/2507.14928)
  Leaderless consensus with Byzantine-robust aggregation avoiding single-leader vulnerabilities.

- **Weighted BFT Consensus for Multi-LLM Networks**
  [https://arxiv.org/abs/2505.05103](https://arxiv.org/abs/2505.05103)
  Blockchain consensus for multi-LLM; weighting by response quality and trustworthiness.

### Industry and Frameworks

- **Multi-Agent in Production in 2026: What Actually Survived** (Lanham retrospective)
  [https://medium.com/@Micheal-Lanham/multi-agent-in-production-in-2026-what-actually-survived-f86de8bb1cd1](https://medium.com/@Micheal-Lanham/multi-agent-in-production-in-2026-what-actually-survived-f86de8bb1cd1)
  Only orchestrated pipelines survived. Free-form loops didn't.

- **AWS Strands: Multi-Agent Collaboration — The Arbiter Pattern**
  [https://aws.amazon.com/blogs/devops/multi-agent-collaboration-with-strands/](https://aws.amazon.com/blogs/devops/multi-agent-collaboration-with-strands/)
  Dynamic agent fabrication + semantic capability matching + blackboard coordination.

- **blackboard-core Python SDK** (PyPI)
  [https://pypi.org/project/blackboard-core/](https://pypi.org/project/blackboard-core/)
  Ready-made blackboard pattern for LLM multi-agent systems. Async support, MCP integration.

---

## 4. Long-Horizon Agent Consistency

### Core Research Papers

- **Beyond pass@1: A Reliability Science Framework for Long-Horizon LLM Agents** (March 2026)
  [https://arxiv.org/abs/2603.29231](https://arxiv.org/abs/2603.29231)
  **Key finding: memory scaffolds universally HURT long-horizon reliability (the "MOP paradox").** Frontier models have highest meltdown rates because they pursue ambitious strategies.

- **The Long-Horizon Task Mirage: Diagnosing Where and Why Agentic Systems Break** (April 2026)
  [https://arxiv.org/abs/2604.11978](https://arxiv.org/abs/2604.11978)
  HORIZON benchmark, 3,100+ trajectories. Model scaling alone won't fix dominant failure mechanisms.

- **Sophia: A Persistent Agent Framework of Artificial Life**
  [https://arxiv.org/abs/2512.18202](https://arxiv.org/abs/2512.18202)
  "System 3" meta-cognitive layer. 80% fewer reasoning steps on recurring tasks; 40% higher success on hard tasks.

- **Engram: Improving Coherence and Persistence in Agentic AI**
  [https://arxiv.org/abs/2603.21321](https://arxiv.org/abs/2603.21321)
  Persistent archive + Research Digest handoff. Sustains coherent research across hundreds of trials.

- **From Static Templates to Dynamic Runtime Graphs** (IBM survey, March 2026)
  [https://arxiv.org/abs/2603.22386](https://arxiv.org/abs/2603.22386)
  Formalizes agentic systems as computation graphs; static vs. dynamic workflow determination.

- **AI Runtime Infrastructure** (March 2026)
  [https://arxiv.org/abs/2603.00495](https://arxiv.org/abs/2603.00495)
  Formalizes runtime layer for adaptive memory management, failure detection/recovery, and policy enforcement. Describes VIGIL reflective recovery system.

- **CAR-bench: Evaluating Consistency and Limit-Awareness under Uncertainty** (Jan 2026)
  [https://arxiv.org/abs/2601.22027](https://arxiv.org/abs/2601.22027)
  58 tools; frontier models achieve under 50% consistent pass rate on disambiguation tasks.

- **Optimizing Agentic Workflows using Meta-tools**
  [https://arxiv.org/abs/2601.22037](https://arxiv.org/abs/2601.22037)
  Checkpoint and trajectory efficiency for long agent runs on VisualWebArena and AppWorld.

- **A Practical Guide for Production-Grade Agentic AI Workflows**
  [https://arxiv.org/abs/2512.08769](https://arxiv.org/abs/2512.08769)
  Reliability, observability, maintenance, governance. Checkpoint-based safeguards for multi-step execution.

### Industry Data and Analysis

- **Context Decay, Orchestration Drift, and Silent Failures** (VentureBeat, April 2026)
  [https://venturebeat.com/infrastructure/context-decay-orchestration-drift-and-the-rise-of-silent-failures-in-ai-systems](https://venturebeat.com/infrastructure/context-decay-orchestration-drift-and-the-rise-of-silent-failures-in-ai-systems)
  ~2% accuracy degradation per reasoning step; ~40% failure by step 20. Systems show green on infra metrics while reasoning over stale data.

- **Agent Drift: Why Long-Running AI Agents Lose the Plot** (Wire Blog)
  [https://usewire.io/blog/agent-drift-why-long-running-ai-agents-lose-the-plot/](https://usewire.io/blog/agent-drift-why-long-running-ai-agents-lose-the-plot/)
  Six drift mechanisms: goal, context, role, tool-use, hallucination cascade, plan decay. METR data: reliable completion on order of hours, not days.

- **How Long Contexts Fail** (dbreunig.com, June 2025)
  [https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html)
  Context poisoning, distraction, confusion. Gemini 2.5 Pro degrades beyond 100K tokens despite 1M window.

- **The Potential of RLMs** (dbreunig.com, Feb 2026)
  [https://www.dbreunig.com/2026/02/09/the-potential-of-rlms.html](https://www.dbreunig.com/2026/02/09/the-potential-of-rlms.html)
  Reasoning Language Models with separate tokenized and programmatic context pools to combat context rot.

- **CrewAI Issue #3154: Agent Fabricates Tool Usage**
  [https://github.com/crewAIInc/crewAI/issues/3154](https://github.com/crewAIInc/crewAI/issues/3154)
  Agents generate fake Thought-Action-Observation traces without executing real tool calls.

### Framework Comparisons

- **Hardening LangGraph State for Production** (MLPills Substack)
  [https://mlpills.substack.com/p/extra-7-hardening-langgraph-state](https://mlpills.substack.com/p/extra-7-hardening-langgraph-state)
  Checkpoint bloat (50 snapshots for 10-turn conversation), opaque blobs, concurrency races.

- **LangGraph State Management with MongoDB** (MLPills)
  [https://mlpills.substack.com/p/issue-125-langgraph-state-management](https://mlpills.substack.com/p/issue-125-langgraph-state-management)
  Full state snapshot after every node; bloat, opaque storage, persistence of ephemeral data.

- **Mem0 vs Letta vs MemGPT 2026** (TokenMix.ai)
  [https://tokenmix.ai/blog/ai-agent-memory-mem0-vs-letta-vs-memgpt-2026](https://tokenmix.ai/blog/ai-agent-memory-mem0-vs-letta-vs-memgpt-2026)
  Mem0 = memory-as-a-service. Letta = full agent runtime with self-editing three-tier memory.

- **Temporal vs LangGraph 2026** (Cordum.io)
  [https://cordum.io/blog/temporal-vs-langgraph](https://cordum.io/blog/temporal-vs-langgraph)
  Recommended: wrap LangGraph as Temporal activity for retries, timeout, restart safety.

- **LangChain vs CrewAI vs AutoGen: Which Breaks in Production?** (Cordum.io)
  [https://cordum.io/blog/ai-agent-frameworks-comparison](https://cordum.io/blog/ai-agent-frameworks-comparison)
  Highest-cost mistakes are durability and approval flows, not prompt syntax.

---

## 5. MongoDB Atlas Implementation References

### Voyage AI and Embeddings

- **Voyage 4 Models Announcement** (press release, Jan 2026)
  [https://www.mongodb.com/press/mongodb-sets-a-new-standard-for-retrieval-accuracy-with-voyage-4-models](https://www.mongodb.com/press/mongodb-sets-a-new-standard-for-retrieval-accuracy-with-voyage-4-models)
  Voyage 4 family (large, standard, lite, nano); MoE architecture; shared embedding space.

- **Automated Embedding in MongoDB Vector Search** (blog)
  [https://www.mongodb.com/company/blog/product-release-announcements/unlocking-ai-search-introducing-automated-embedding-in-mongodb-vector-search](https://www.mongodb.com/company/blog/product-release-announcements/unlocking-ai-search-introducing-automated-embedding-in-mongodb-vector-search)
  Auto-generates and syncs Voyage AI embeddings on index creation.

- **How to Automatically Generate Vector Embeddings** (docs)
  [https://www.mongodb.com/docs/atlas/atlas-vector-search/crud-embeddings/create-embeddings-automatic/](https://www.mongodb.com/docs/atlas/atlas-vector-search/crud-embeddings/create-embeddings-automatic/)
  Step-by-step: model selection, `$vectorSearch` query-text option.

- **Atlas Embedding and Reranking API** (REST API docs)
  [https://www.mongodb.com/docs/api/doc/atlas-embedding-and-reranking-api/](https://www.mongodb.com/docs/api/doc/atlas-embedding-and-reranking-api/)
  Endpoints, rate limits, multimodal support. Public preview; 200M free tokens.

- **Embedding and Reranking API Announcement** (blog)
  [https://www.mongodb.com/company/blog/product-release-announcements/introducing-the-embedding-and-reranking-api-on-mongodb-atlas](https://www.mongodb.com/company/blog/product-release-announcements/introducing-the-embedding-and-reranking-api-on-mongodb-atlas)
  Serverless API with token-based pricing.

- **Voyage AI Quick Start** (docs)
  [https://www.mongodb.com/docs/voyageai/quickstart/](https://www.mongodb.com/docs/voyageai/quickstart/)
  Getting started with Voyage AI Python client; voyage-4-large; 1024-dim output.

- **Semantic Search with Voyage AI Embeddings** (tutorial)
  [https://www.mongodb.com/docs/voyageai/tutorials/semantic-search/](https://www.mongodb.com/docs/voyageai/tutorials/semantic-search/)
  End-to-end semantic search with `input_type` optimization.

### Atlas Vector Search

- **Vector Search Overview** (docs)
  [https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/](https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/)
  ANN/ENN search, index creation, `$vectorSearch` aggregation stage, quantization.

- **Hybrid Search** (docs)
  [https://www.mongodb.com/docs/atlas/atlas-vector-search/hybrid-search/](https://www.mongodb.com/docs/atlas/atlas-vector-search/hybrid-search/)
  Combining `$vectorSearch` with `$search` via `$rankFusion` (v8.0+) or `$scoreFusion` (v8.2+).

- **Vector Search Quick Start** (tutorial)
  [https://www.mongodb.com/docs/atlas/atlas-vector-search/tutorials/vector-search-quick-start/](https://www.mongodb.com/docs/atlas/atlas-vector-search/tutorials/vector-search-quick-start/)
  Create index, insert embeddings, run `$vectorSearch` with Python/PyMongo.

### Core MongoDB Features for Darwin

- **Change Streams** (docs)
  [https://www.mongodb.com/docs/manual/changestreams/](https://www.mongodb.com/docs/manual/changestreams/)
  Real-time change events; resume tokens; aggregation pipeline filtering; pre/post-image support.

- **Time Series Collections** (docs)
  [https://www.mongodb.com/docs/manual/core/timeseries-collections/](https://www.mongodb.com/docs/manual/core/timeseries-collections/)
  Columnar storage, automatic bucketing, metaField indexing. For fitness history tracking.

- **Aggregation Pipelines** (docs)
  [https://www.mongodb.com/docs/manual/core/aggregation-pipeline/](https://www.mongodb.com/docs/manual/core/aggregation-pipeline/)
  `$match`, `$group`, `$lookup`, `$project`, `$unwind`. For population statistics.

- **TTL Indexes** (docs)
  [https://www.mongodb.com/docs/manual/tutorial/expire-data/](https://www.mongodb.com/docs/manual/tutorial/expire-data/)
  Auto-delete documents after specified duration. For culling dead genomes.

- **Transactions** (docs)
  [https://www.mongodb.com/docs/manual/core/transactions/](https://www.mongodb.com/docs/manual/core/transactions/)
  Multi-document ACID. For safe concurrent population updates during evolution.

### Agent Architecture with MongoDB

- **Converged Datastore for Agentic AI** (blog, Aug 2025)
  [https://www.mongodb.com/company/blog/technical/converged-datastore-for-agentic-ai](https://www.mongodb.com/company/blog/technical/converged-datastore-for-agentic-ai)
  MongoDB Atlas as unified cognitive core: operational data + vectors + streams + tools.

- **Why Multi-Agent Systems Need Memory Engineering** (blog)
  [https://www.mongodb.com/company/blog/technical/why-multi-agent-systems-need-memory-engineering](https://www.mongodb.com/company/blog/technical/why-multi-agent-systems-need-memory-engineering)
  Four failure modes: context poisoning, distraction, confusion, clash.

- **Long-Term Memory for Agents with LangGraph and MongoDB** (blog)
  [https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph](https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph)
  `langgraph-store-mongodb` package; cross-thread persistence + semantic memory retrieval.

- **Multi-Agent Order Management with smolagents + MongoDB** (HuggingFace Cookbook)
  [https://huggingface.co/learn/cookbook/en/mongodb_smolagents_multi_micro_agents](https://huggingface.co/learn/cookbook/en/mongodb_smolagents_multi_micro_agents)
  Step-by-step multi-agent tutorial with inventory/order/delivery agents.

### MongoDB MCP and Agent Skills

- **MongoDB MCP Server** (docs)
  [https://www.mongodb.com/docs/mcp-server/](https://www.mongodb.com/docs/mcp-server/)
  MCP server exposing DB ops, Atlas management, Performance Advisor to AI clients.

- **mongodb-js/mongodb-mcp-server** (GitHub)
  [https://github.com/mongodb-js/mongodb-mcp-server](https://github.com/mongodb-js/mongodb-mcp-server)
  Source repo; setup, config, Docker support, HTTP/stdio transport.

- **mongodb/agent-skills** (GitHub)
  [https://github.com/mongodb/agent-skills](https://github.com/mongodb/agent-skills)
  Pre-built skills for coding agents: schema design, indexing, query patterns, vector search.

### Pete Johnson (Judge) — Recent Output

- **5 Core Embeddings Choices for Developers** (MongoDB.local SF 2026, YouTube)
  [https://www.youtube.com/watch?v=YqQ0laSZCxM](https://www.youtube.com/watch?v=YqQ0laSZCxM)
  The 5 decisions: similarity function, chunking, dimensions, quantization, reranking. **These ARE Darwin's retrieval genome parameters.**

- **You Need Quality Engineers to Turn AI into ROI** (Stack Overflow Podcast)
  [https://stackoverflow.blog/2026/01/07/you-need-quality-engineers-to-turn-ai-into-roi/](https://stackoverflow.blog/2026/01/07/you-need-quality-engineers-to-turn-ai-into-roi/)
  Embeddings/vector search drive AI ROI; Voyage AI acquisition rationale.

- **MongoDB's 2025 in Review and 2026 Predictions** (blog)
  [https://www.mongodb.com/company/blog/mongodb-2025-in-review-2026-predictions](https://www.mongodb.com/company/blog/mongodb-2025-in-review-2026-predictions)
  Voyage AI, CEO transition, customer wins, 2026 AI predictions.

### Hackathon

- **Agentic Memory & Context Engineering Hackathon** (Cerebral Valley)
  [https://cerebralvalley.ai/e/mongoDB-hackathon](https://cerebralvalley.ai/e/mongoDB-hackathon)
  The hackathon page. Note: title on site is "Agentic Memory & Context Engineering" rather than "Agentic Evolution."
