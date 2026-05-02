# Darwin — Evolutionary Adaptive Retrieval

**Hackathon:** MongoDB Agentic Evolution Hackathon, London, May 2, 2026 (12h build, 9am-9pm)
**Finalists demo:** MongoDB.local London, May 7
**Prizes:** 15k GBP cash, 1-month London Founder House residency, partner credits
**Rules:** Max team size 4, repos must be public, only new work built during the event counts
**Required stack for finalists:** MongoDB Atlas

---

## The Idea

A retrieval system where the entire multi-agent coordination architecture evolves through natural selection. Retrieval strategies, collaboration protocols, and durability behaviors are encoded as parameterized "genomes" — structured MongoDB documents. A population of agent genomes competes on incoming queries. Fitness is measured by downstream answer quality. The population evolves through selection, crossover, and mutation. The system literally discovers its own optimal multi-agent retrieval architecture rather than having it designed by a human.

The core claim: **multi-agent coordination protocols can be discovered through evolution rather than designed.**

### Why This Wins

1. The hackathon is literally called "Agentic **Evolution**" — a system that does biological evolution is the most on-theme entry possible
2. Pete Johnson's (judge, MongoDB Field CTO AI) MongoDB.local SF talk identified 5 embedding decisions: chunking, similarity function, dimensions, quantization, reranking — those five decisions ARE the retrieval genome layer
3. Every MongoDB Atlas differentiator is load-bearing (automated embedding, document model, time-series, change streams, ACID, vector search)
4. Confirmed novel — no paper connects evolutionary computation to modern RAG pipelines
5. The demo moment: "We didn't design our multi-agent retrieval system. We evolved it."

---

## Three-Layer Genome

Each agent genome is a MongoDB document with three layers, one per hackathon theme:

### Layer 1 — Retrieval Genes (Theme 3: Adaptive Retrieval)
- Embedding model (Voyage 4 variant: voyage-4, voyage-4-large, voyage-4-lite, voyage-4-nano)
- Chunk size (e.g., 128, 256, 512, 1024 tokens)
- Chunk overlap (0%, 10%, 25%, 50%)
- Query transformation method (none, HyDE, multi-query, step-back)
- Reranking approach (none, cross-encoder, LLM-rerank, reciprocal rank fusion)
- Confidence threshold (0.0 - 1.0, below which results are discarded)
- Source routing (which collections/indices to query)

### Layer 2 — Coordination Genes (Theme 2: Multi-Agent Collaboration)
- Broadcasting behavior (broadcast_all | broadcast_high_confidence | broadcast_never)
- Context sharing threshold (how much of context window to expose to peers)
- Deference rules (when to yield to another agent's results — never | on_low_confidence | on_specialization_match)
- Specialization affinity (what query types this agent claims competence on)
- Consensus participation (independent | voting | defer_to_majority)

### Layer 3 — Durability Genes (Theme 1: Prolonged Coordination)
- Checkpoint frequency (every_query | every_5 | every_10 | on_confidence_drop)
- Drift detection sensitivity (0.0 - 1.0, how aggressively it checks consistency against prior decisions)
- Memory decay rate (none | slow | medium | aggressive)
- Recovery strategy (restart_fresh | resume_checkpoint | rollback_last_good)

---

## The Evolutionary Loop

1. **Query arrives**
2. **Tournament selection**: pick top-K agent genomes by fitness score, weighted by similarity to query type
3. **Each selected agent executes independently** (multi-agent retrieval via blackboard/workspace)
4. **Fitness evaluation**: LLM-as-judge scores each agent's retrieval quality against downstream answer correctness
5. **Update fitness scores** in MongoDB time-series collection
6. **Every N queries, evolve the population**:
   - Tournament selection (pick parents from top performers)
   - Crossover (combine genes from two parents — discrete genes pick one parent's value, continuous genes interpolate)
   - Mutation (Gaussian perturbation on continuous genes, random swap on discrete genes)
   - New child genomes enter the population
7. **Cull** the weakest genomes below a fitness threshold

---

## Theme Coverage

### Theme 3 — Adaptive Retrieval (PRIMARY)
> "Create an agentic retrieval system that actively fetches from various resources... modifying query approaches, altering chunking, reordering results based on input. How can you create an agentic and adaptive retrieval system that improves over time and performs reasoning across various documents and sources?"

- **Modifying query approaches**: different genomes use different query transformation methods (HyDE, multi-query, step-back)
- **Altering chunking**: different genomes use different chunk sizes and overlaps
- **Reordering results**: fitness-weighted reranking; different reranking strategies per genome
- **Improves over time**: the population evolves — fitness increases generation over generation
- **Various resources**: source routing genes control which collections/indices each agent queries
- **Reasoning across documents**: fittest strategies do cross-document synthesis

### Theme 2 — Multi-Agent Collaboration (STRONG SECONDARY)
> "How do agents convey their skills, identify suitable peers for a sub-task, share context effectively within token limits, and perform intricate tasks resulting from successful collaborations?"

- **Convey skills**: specialization affinity genes encode what each agent is good at
- **Identify suitable peers**: tournament selection + query-type matching
- **Share context within token limits**: context sharing threshold gene controls exposure
- **Successful collaborations**: coordination genes evolve — the system discovers which collaboration patterns produce the best results
- **Blackboard architecture**: agents share results via MongoDB workspace collection; broadcasting behavior is evolved, not designed

### Theme 1 — Prolonged Coordination (SOLID TERTIARY)
> "How do you execute tool calls, retain reasoning state, recover from single failures, and ensure task consistency in multi-step tasks?"

- **Retain reasoning state**: checkpoint frequency gene controls persistence granularity; MongoDB is the durable state backend
- **Recover from failures**: recovery strategy gene (restart/resume/rollback) is evolved; crash and restart, evolution continues from last checkpoint
- **Task consistency**: drift detection sensitivity gene controls how aggressively agents check their own consistency
- **Multi-step**: evolution runs continuously over extended operation periods; fitness history spans hours/days as time-series data

---

## Judge Coverage

| Judge | Role | What They See in Darwin |
|-------|------|------------------------|
| Pete Johnson | MongoDB Field CTO AI | His 5 embedding decisions are the retrieval genome. Every Atlas feature is load-bearing. |
| Charlie Cheesman | 60x.ai CEO (multi-agent + knowledge graphs) | Strategy lineage IS a knowledge graph. Multi-agent competition + emergent specialization. |
| David Asamu | LangChain/LangGraph Platform | Novel orchestration pattern — evolutionary loop, not a DAG or conversation graph. |
| Sarah Otter | Creandum VP | Platform wedge — every RAG system needs strategy optimization. Darwin automates what devs tune by hand. |
| Bill Earner | EF Venture Partner | Technical insight that creates a moat: evolved coordination protocols are hard to reverse-engineer. |
| Raman Rai | UN Women UK AI Advisor | Transparent AI — every retrieval decision has a full audit trail (which strategy, its lineage, its fitness). |
| George Gilligan | ElevenLabs Security & Safety | Adversarial robustness — diverse strategy population is harder to fool than a single pipeline. |

---

## Demo Script (90 seconds)

### Pre-recorded video (60-75s):
1. Start with population of 10 base agent genomes (4 retrieval strategies x varying coordination/durability genes)
2. Run 50 queries through the system
3. Show evolution visualization in real-time:
   - Fitness curves per genome (line chart, generation on x-axis)
   - Family tree (who bred with whom, which children outperformed parents)
   - Emergent specialization (color-coded by evolved query-type affinity)
4. Highlight a child genome that outperforms both parents: "This retrieval architecture didn't exist 5 minutes ago. The system bred it from two parents."
5. Show the emerged collaboration pattern: "Agent A evolved to broadcast only high-confidence results. Agent B evolved to defer to A on legal queries but take the lead on technical queries. We didn't program this."
6. Introduce adversarial queries — show the population adapting (vulnerable strategies lose fitness, resistant ones thrive)

### Live anchor (15-30s):
- One real query against the evolved population
- Show which agent genome was selected, its lineage, its fitness history
- Show the result quality

### Backstop:
- Deployed URL (even if simple) so judges can poke at it post-demo

---

## 12-Hour Build Plan

| Block | Hours | What | Risk |
|-------|-------|------|------|
| Three-layer genome schema + MongoDB Atlas setup | 1 | Document model, indexes, collections (genomes, fitness_history, workspace, evolution_events) | Low — straightforward schema design |
| 4 base retrieval strategies (dense/sparse/hybrid/keyword via Voyage 4) | 1.5 | Implement each strategy as a parameterized function that reads its config from the genome | Medium — Voyage 4 API learning curve |
| Blackboard/workspace with coordination gene parameterization | 2 | Agents share via MongoDB workspace collection; broadcasting, deference, and specialization controlled by coordination genes | Medium — coordination logic is the novel part |
| Fitness evaluation (LLM-as-judge, tournament selection) | 1.5 | Head-to-head comparison of retrieval quality; reduces noise vs. absolute scoring | Low — well-understood pattern |
| Genetic operators (crossover + mutation across all three layers) | 2 | Discrete genes: single-parent selection. Continuous genes: Gaussian perturbation. Tournament selection for parents. | Low — standard evolutionary computation |
| Evolution loop with MongoDB checkpointing + time-series | 1 | Change streams trigger evolution events; population state durable in Atlas | Low |
| Visualization UI (evolution tree + fitness curves + collaboration patterns) | 2 | Web UI showing real-time evolution. This IS the demo surface. | High — UI is always the time sink |
| Testing + demo recording | 1 | Pre-run evolution for video; one live query for anchor | Medium — demo quality matters |

**Total: 12 hours. No slack.**

### Fleet (dev agent) assignments:
Fleet handles boilerplate — MongoDB CRUD, base strategy implementations, UI scaffolding. Lindell focuses on the evolutionary mechanics, coordination gene logic, and fitness evaluation.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Evolution doesn't converge in limited runtime | Pre-seed population with diverse but reasonable genomes. Curated query set that exercises different strategy strengths. Accelerate evolution to every 5 queries for demo. |
| Coordination genes produce nonsensical collaboration | Use discrete genes (enum values) not continuous. Crossover picks one parent's value per gene. Keeps patterns interpretable. |
| LLM-as-judge fitness is too noisy | Tournament selection (head-to-head comparison) reduces noise vs. absolute scoring. |
| Evolved system isn't measurably better than hand-designed | Demo goal is emergent specialization, not raw benchmark numbers. Agents evolving distinct complementary roles IS the "holy shit" moment. |
| 12 hours isn't enough | Cut UI visualization to simpler version if behind. The evolution engine + one terminal-based demo is the MVP. Pretty UI is stretch. |
| MongoDB Atlas setup takes too long | Pre-read Atlas docs. Have cluster provisioned before 9am if rules allow (infra setup vs. code). |

---

## MongoDB Atlas Features Used (Pete Johnson checklist)

| Feature | How Darwin Uses It | Why It's Load-Bearing |
|---------|-------------------|----------------------|
| Document model | Strategy genomes ARE documents — nested, polymorphic, schema-flexible | Genomes have variable-length gene arrays; relational model would fight this |
| Automated Embedding (Voyage 4) | Each strategy variant gets embeddings natively on ingest | No external embedding API calls; strategies can be compared by embedding similarity |
| Atlas Vector Search | Query-to-strategy routing via genome embedding similarity | Find strategies that historically perform well on similar queries |
| Time-series collections | Fitness history per genome over time | Track evolution trajectory; visualize convergence |
| Change streams | Trigger evolution events when fitness thresholds are crossed | Event-driven architecture; evolution doesn't poll |
| ACID transactions | Safe concurrent population updates during evolution | Multiple agents evaluating simultaneously; population mutations are atomic |
| Aggregation pipelines | Compute population statistics (mean fitness, diversity, specialization distribution) | Evolution decisions based on population-level metrics |
| TTL indexes | Auto-expire dead genomes below fitness threshold | Self-cleaning population |

---

## Previous Ideas Considered (and why Darwin won)

### Skillforge (agent skill registry with trust scoring)
- Red-teamed heavily. Theme 3 fit was only ~40% — it's a registry, not an adaptive retrieval system. "Modifying query approaches" and "altering chunking" had no answer. Competitive landscape crowded (Vercel skills.sh, Snyk+Tessl, SkillClaw paper).

### Forgetting Machine (selective memory decay)
- Novel angle ("AI gets better by forgetting"), based on real research (memory scaffolds hurt performance). But risky — hard to prove the effect in a demo window. Theme 2 coverage weak. Less MongoDB-differentiated (TTL indexes are common).

### Drift Detector (real-time consistency monitoring)
- Strong Theme 1 coverage but hard to demo — drift is slow, not visceral in 90 seconds.

### Adversarial Retrieval Hardening (self-red-teaming retrieval)
- George Gilligan would love it but narrow in theme coverage. Hard to show meaningful arms race in 12 hours.

### Darwin (retrieval-only, single-layer genome)
- The original version. Evolves retrieval parameters only. Ambitious but ultimately "sophisticated parameter tuning dressed up in biological metaphor." A sharp judge sees through it. Three-layer genome is the fix.

---

## Competitive Landscape

### What exists in evolutionary retrieval:
- Evolutionary approaches for classical IR exist (Springer 2025) but have NOT been applied to modern RAG
- NSCO framework (Swarm and Evolutionary Computation, 2025) integrates neural networks with evolutionary optimization — could be a template but nobody connected it to RAG
- No paper treats retrieval configuration as a mutable genome subject to selection pressure

### What exists in adaptive RAG:
- CRAG: lightweight evaluator classifies docs as Correct/Incorrect/Ambiguous, triggers web search fallback
- Self-RAG: reflection tokens for on-demand retrieval
- FLARE: forward-looking active retrieval when confidence drops
- Adaptive-RAG (KAIST, 2024): routes queries by complexity with static classifier — never learns from outcomes
- AIR-RAG (Dec 2025): adaptive iterative retrieval with feedback between ranking and refinement
- RankRAG: instruction-fine-tuned LLM does both ranking and generation
- RAG-Fusion: multi-query + reciprocal rank fusion
- None of these evolve. None learn from outcomes in a closed loop. None treat strategies as first-class evolvable objects.

### What exists in multi-agent collaboration:
- LbMAS blackboard architecture: 13-57% improvement over master-slave and RAG baselines
- "Theater of Mind" (arXiv 2604.08206, April 2026): Global Workspace Theory for LLM agents — active event-driven broadcasting
- ProtocolBench (arXiv 2510.17149): benchmarks agent communication protocols
- CrewAI, AutoGen, MetaGPT, Swarm: all orchestrated, none evolve their collaboration patterns

### Darwin's unique position:
Nobody has combined evolutionary computation + adaptive retrieval + multi-agent coordination evolution + MongoDB-native persistence. Each of these exists in isolation; the combination is novel.
