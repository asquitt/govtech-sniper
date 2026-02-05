#!/usr/bin/env python3
"""
Basic load test for ingest + search endpoints.
"""

import asyncio
import os
import time

import httpx


async def run_probe(client: httpx.AsyncClient, base_url: str) -> None:
    await client.get(f"{base_url}/api/v1/rfps", params={"limit": 5})
    await client.post(
        f"{base_url}/api/v1/ingest/sam/quick-search",
        json={"keywords": "software", "limit": 1},
    )


async def main() -> int:
    base_url = os.getenv("RFP_API_URL", "http://localhost:8000")
    concurrency = int(os.getenv("RFP_LOAD_CONCURRENCY", "5"))
    iterations = int(os.getenv("RFP_LOAD_ITERATIONS", "10"))

    async with httpx.AsyncClient(timeout=30.0) as client:
        start = time.time()
        for _ in range(iterations):
            tasks = [run_probe(client, base_url) for _ in range(concurrency)]
            await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

    print(f"Completed {iterations * concurrency} probes in {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
