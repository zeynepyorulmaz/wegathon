import asyncio
import json
import time
from typing import Any, Dict, List

import httpx


API_URL = "http://localhost:8000/parse"


TEST_PROMPTS: List[str] = [
    "Eşimle 15 Ekim Berlin’e 3-4 gün gidelim, bütçe sonra.",
    "Tek başıma Paris'e kasımda 5 gün.",
    "Ailecek Antalya'ya yaz tatilinde, 2 çocuk (5 ve 9).",
    "İstanbul'dan Roma'ya 1 Aralık, 1 hafta, 30 bin TL.",
    "New York'a önümüzdeki ay 4 gün, arkadaşlarımla.",
    "Tokyo mart ayı 2 hafta, sushi ve müze ağırlıklı.",
    "Balayına Maldivler, ocak, lüks otel, 7 gün.",
    "Amsterdam hafta sonu kaçamağı, gelecek hafta.",
    "Kapadokya 3 gün, sıcak hava balonu şart.",
    "Berlin → Amsterdam → Paris, 10 gün, ekonomik."
]


async def send_request(client: httpx.AsyncClient, prompt: str) -> Dict[str, Any]:
    payload = {"input": prompt, "locale": "tr-TR"}
    t0 = time.perf_counter()
    r = await client.post(API_URL, json=payload, timeout=120)
    elapsed = time.perf_counter() - t0
    try:
        data = r.json()
    except Exception:
        data = {"error": r.text}
    return {
        "status_code": r.status_code,
        "elapsed_sec": round(elapsed, 3),
        "prompt": prompt,
        "response": data,
    }


async def main() -> None:
    async with httpx.AsyncClient() as client:
        tasks = [send_request(client, p) for p in TEST_PROMPTS]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    # Log line-by-line
    for idx, res in enumerate(results, start=1):
        status = res["status_code"]
        elapsed = res["elapsed_sec"]
        print(f"[{idx:02d}] {status} in {elapsed}s :: {res['prompt']}")

    # Summary
    latencies = [r["elapsed_sec"] for r in results]
    ok = sum(1 for r in results if 200 <= r["status_code"] < 300)
    failed = len(results) - ok
    summary = {
        "count": len(results),
        "ok": ok,
        "failed": failed,
        "latency_sec": {
            "min": min(latencies),
            "max": max(latencies),
            "avg": round(sum(latencies) / len(latencies), 3),
        },
        "results": results,
    }
    print("\nJSON summary:\n" + json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())


