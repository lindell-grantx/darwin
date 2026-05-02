# Darwin — Architecture Proposal & Build Map

**Build window:** 5.5h · **Team:** 3 humans + fleet (alpha, beta, scout, reviewer, approver) · **Demo:** May 2 2026, MongoDB Agentic Evolution Hackathon London

---

## 1. Component Map

| Component | Lang | Purpose | Reads | Writes | Talks to |
|---|---|---|---|---|---|
| **`mongo_client`** | Py lib | Atlas connection pool, change-stream helpers | — | — | (used by all) |
| **`embedder`** | Py lib | Voyage-4 family wrapper (4, large, lite, nano + rerank) | — | — | Voyage API |
| **`retriever`** | Py lib | Vector + hybrid retrieval, query transform, rerank — gene-driven | `chunks` | — | `embedder`, Atlas Vector Search |
| **`fitness_judge`** | Py lib | LLM-as-judge (Claude Haiku 4.5) — relevance/accuracy/coverage | — | — | Anthropic API |
| **`agent_runner`** | Py worker | Executes one (genome, query) eval — retrieval → answer → score | `genomes`, `queries`, `chunks` | `fitness_evaluations` | `retriever`, `fitness_judge`, optional siblings via blackboard |
| **`coordinator`** | Py lib | Multi-agent collaboration protocols (vote / consult / debate) | `genomes` | (transient blackboard, persisted into `fitness_evaluations.coordination_trace`) | `agent_runner` |
| **`conductor`** | Py service | Drives evolution: change-stream listener, selection, crossover, mutation, generation rollover | `fitness_evaluations`, `genomes`, `generations` | `genomes`, `generations`, `champions` | Atlas change streams |
| **`api_server`** | FastAPI | Demo backend — `/query`, `/population`, `/lineage`, `/fitness-curve`, `/champions`, SSE for live evolution events | all 6 | `queries` (records new), enqueues evals via `fitness_evaluations` | `conductor` (in-process) |
| **`ui`** | Streamlit (primary) / Next.js (stretch) | Three-panel demo: fitness curve, family tree, live query | (via API) | — | `api_server` |
| **`seeder`** | Py CLI | Loads corpus → `chunks` (with Voyage embeddings × 4 model variants), seeds `queries`, births gen-0 `genomes` | — | `chunks`, `queries`, `genomes`, `generations` | Voyage API |

**Pick:** Streamlit for the UI. Next.js is sexier but burns 2h on plumbing — Streamlit gives charts + reactive components in 30 lines.

---

## 2. Data Flow (ASCII)

```
                             ┌─────────────┐
                             │  USER / UI  │
                             └──────┬──────┘
                                    │ POST /query
                                    ▼
                          ┌─────────────────────┐
                          │     api_server      │
                          │  - record query     │───────── writes ───────► [queries]
                          │  - select genomes   │◄──────── reads ───────── [genomes]
                          │  - dispatch run     │
                          └──────────┬──────────┘
                                     │ fanout (asyncio.gather, N=POP_PER_QUERY)
            ┌────────────────────────┼────────────────────────┐
            ▼                        ▼                        ▼
    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │ agent_runner │         │ agent_runner │         │ agent_runner │
    │   genome A   │◄──blackboard──►   B    │◄──blackboard──►   C    │
    └──────┬───────┘         └──────┬───────┘         └──────┬───────┘
           │ retrieve                │                       │
           │ (gene-driven)           │                       │
           ▼                         ▼                       ▼
       [chunks] ──── Voyage embed + Atlas Vector Search ────┐
                                                            │
           │ generate_answer (Claude)                       │
           │ judge (relevance/accuracy/cost/latency)        │
           ▼                                                │
   insert ──────────────────────────────────────────►  [fitness_evaluations]
                                                            │
                                                            │ MongoDB CHANGE STREAM
                                                            ▼
                                              ┌─────────────────────────┐
                                              │       conductor         │
                                              │  if N evals in for gen: │
                                              │   - aggregate fitness   │
                                              │   - elite + tournament  │
                                              │   - crossover + mutate  │
                                              │   - birth offspring     │
                                              └────────────┬────────────┘
                                                           │
                                          ┌────────────────┼────────────────┐
                                          ▼                ▼                ▼
                                     [genomes]      [generations]      [champions]
                                                           │
                                                  SSE event to UI ───► fitness curve tick
```

**The change stream on `fitness_evaluations` is load-bearing.** It is the heartbeat of the system — no polling, no cron, no scheduler. MongoDB-native event loop.

---

## 3. Module Layout

```
darwin/
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md          ← this document
├── .env.example             ← MONGODB_URI, VOYAGE_API_KEY, ANTHROPIC_API_KEY
├── src/darwin/
│   ├── __init__.py
│   ├── config.py            ← settings (population size, mutation rate, model names)
│   ├── db/
│   │   ├── client.py        ← AsyncIOMotorClient singleton + change-stream helper
│   │   ├── schemas.py       ← Pydantic models for all 6 collections
│   │   └── indexes.py       ← idempotent index creation incl. vector index on chunks
│   ├── genome/
│   │   ├── types.py         ← Genome dataclass, three nested gene layers
│   │   ├── factory.py       ← random_genome() — uniform sampling over gene space
│   │   ├── crossover.py     ← uniform crossover over gene fields
│   │   └── mutate.py        ← per-gene mutation operators (gaussian for floats, swap for enums)
│   ├── retrieval/
│   │   ├── embedder.py      ← Voyage-4 family wrapper, model selected by gene
│   │   ├── chunker.py       ← variant chunking helpers (already pre-chunked at seed time)
│   │   ├── retriever.py     ← gene-driven Atlas vector search + optional hybrid
│   │   └── reranker.py      ← Voyage rerank-2, optional per gene
│   ├── agents/
│   │   ├── runner.py        ← evaluate(genome, query) → writes fitness_evaluation
│   │   ├── blackboard.py    ← in-memory Blackboard dict, scoped to run_id
│   │   ├── coordinator.py   ← protocols: solo / vote / consult / debate
│   │   └── generator.py     ← Claude call to compose answer from chunks
│   ├── fitness/
│   │   ├── judge.py         ← Haiku LLM-judge: relevance, accuracy, coverage
│   │   └── score.py         ← composite_fitness(components, weights)
│   ├── evolution/
│   │   ├── conductor.py     ← main loop, consumes fitness_evaluations change stream
│   │   ├── selection.py     ← tournament_select(), elite_select()
│   │   ├── population.py    ← birth_offspring(), retire(), promote_to_champions()
│   │   └── lineage.py       ← parent_ids walker for family-tree endpoint
│   ├── api/
│   │   ├── server.py        ← FastAPI app, lifespan starts conductor
│   │   ├── routes.py        ← /query /population /lineage /fitness-curve /champions
│   │   └── events.py        ← SSE stream of evolution events for UI
│   └── demo/
│       ├── narrate.py       ← Rich-based terminal demo (fallback if UI breaks)
│       └── scripted_run.py  ← deterministic seeded run for the recorded video
├── ui/
│   └── streamlit_app.py     ← three-panel demo (curve / tree / live query)
├── scripts/
│   ├── seed_corpus.py       ← chunk + embed × 4 Voyage variants, write to chunks
│   ├── seed_queries.py      ← load eval set (20-30 Q&A pairs)
│   ├── seed_genesis.py      ← random gen-0 population (16 genomes)
│   ├── run_evolution.py     ← local dev entry point
│   └── record_demo.py       ← deterministic seeded run for video capture
└── tests/
    ├── test_genome.py       ← mutation preserves schema, crossover is symmetric
    ├── test_retrieval.py    ← gene → retrieval params mapping
    ├── test_fitness.py      ← composite math, judge wiring (mocked LLM)
    ├── test_evolution.py    ← single-generation rollover end-to-end (mocked Voyage)
    └── test_change_stream.py← change-stream consumer fires conductor
```

---

## 4. The Evolution Loop (algorithm)

```python
# api_server: query intake
async def handle_query(q_text: str, run_kind="evolve"):
    q = await db.queries.find_one_and_upsert({"text": q_text}, ...)
    pop = await db.genomes.find({"status": "alive"}).to_list(POP_SIZE)
    contestants = selection.tournament(pop, k=POP_PER_QUERY, by="fitness.composite")
    run_id = uuid4()
    blackboard = Blackboard(run_id, q_text, contestants)
    await asyncio.gather(*[
        agent_runner.evaluate(g, q, run_id, blackboard) for g in contestants
    ])
    final = coordinator.resolve(blackboard, protocol=majority_protocol(contestants))
    return final

# agent_runner.evaluate
async def evaluate(genome, query, run_id, blackboard):
    chunks = await retriever.retrieve(query.text, genome.retrieval_genes)   # ← Atlas Vector Search
    if genome.coordination_genes.protocol == "consult":
        await blackboard.publish_proposal(genome.id, partial_answer=summarize(chunks))
        peers = await blackboard.gather(timeout=genome.coordination_genes.timeout_ms)
        chunks = merge(chunks, peers)
    answer = await generator.compose(query.text, chunks, genome)
    components = await fitness.judge(answer, query.expected_facts)          # ← LLM judge
    composite = fitness.score(components, weights=DEFAULT_WEIGHTS)
    await db.fitness_evaluations.insert_one({                               # ← TRIGGERS CHANGE STREAM
        "genome_id": genome.id, "query_id": query.id,
        "generation": genome.generation, "run_id": run_id,
        "generated_answer": answer,
        "retrieval_trace": [{"chunk_id": c.id, "score": c.score, "position": i} for i,c in enumerate(chunks)],
        "coordination_trace": blackboard.snapshot_for(genome.id),
        "components": components, "composite_fitness": composite,
        "timestamp": now(),
    })

# conductor: change-stream consumer (single process, persistent)
async def watch_evaluations():
    async with db.fitness_evaluations.watch([{"$match": {"operationType":"insert"}}]) as stream:
        async for change in stream:
            gen = change["fullDocument"]["generation"]
            count = await db.fitness_evaluations.count_documents({"generation": gen})
            if count >= EVALS_PER_GENERATION_THRESHOLD and not await gen_already_evolved(gen):
                await evolve_generation(gen)

async def evolve_generation(gen):
    fitness_by_genome = await aggregate_mean_fitness_by_genome(gen)         # ← MongoDB aggregation pipeline
    elites = selection.elite(fitness_by_genome, k=ELITE_K)
    parents = selection.tournament(fitness_by_genome, k=N_PARENTS)
    offspring = []
    for _ in range(POP_SIZE - ELITE_K):
        p1, p2 = random.sample(parents, 2)
        child = mutate(crossover(p1, p2), rate=MUTATION_RATE)
        child["generation"] = gen + 1
        child["parent_ids"] = [p1["_id"], p2["_id"]]
        offspring.append(child)
    await db.genomes.update_many({"_id": {"$in": elite_ids}}, {"$set": {"generation": gen+1}})
    await db.genomes.update_many({"_id": {"$nin": survivor_ids}, "generation": gen}, {"$set": {"status":"retired"}})
    await db.genomes.insert_many(offspring)
    await db.generations.insert_one({                                       # ← time-series collection
        "generation": gen+1, "population_size": POP_SIZE,
        "best_fitness": max(fitness_by_genome.values()),
        "mean_fitness": mean(fitness_by_genome.values()),
        "diversity_index": gene_diversity(offspring),
        "selection": "tournament", "crossover_rate": 1.0, "mutation_rate": MUTATION_RATE,
        "created_at": now(),
    })
    await promote_champions(elites, gen)                                    # writes [champions]
    await emit_sse_event("generation.evolved", gen+1)
```

**Why change streams beat polling here:** the demo's "live evolution" feel comes from the UI updating the moment a generation rolls. Polling adds latency floor; change streams give us sub-100ms reactivity for free, and it's a feature MongoDB judges will recognize.

---

## 5. Multi-Agent Coordination Pattern

**Pattern:** in-memory **blackboard** scoped to `run_id`, materialized into the `coordination_trace` field of each fitness_evaluation doc on completion. We do NOT add a 7th MongoDB collection — schema is locked, and the blackboard's lifetime is the duration of one query (seconds), so persistence would be wasted writes.

```python
class Blackboard:
    run_id: str
    query: str
    proposals: dict[genome_id, {"draft": str, "confidence": float, "chunks": list[ChunkRef]}]
    votes: dict[genome_id, {"voted_for": genome_id, "reason": str}]
    final_answer: str | None
    protocol: Literal["solo", "vote", "consult", "debate"]
```

**Protocols (driven by `coordination_genes.protocol`):**
- **solo** — agent runs independently, no blackboard interaction. Baseline.
- **vote** — all agents draft answers in parallel; each then votes on best peer answer; majority wins.
- **consult** — agent A retrieves, posts retrieval to blackboard, agent B may pull A's chunks if confidence > threshold.
- **debate** — two-round: draft → critique → refine.

The `coordination_trace` persisted per-genome captures: which peers it consulted, votes cast, votes received. This is the **emergent specialization** narrative for the demo — we can show that one champion lineage developed "always consult genome X for legal queries."

**Why blackboard over agent-to-agent messaging:** simpler to implement in an afternoon, deterministic to test, naturally captures the "shared workspace" aesthetic that judges associate with multi-agent systems.

---

## 6. Demo Architecture

**UI: three panels (Streamlit, ~150 LOC)**

| Panel | Source | What it shows |
|---|---|---|
| **Fitness curve** | GET `/fitness-curve` (aggregation over `generations`) | Line chart, generation × {best, mean, diversity}. Updates via SSE on `generation.evolved`. |
| **Family tree** | GET `/lineage/<champion_id>` (recursive walk on `parent_ids`) | DAG of ancestor genomes with gene-diff highlighted at each branch. |
| **Live query** | POST `/query` then SSE | Input box → agents-running spinner → answer + retrieval trace + which genome won. |

**Endpoints (FastAPI):**
```
POST /query              { text } → { run_id, answer, winning_genome, fitness }
GET  /population         → current alive genomes with summary fitness
GET  /generations        → time-series of generation summaries
GET  /fitness-curve      → [{generation, best, mean, diversity}, ...]
GET  /lineage/{genome_id}→ ancestor DAG
GET  /champions          → hall of fame
GET  /events             → SSE stream of evolution events
```

**Minimal viable demo (terminal fallback):** `python -m darwin.demo.narrate` — Rich panel with:
- ASCII fitness sparkline that grows across generations
- Champion gene-diff vs. gen-0 random ancestor
- Single live query running against current best, showing retrieved chunks + answer

If Streamlit breaks at hour 5, this terminal is the demo. It's intentionally beautiful with Rich so it's still recordable.

---

## 7. Parallel Work Streams

| # | Stream | Owner | Hours | Hard deps | Deliverable |
|---|---|---|---|---|---|
| **A** | Atlas + corpus seeding | Human #1 | 1.5 | — | Atlas cluster live, indexes created (vector index on `chunks.embeddings.voyage_4`, time-series on `generations`), `chunks` populated with 4 embedding variants × ~500 chunks, `queries` seeded with 25 eval Q&A pairs |
| **B** | Genome + evolution engine | Human #2 + **alpha** | 3.0 | schemas.py from A (30min in) | `src/darwin/genome/*`, `src/darwin/evolution/*`, change-stream conductor, passing test_evolution.py with mocked Voyage |
| **C** | Retrieval + agent runner + judge | Human #3 + **beta** | 2.5 | schemas.py from A (30min in) | `src/darwin/retrieval/*`, `src/darwin/agents/*`, `src/darwin/fitness/*`, end-to-end `evaluate()` writing real fitness_evaluations |
| **D** | API server + SSE | **alpha** (after B@2h) | 1.0 | B+C joinable | FastAPI with all 7 endpoints, SSE wired to conductor events |
| **E** | UI (Streamlit) | **scout** | 2.0 | Mock data fixtures from B@1h, real API at hour 4.5 | `ui/streamlit_app.py` with three panels, polling fallback if SSE flakes |
| **F** | Demo recording + script | Human #1 (after A) | 1.0 | Terminal demo working (hour 4) | 90s video, narration script, live-anchor 15-30s plan |
| **G** | Tests + dress rehearsal | **reviewer** + **approver** | continuous | — | Smoke test suite, final 30-min dress rehearsal at hour 5 |

**Sync points:** hour 2 (schemas + corpus done), hour 4 (E2E single generation works), hour 5 (lock the build, dress rehearsal only).

**Critical path:** A → schemas → B/C in parallel → D → E → F.

---

## 8. Risks and Cut Lines

**Hour 3 cut (if behind):**
- Drop Streamlit, commit to terminal demo (Rich). Saves 2h of integration headaches.
- Drop debate protocol; keep only `solo` and `vote`. Still demonstrates multi-agent.

**Hour 5 cut (panic mode):**
- Drop multi-agent coordination entirely — single-genome fitness eval still demonstrates evolution, which is the headline.
- Drop SSE, just refresh the terminal output every 2 seconds.
- Use 8 genomes per generation instead of 16 — half the eval cost, evolution still visible.

**MVP that absolutely must work:**
1. Atlas with all 6 collections populated.
2. Genomes evolve over **≥3 generations** on real queries with real Voyage retrieval.
3. Fitness curve trends measurably upward (best fitness gen-3 > best fitness gen-0).
4. Terminal or UI shows one champion lineage with gene-diff vs ancestor.
5. One live query works end-to-end against the current best genome.

**Top failure modes:**
- **Voyage rate limits** during seeding — pre-embed corpus *before* hackathon if possible; if not, parallelize seeding with backoff.
- **Atlas vector index slow to build** — create indexes first thing, before any code.
- **Change stream auth/permissions** — test in hour 1 with a smoke script; fall back to a polling consumer if needed (5 LOC swap).
- **LLM judge is slow/expensive** — use Haiku 4.5, cap evaluations at 16 genomes × 5 queries = 80 per generation, parallelize with `asyncio.gather` + semaphore=8.
- **Demo machine WiFi at venue** — record video as backstop (deliverable F is non-negotiable).

---

## 9. The Demo Moment (60s arc)

| Time | Beat | What's on screen | What code/UI must exist |
|---|---|---|---|
| **0–10s** | Hook | Title card: "RAG is brittle. We don't tune retrieval — we **evolve** it." | Slide / Streamlit landing |
| **10–25s** | The genome | Zoom into a `genomes` document in MongoDB Compass / Streamlit panel — three gene layers visible, annotated | `genomes` populated; UI panel rendering one genome doc |
| **25–40s** | Evolution in motion | Fitness curve climbs across 5 generations as red genomes (low fitness) die and green ones (high fitness) reproduce | `/fitness-curve` endpoint + Streamlit line chart with color-coded population dots |
| **40–50s** | Emergent champion | Family tree zooms to current champion. Gene diff vs gen-0 ancestor highlighted: "Look — it discovered voyage-4-large + chunk_size=512 + rerank=on for technical queries." | `/lineage` endpoint + Streamlit graph; champions promoted correctly |
| **50–60s** | Live | Type a query → live retrieval → answer streams in. Caption: "This system wasn't designed. It was selected for." | `/query` endpoint working end-to-end |

**Live anchor (15–30s after video):** type a fresh query the audience suggests, show the live champion answering it. Backup: pre-staged query if WiFi dies.

---

## Opinionated choices (and why, in one sentence each)

- **Streamlit over Next.js** — 30 LOC vs 300, and we don't have a frontend specialist on the team.
- **Blackboard in-memory, not 7th collection** — schema is locked at 6, blackboard lifetime is seconds, persistence would be wasted writes.
- **Change streams over polling** — sub-100ms reactivity is free, and judges from MongoDB will explicitly look for change-stream usage.
- **Haiku 4.5 for the judge** — fast and cheap, judging is bounded-quality (we need consistent ranking, not perfect prose).
- **Async Python (Motor + httpx + asyncio.gather)** — the workload is I/O-bound (Voyage + Atlas + Anthropic), threading would just add complexity.
- **Pre-compute embeddings for all 4 Voyage variants at seed time** — gene picks an index, not a model invocation, so per-eval latency is one Atlas query, not one embed + one Atlas query.
- **Tournament + elite selection** — well-understood, hard to bug, demo-friendly because elite preservation guarantees fitness curve never drops.
- **Pre-recorded video + live anchor** — venue WiFi is the #1 demo killer; the video is the safety net, the live anchor is the wow.

---

```
RESULT:
- What was done: Produced a complete 9-section Darwin architecture proposal — component map, ASCII data flow, file-level module layout, evolution-loop pseudocode (with explicit MongoDB ops), multi-agent blackboard pattern, demo architecture (Streamlit primary + Rich terminal fallback), 7-stream parallel work plan for 3 humans + fleet over 5.5h, hour-3/hour-5 cut lines + MVP definition, and a beat-by-beat 60s demo narrative.
- Files changed: None — repo is not cloned in this workspace. Recommend committing this response as `darwin/ARCHITECTURE.md` (dispatch alpha or scout with --repo git@github.com:lindell-grantx/darwin.git).
- Verification: Cross-checked every section against the locked decisions in fleet memory — six-collection schema (genomes, generations, queries, fitness_evaluations, chunks, champions), Atlas + Voyage-4 + Python 3.12+ stack, three hackathon themes (adaptive retrieval primary, multi-agent secondary, prolonged coordination tertiary), 5.5h build window, 90s + live-anchor demo format. Pseudocode references the exact field names from the locked schema (retrieval_trace, components, composite_fitness, parent_ids, etc.). Work-stream dependencies form a valid DAG with critical path A → schemas → B/C → D → E → F.
- Open items:
  - DECISION NEEDED: Streamlit vs Next.js for UI (I picked Streamlit; flag if team has a frontend specialist who'd be faster in Next.js).
  - DECISION NEEDED: number of genomes per generation (proposed 16, cuttable to 8 at hour 5).
  - DECISION NEEDED: which 25 eval queries to seed — needs domain pick (technical docs? legal? mixed?). Suggest dispatching a scout task to draft the eval set in parallel with stream A.
  - Not addressed: deployment URL backstop (mentioned in fleet-memory build constraints) — recommend a separate stream after hour 4 to push api_server to a hosted target (Railway / Fly / Modal). Add as Stream H if we can spare scout cycles.
  - grantx-kb CLI is uncredentialed in this workspace (FLEET_SUPABASE_URL not set). Did not write this architecture as a knowledge entry; recommend conductor or human run the kb write.
```