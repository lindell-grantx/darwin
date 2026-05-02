# Darwin Demo Voiceover

Target length: 60-75 seconds.

## Script

Darwin is an evolutionary adaptive retrieval system. Instead of hand-designing one fixed RAG pipeline, Darwin keeps a population of retrieval strategies called genomes.

Each genome controls choices like the embedding model, chunk size, query transformation, reranking, and how agents coordinate. For the same technical question, multiple genomes retrieve evidence, generate answers, and compete.

The fitness judge scores each answer on relevance, accuracy, and coverage. Those scores become fitness. Stronger genomes survive, weaker genomes retire, and the next generation inherits better retrieval behavior.

In this demo, the dashboard shows the current population, the best and mean fitness over generations, the champion genome, and a live query tournament. The key idea is that Darwin can explain not only that answer quality improved, but also which retrieval and coordination choices were selected.

If the web UI is available, we show the same loop visually. If the UI or network fails, the terminal demo is the fallback: it still shows the population, fitness curve, genome changes, and winning answer in a deterministic run.

The demo moment is this: Darwin is not a single RAG configuration. It is a system that searches the design space of RAG strategies and evolves toward better answers.

## Pacing Notes

- First 10 seconds: explain the problem, fixed RAG pipelines are brittle.
- Next 20 seconds: explain genomes and competing retrieval strategies.
- Next 20 seconds: explain fitness scoring and evolution.
- Final 10-20 seconds: point at the dashboard and summarize the demo moment.
