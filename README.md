# Darwin

> Multi-agent retrieval architectures that evolve through natural selection.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Built at MongoDB Hackathon](https://img.shields.io/badge/Built%20at-MongoDB%20Agentic%20Evolution%20Hackathon-00ED64)](https://cerebralvalley.ai/e/mongoDB-hackathon)

Darwin is an evolutionary substrate for RAG systems. Instead of hand-tuning retrieval pipelines — chunking strategies, similarity functions, reranking approaches, multi-agent collaboration protocols — Darwin encodes these choices as parameterized **genomes** and lets natural selection discover what works for your corpus and query patterns.

The core claim: **multi-agent coordination protocols can be discovered through evolution rather than designed.**

## Use cases

**Internal knowledge base ("company brain").** Your company has a docs corpus, a Slack export, and recurring "how do we do X here?" questions. Every RAG implementer faces the same five decisions: chunking strategy, similarity function, embedding dimensions, quantization, and reranking approach ([Pete Johnson, MongoDB.local SF 2026](https://www.youtube.com/watch?v=YqQ0laSZCxM)). Teams spend weeks tuning these by hand. Darwin encodes them as genes and evolves the optimal configuration for your specific corpus and query distribution — including multi-agent collaboration protocols that emerge from selection pressure rather than manual design.

**Other applications:** customer support deflection, technical documentation Q&A, regulatory and compliance lookup — anywhere you have a stable corpus, recurring query patterns, and measurable downstream answer quality.

## How it works

Darwin represents each retrieval strategy as a three-layer **genome** stored as a MongoDB document:

| Layer | What it encodes | Example genes |
|-------|----------------|---------------|
| **Retrieval** | How documents are found | Embedding model, chunk size, query transformation, reranking approach |
| **Coordination** | How agents collaborate | Broadcasting behavior, context sharing threshold, deference rules, consensus mode |
| **Durability** | How state persists across long runs | Checkpoint frequency, drift detection, memory decay, recovery strategy |

A population of genomes competes on incoming queries. An LLM judge scores each agent's retrieval quality. The population evolves through tournament selection, crossover, and mutation. Over generations, Darwin discovers retrieval architectures that no human designed.

```mermaid
graph LR
    Q[Query] --> H[Hono API<br/>Node.js]
    H -->|query_runs| M[(MongoDB Atlas)]
    M -->|change stream| P[Python Supervisor<br/>Evolution Engine]
    P -->|embeddings| V[Voyage AI]
    P -->|judge + generate| A[Claude API]
    P -->|fitness, genomes,<br/>generations| M
    M -->|change stream| H
    H -->|SSE events| UI[Browser UI]
```

**Components:**
- **Hono API** (`server/`) — TypeScript API server. Accepts queries, streams evolution events to the browser via SSE.
- **Python Supervisor** (`src/darwin/`, `scripts/`) — Evolution engine. Runs agent evaluations, fitness scoring, selection, crossover, and mutation. Communicates with the Hono server through MongoDB change streams.
- **Browser UI** (`frontend/`) — Vite + React dashboard. Shows fitness curves, family trees, genome cards, and live query results.
- **MongoDB Atlas** — The evolutionary substrate. Stores genomes, fitness evaluations, generations, champions, and evolution events. Change streams drive the event loop.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full component map and collection schemas.

## Quickstart

### Prerequisites

- Node.js 24+
- Python 3.12+
- A [MongoDB Atlas](https://www.mongodb.com/atlas) cluster (free tier works)
- A [Voyage AI](https://www.voyageai.com/) API key (for embeddings and reranking)
- An [Anthropic](https://console.anthropic.com/) API key (for the LLM judge and answer generator) — or a GCP project with Vertex AI enabled

### Install

```bash
git clone https://github.com/lindell-grantx/darwin.git
cd darwin
npm run install:all
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

### Configure

```bash
cp server/.env.example server/.env
```

Edit `server/.env` and fill in:

```
MONGODB_URI=mongodb+srv://USER:PASSWORD@YOUR-CLUSTER/darwin?retryWrites=true&w=majority
VOYAGE_API_KEY=your-voyage-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

For the Python side, export the same variables in your shell:

```bash
export MONGODB_URI="mongodb+srv://..."
export VOYAGE_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

### Seed

```bash
python scripts/seed_corpus.py
python scripts/seed_queries.py
```

### Run

In one terminal (Hono API + React frontend):

```bash
npm run dev
```

In another terminal (Python evolution engine):

```bash
python scripts/run_all.py
```

Open [http://localhost:5173](http://localhost:5173) and watch the population evolve.

## Project layout

```
darwin/
├── server/          # Hono API (TypeScript) — query endpoint, SSE, MongoDB reads
│   └── src/
├── frontend/        # Vite + React dashboard — fitness curves, family trees, live queries
│   └── src/
├── src/darwin/      # Python evolution engine
│   ├── agents/      # Coordinator, generator, runner (multi-agent eval)
│   ├── api/         # FastAPI service for synchronous evaluation
│   ├── db/          # MongoDB client, schemas, indexes
│   ├── evolution/   # Conductor, selection, population, lineage
│   ├── fitness/     # LLM judge, scoring, eval-split
│   ├── genome/      # Crossover, mutation, factory, type definitions
│   ├── llm/         # Vertex AI / Anthropic client wrapper
│   ├── lib/         # Shared utilities (secret resolution)
│   └── retrieval/   # Embedder, reranker, retriever
├── scripts/         # CLI tools: seed corpus, seed queries, run evolution loop
├── tests/           # Smoke tests
└── docs/            # Architecture documentation
```

## Background and inspiration

Darwin was built at the [MongoDB Agentic Evolution Hackathon](https://cerebralvalley.ai/e/mongoDB-hackathon) in London on May 2, 2026.

The project sits at the intersection of three research threads:

**Evolutionary computation for information retrieval.** Genetic algorithms and genetic programming have been applied to classical IR — evolving ranking functions ([ARRANGER/TREC](https://trec.nist.gov/pubs/trec12/papers/vatech.robust.pdf)), optimizing document similarity ([arXiv 2502.19437](https://arxiv.org/html/2502.19437v1)), and multi-objective search ([PPSN 2024](https://arxiv.org/abs/2401.07454)). But nobody has applied population-based evolutionary search to modern RAG pipelines, where the search space includes embedding models, chunking strategies, reranking, and multi-agent coordination protocols.

**Adaptive RAG.** Systems like [CRAG](https://arxiv.org/abs/2401.15884), [Self-RAG](https://arxiv.org/abs/2310.11511), and [Adaptive-RAG](https://arxiv.org/abs/2403.14403) make retrieval reactive — routing queries by complexity, triggering fallbacks on low confidence. But none of them learn from outcomes in a closed loop. None treat retrieval strategies as first-class evolvable objects. The closest conceptual neighbor is [EvoRAG](https://arxiv.org/abs/2604.15676) (April 2025), which propagates feedback scores back to knowledge-graph triplets, achieving 7.34% improvement over GraphRAG — but it operates on graph structure, not pipeline configuration, and isn't population-based.

**Multi-agent coordination.** The [LbMAS blackboard architecture](https://arxiv.org/abs/2507.01701) showed 13–57% improvement over master-slave and RAG baselines through shared-memory coordination. The ["Theater of Mind" (GWA)](https://arxiv.org/abs/2604.08206) architecture demonstrated event-driven broadcasting with entropy-based deadlock breaking. CrewAI, AutoGen, MetaGPT, and Swarm all orchestrate agent collaboration — but none of them evolve their coordination protocols. Darwin's coordination genes (broadcasting, deference, consensus, specialization) are subject to the same selection pressure as retrieval genes, so the system discovers which collaboration patterns produce the best answers.

The only existing open-source project that genuinely merges evolutionary algorithms with a RAG paradigm is [RAG-SR](https://github.com/hengzhe-zhang/RAG-SR) (ICLR 2025), which uses population-based search for symbolic regression — a different domain entirely.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, branch conventions, and how to submit a pull request.

## About

Origins: prior research at t5 labs (RAG benchmarking and evolutionary search prototypes); implementation at the MongoDB Agentic Evolution Hackathon (London, May 2 2026). Built by [Lindell Cumes](https://github.com/lindell-grantx), [Andrey](https://github.com/Systerr), and [Liangxiao LI](https://github.com/Liangxiao-LI). Maintained as open research from [GrantX](https://grantx.io).

## License

[MIT](LICENSE)
