# Darwin Seed Queries

This folder describes the seeded evaluation queries for Darwin's first demo loop.

The actual seed file lives at `scripts/eval_queries.json`. These are not random user questions. They are a small benchmark set used to make different genomes compete on the same tasks, so Darwin can measure fitness, select stronger strategies, and evolve the population.

## Why These Queries Exist

Darwin needs a repeatable evaluation set:

1. Select several genomes from the current population.
2. Run each genome against the same query.
3. Generate an answer using that genome's retrieval and coordination genes.
4. Score the answer with the fitness judge.
5. Write the result to MongoDB.
6. Use the accumulated scores to select parents and create child genomes.

Without seeded queries, every run would be too random to show whether evolution is improving the system.

## What The Queries Cover

The seed set is designed to exercise the full Darwin concept:

- **Project summary**: Can the system explain Darwin clearly?
- **MongoDB architecture**: Can it identify which Atlas features are load-bearing?
- **Adaptive retrieval**: Can it compare Darwin to Self-RAG, Adaptive-RAG, and related systems?
- **Multi-agent collaboration**: Can it explain blackboard coordination and emergent specialization?
- **Durability**: Can it explain checkpointing, drift detection, memory decay, and recovery?
- **Fitness evaluation**: Can it describe how genomes are scored?
- **Demo narrative**: Can it surface the strongest pitch and visualization moments?
- **Risk handling**: Can it reason about hackathon failure modes and MVP cut lines?

These categories give the evolution loop enough variety to reward different retrieval strategies.

## Query Document Shape

Each query document looks like this:

```json
{
  "text": "How do I create an Atlas Vector Search index for embeddings stored under embeddings.voyage_4?",
  "ground_truth": "Create an Atlas Search vector index whose definition has a vector field at the nested path embeddings.voyage_4.",
  "expected_facts": [
    "Atlas Search vector index",
    "path embeddings.voyage_4",
    "type vector"
  ],
  "difficulty": "easy",
  "domain_tags": ["mongodb", "vector-search"]
}
```

## Field Guide

- `text`: The actual query given to a genome.
- `ground_truth`: A short canonical answer used by the judge.
- `expected_facts`: 3-7 atomic facts the judge should look for when scoring an answer.
- `difficulty`: Rough difficulty level: `easy`, `medium`, or `hard`.
- `domain_tags`: Lightweight labels for filtering, reporting, and visualization.

## How To Seed MongoDB

Set a MongoDB connection string, then run:

```bash
MONGO_URI="mongodb+srv://USER:PASSWORD@CLUSTER/darwin?retryWrites=true&w=majority" \
python3 scripts/seed_queries.py
```

To validate the file without writing to MongoDB:

```bash
python3 scripts/seed_queries.py --dry-run
```

The script writes to:

```text
database:   darwin
collection: queries
```

It is safe to run more than once because it uses `text` as a unique key and performs upserts.

## How The Evolution Loop Uses Them

For each seeded query:

```text
query -> selected genomes -> retrieval + answer -> judge score -> fitness_evaluations -> evolution
```

The important part is that all genomes answer the same query. This makes the fitness comparison fair.

Example:

```text
Query: "How is Darwin different from Adaptive-RAG?"

Genome A: raw vector retrieval, no rerank
Genome B: multi-query retrieval, rerank on
Genome C: HyDE retrieval, high confidence threshold

Judge scores:
Genome A: 0.61
Genome B: 0.84
Genome C: 0.73

Result:
Genome B is more likely to survive and reproduce.
```

## Demo Use

These queries are also useful for the live demo:

- Pick an easy query to explain the project quickly.
- Pick a hard comparison query to show why evolved retrieval matters.
- Pick a MongoDB query to highlight Atlas features.
- Pick a lineage/demo query to show the strongest storytelling moment.

Good live candidates are the easy MongoDB, Voyage, and LangChain questions in `scripts/eval_queries.json`.

## Security Note

Do not put MongoDB credentials, Voyage keys, Anthropic keys, or `.env` files in this folder. The hackathon repository must be public, so all secrets should stay in environment variables or a secure secret manager.
