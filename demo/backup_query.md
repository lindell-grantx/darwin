# Darwin Backup Query

Use this if WiFi, Atlas, the API server, or the web UI is unavailable during the live demo.

## Backup Query

How do I create an Atlas Vector Search index for Voyage embeddings stored under `embeddings.voyage_4`?

## Expected Answer

Create an Atlas Vector Search index with a vector field whose path points to `embeddings.voyage_4`. Set `numDimensions` to match the Voyage embedding model, choose a similarity metric such as cosine, and query the index with the `$vectorSearch` aggregation stage.

## Expected Facts

- Atlas Vector Search requires a vector index.
- The vector field path should match the embedding field, for example `embeddings.voyage_4`.
- `numDimensions` must match the embedding model output dimension.
- Similarity can be cosine or another supported metric.
- Queries use the `$vectorSearch` aggregation stage.

## Backup Retrieved Chunks

1. Atlas Vector Search indexes vector fields and lets applications retrieve semantically similar documents through aggregation.
2. A vector index definition includes a field path, vector dimensions, and a similarity function.
3. The `$vectorSearch` stage accepts a query vector, index name, path, candidate count, and result limit.

## Backup Fitness Story

This query is useful because it tests whether Darwin can connect three pieces of evidence:

- MongoDB Atlas index syntax.
- Voyage embedding storage.
- Runtime vector search behavior.

A stronger genome should retrieve chunks about both index creation and `$vectorSearch`, then produce an answer that names the embedding path and dimensions explicitly.

## Fallback Command

```bash
python3 -m darwin.demo.scripted_run --seed 42 --generations 5 --delay 0.5 --plain
```

If the package has not been installed locally, run:

```bash
PYTHONPATH=src python3 -m darwin.demo.scripted_run --seed 42 --generations 5 --delay 0.5 --plain
```

## Fallback Talk Track

This is the same Darwin loop with deterministic data. Even without live services, we can still show the core concept: genomes compete, answer quality becomes fitness, and the champion genome reflects the best retrieval strategy found so far.
