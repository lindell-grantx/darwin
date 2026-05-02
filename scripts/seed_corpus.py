#!/usr/bin/env python3
"""Seed the Darwin chunks collection.

Scrapes a curated set of MongoDB Atlas Vector Search, Voyage AI, and LangChain
documentation pages in parallel, chunks the text, embeds each chunk with all
four Voyage model variants in parallel, and bulk-inserts into Atlas.

Usage:
    MONGODB_URI=... VOYAGE_API_KEY=... python scripts/seed_corpus.py
    # Either env var can be omitted; falls back to GCP Secret Manager.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import logging
import re
import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from darwin.db.client import close_client, get_db  # noqa: E402
from darwin.db.schemas import EMBEDDING_MODELS, model_to_field  # noqa: E402
from darwin.retrieval.embedder import embed_documents  # noqa: E402


log = logging.getLogger(__name__)


CORPUS_URLS: dict[str, list[str]] = {
    "mongodb": [
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-stage/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-type/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/tutorials/vector-search-quick-start/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/create-embeddings/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/crud-embeddings/create-embeddings-automatic/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/ann-search-vs-enn-search/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/hybrid-search/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/manage-indexes/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-quantization/",
        "https://www.mongodb.com/docs/atlas/atlas-search/field-types/knn-vector/",
        "https://www.mongodb.com/docs/manual/changeStreams/",
        "https://www.mongodb.com/docs/manual/core/timeseries-collections/",
        "https://www.mongodb.com/docs/manual/aggregation/",
        "https://www.mongodb.com/docs/atlas/atlas-vector-search/tutorials/auto-quantize-with-voyage-ai/",
    ],
    "voyage": [
        "https://docs.voyageai.com/docs/embeddings",
        "https://docs.voyageai.com/docs/reranker",
        "https://docs.voyageai.com/docs/quickstart-tutorial",
        "https://docs.voyageai.com/docs/multimodal-embeddings",
        "https://docs.voyageai.com/docs/contextualized-chunk-embeddings",
        "https://docs.voyageai.com/docs/pricing",
        "https://docs.voyageai.com/docs/tokenization",
        "https://docs.voyageai.com/docs/faq",
        "https://docs.voyageai.com/docs/api-key-and-installation",
        "https://docs.voyageai.com/reference/embeddings-api",
        "https://docs.voyageai.com/reference/reranker-api",
        "https://blog.voyageai.com/2026/01/15/voyage-4/",
    ],
    "langchain": [
        "https://python.langchain.com/docs/concepts/rag/",
        "https://python.langchain.com/docs/concepts/retrievers/",
        "https://python.langchain.com/docs/concepts/agents/",
        "https://python.langchain.com/docs/concepts/tools/",
        "https://python.langchain.com/docs/concepts/messages/",
        "https://python.langchain.com/docs/concepts/text_splitters/",
        "https://python.langchain.com/docs/concepts/embedding_models/",
        "https://python.langchain.com/docs/concepts/vectorstores/",
        "https://python.langchain.com/docs/concepts/chat_models/",
        "https://python.langchain.com/docs/concepts/runnables/",
        "https://python.langchain.com/docs/tutorials/rag/",
        "https://python.langchain.com/docs/tutorials/qa_chat_history/",
    ],
}

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
MIN_CHUNK_LEN = 80
HTTP_TIMEOUT = 20.0


_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_BLANKLINE_RE = re.compile(r"\n\s*\n+")


def html_to_text(raw_html: str) -> str:
    text = _SCRIPT_STYLE_RE.sub(" ", raw_html)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = text.replace(" ", " ")
    text = _WS_RE.sub(" ", text)
    text = _BLANKLINE_RE.sub("\n\n", text)
    return text.strip()


def chunk_text(text: str) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        end = min(pos + CHUNK_SIZE, len(text))
        # Try to back off to a clean break (sentence end / newline)
        if end < len(text):
            for boundary in (". ", "\n", "? ", "! "):
                cut = text.rfind(boundary, pos + CHUNK_SIZE // 2, end)
                if cut != -1:
                    end = cut + len(boundary)
                    break
        snippet = text[pos:end].strip()
        if len(snippet) >= MIN_CHUNK_LEN:
            chunks.append(snippet)
        if end >= len(text):
            break
        pos = max(pos + 1, end - CHUNK_OVERLAP)
    return chunks


async def fetch_one(
    client: httpx.AsyncClient, source: str, url: str
) -> tuple[str, str, str] | None:
    try:
        response = await client.get(url)
    except httpx.HTTPError as exc:
        log.warning("fetch failed: %s -> %s", url, exc)
        return None
    if response.status_code != 200:
        log.warning("fetch %s -> HTTP %d", url, response.status_code)
        return None
    return source, url, response.text


async def fetch_all(urls: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    headers = {"User-Agent": "darwin-hackathon-seeder/0.1 (research)"}
    flat = [(s, u) for s, pages in urls.items() for u in pages]
    log.info("fetching %d URLs in parallel", len(flat))
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT, follow_redirects=True, headers=headers
    ) as client:
        results = await asyncio.gather(
            *(fetch_one(client, s, u) for s, u in flat),
            return_exceptions=False,
        )
    return [r for r in results if r is not None]


async def embed_all_models(texts: list[str]) -> dict[str, list[list[float]]]:
    """Run all 4 model embedding passes in parallel via thread executor."""

    log.info("embedding %d chunks across %d models in parallel", len(texts), len(EMBEDDING_MODELS))
    tasks = {
        model: asyncio.to_thread(embed_documents, texts, model)
        for model in EMBEDDING_MODELS
    }
    results = await asyncio.gather(*tasks.values())
    return dict(zip(tasks.keys(), results))


async def main(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    fetched = await fetch_all(CORPUS_URLS)
    log.info("fetched %d/%d pages", len(fetched), sum(len(v) for v in CORPUS_URLS.values()))

    chunks: list[dict] = []
    seen_texts: set[str] = set()
    per_source: dict[str, int] = {}
    duplicates = 0
    for source, url, html in fetched:
        text = html_to_text(html)
        page_chunks = chunk_text(text)
        kept = 0
        for i, snippet in enumerate(page_chunks):
            if snippet in seen_texts:
                duplicates += 1
                continue
            seen_texts.add(snippet)
            chunks.append(
                {
                    "doc_id": url,
                    "text": snippet,
                    "position": i,
                    "chunk_size": CHUNK_SIZE,
                    "source": source,
                    "embeddings": {},
                    "metadata": {"url": url, "length": len(snippet)},
                }
            )
            kept += 1
        per_source[source] = per_source.get(source, 0) + kept
    log.info(
        "produced %d unique chunks (%d duplicates dropped): %s",
        len(chunks),
        duplicates,
        per_source,
    )

    if not chunks:
        log.error("no chunks produced. aborting before embeddings.")
        return

    if args.dry_run:
        log.info("dry-run: skipping embedding + insert")
        return

    texts = [c["text"] for c in chunks]
    embeddings_per_model = await embed_all_models(texts)
    for model, vectors in embeddings_per_model.items():
        field = model_to_field(model)
        for chunk, vec in zip(chunks, vectors):
            chunk["embeddings"][field] = vec
        log.info("  %s done — dim=%d", model, len(vectors[0]))

    db = await get_db()
    if args.replace:
        deleted = (await db["chunks"].delete_many({})).deleted_count
        log.info("deleted %d existing chunks (--replace)", deleted)
    log.info("inserting %d chunks", len(chunks))
    insert_result = await db["chunks"].insert_many(chunks)
    log.info("inserted %d chunks", len(insert_result.inserted_ids))

    distinct_sources = sorted(await db["chunks"].distinct("source"))
    log.info("source coverage: %s", distinct_sources)
    sample = await db["chunks"].find_one()
    log.info(
        "sample: doc_id=%s position=%d source=%s embed_keys=%s",
        sample["doc_id"],
        sample["position"],
        sample["source"],
        list(sample["embeddings"].keys()),
    )

    await close_client()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Darwin corpus chunks into MongoDB.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + chunk only; skip embedding and insert.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing chunks before inserting (idempotent reseed).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
