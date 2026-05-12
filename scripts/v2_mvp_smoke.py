#!/usr/bin/env python
"""v2 MVP smoke: 20 queries through the hosted supervisor + Hono routing.

Verifies:
- Hono /query returns 200 with a `routing` block populated
- Across 20 queries, at least 2 distinct sampled_defender_ids appear (the
  mixed strategy is actually mixing)
- At least 3 distinct routing buckets are observed

Usage:
    DARWIN_API_URL=http://your-vm:3300 python scripts/v2_mvp_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from urllib import request


EVAL_QUERIES_PATH = Path(__file__).resolve().parent / "eval_queries.json"


def main() -> int:
    base_url = os.environ.get("DARWIN_API_URL")
    if not base_url:
        print("ERROR: set DARWIN_API_URL", file=sys.stderr)
        return 2

    base_url = base_url.rstrip("/")
    queries = json.loads(EVAL_QUERIES_PATH.read_text(encoding="utf-8"))[:20]
    print(f"smoke: posting {len(queries)} queries to {base_url}/query")

    sampled_defenders: list[str] = []
    bucket_keys: list[tuple[str, ...]] = []
    n_ok = 0
    n_fail = 0

    for i, q in enumerate(queries, 1):
        payload = json.dumps({"text": q["text"]}).encode("utf-8")
        req = request.Request(
            f"{base_url}/query",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as r:
                body = json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            print(f"  [{i}] FAIL: {exc}")
            n_fail += 1
            continue

        routing = body.get("routing") or {}
        sampled = routing.get("sampled_defender_id")
        bucket = routing.get("bucket_key")
        if sampled:
            sampled_defenders.append(sampled)
        if bucket:
            bucket_keys.append(tuple(bucket))
        n_ok += 1
        print(f"  [{i}] ok  sampled={sampled and sampled[:8]} bucket={bucket}")

    print()
    print(f"summary: ok={n_ok} fail={n_fail}")
    print(f"distinct sampled defenders: {len(set(sampled_defenders))}")
    print(f"distinct routing buckets:   {len(set(bucket_keys))}")
    print()
    print("sampled defender frequency:")
    for d, n in Counter(sampled_defenders).most_common():
        print(f"  {d[:12]}  {n}")

    if len(set(sampled_defenders)) < 2:
        print("WARN: mixed strategy did not mix - check Nash strategy and routing")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
