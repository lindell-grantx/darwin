# Darwin Terminal Demo

This folder contains the DAR-16 terminal fallback demo.

It gives the team a runnable command-line demo for Darwin's core story:

1. A population of retrieval strategies competes.
2. Each strategy is represented as a genome.
3. Query results are scored as fitness.
4. Stronger genomes become champions.
5. Later generations show better retrieval behavior.

The terminal demo is useful if the web UI is not ready, but it is also useful as a developer-facing observability tool.

## Files

```text
src/darwin/demo/
├── narrate.py        # Live or preview terminal dashboard
└── scripted_run.py   # Deterministic generation-by-generation demo run
```

## Current Data Modes

`narrate.py` supports three data sources:

- Deterministic preview data, which works without external services.
- API data from `DARWIN_API_URL`, when the backend is running.
- MongoDB data from `MONGODB_URI` or `MONGO_URI`, when Motor is installed.

If neither API nor MongoDB is configured, the demo falls back to deterministic preview data.

## Running The Demo

Because the repo currently uses a `src/` Python layout without package metadata, run these commands with `PYTHONPATH=src`.

### One-Shot Preview

```bash
PYTHONPATH=src python3 -m darwin.demo.narrate --preview --once
```

Use this for a quick sanity check. It renders one self-explanatory snapshot.

### Live One-Shot

```bash
PYTHONPATH=src python3 -m darwin.demo.narrate --live --once
```

If `DARWIN_API_URL` or `MONGODB_URI` is configured, this reads live state. Otherwise it uses deterministic preview data.

### Scripted Recording Run

```bash
PYTHONPATH=src python3 -m darwin.demo.scripted_run --seed 42 --generations 5 --delay 0.5 --plain
```

Use this for rehearsal or backup recording. It prints a deterministic generation-by-generation story from generation 0 to generation 5.

### API-Backed Mode

```bash
DARWIN_API_URL=http://localhost:3000 \
PYTHONPATH=src python3 -m darwin.demo.narrate --live --once
```

This reads from the backend API.

### MongoDB-Backed Mode

```bash
MONGODB_URI="mongodb+srv://..." \
PYTHONPATH=src python3 -m darwin.demo.narrate --live --once
```

This reads directly from MongoDB. It requires `motor`.

## Rich vs Plain Output

The demo uses Rich when `rich` is installed.

If `rich` is not installed, it falls back to plain terminal output. The plain fallback is intentional so the demo still runs on a fresh machine.

Install Rich to enable the polished dashboard layout:

```bash
python3 -m pip install rich
```

## How To Explain The Output

The output is organized into five sections.

### 1. Population State

Shows the current generation and active genome count.

Example:

```text
Current generation: 5
Active genomes: 24
```

Meaning: Darwin is not running one fixed RAG pipeline. It is evolving a population of retrieval strategies.

### 2. Fitness Over Generations

Shows best and mean fitness.

```text
Best fitness  0.42 -> 0.77
Mean fitness  0.31 -> 0.57
```

Meaning:

- Best fitness shows the strongest strategy improving.
- Mean fitness shows the whole population improving, not only one lucky genome.

Fitness is a 0-1 judge score for answer quality.

### 3. Champion Genome

Shows the current winning strategy and how it differs from the generation-0 baseline.

Example:

```text
retrieval_genes.embedding: voyage-4-large (was voyage-3)
retrieval_genes.chunk_size: 512 (was 256)
retrieval_genes.rerank: True (was False)
```

Meaning: the system can explain what changed, not only that the score improved.

### 4. Live Query Tournament

Shows multiple genome strategies evaluating the same query.

Example:

```text
alpha: retrieving... ok
beta: reranking... ok
gamma: consulting... ok
```

Meaning: Darwin compares strategies on the same task and selects the strongest answer.

### 5. Winning Answer

Shows the answer produced by the winning genome.

Meaning: retrieval quality feeds into answer quality, and answer quality becomes fitness for future generations.

## 30-Second Talk Track

Darwin is an evolutionary adaptive retrieval system. Instead of hand-designing one RAG pipeline, it keeps a population of retrieval strategies called genomes. Each genome controls retrieval settings like embedding model, chunk size, reranking, top-k, and coordination behavior. The system runs the same query through competing genomes, scores the answers, and uses those scores as fitness. Over generations, stronger strategies survive and the population improves. This terminal demo shows that loop: population state, fitness improvement, champion genome changes, query tournament, and winning answer.

## Verification

Commands used to verify this implementation:

```bash
PYTHONPATH=src python3 -m py_compile src/darwin/demo/narrate.py src/darwin/demo/scripted_run.py
PYTHONPATH=src python3 -m darwin.demo.narrate --preview --once
PYTHONPATH=src python3 -m darwin.demo.narrate --live --once
PYTHONPATH=src python3 -m darwin.demo.scripted_run --seed 42 --generations 5 --delay 0.5 --plain
```
