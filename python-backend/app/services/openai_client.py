from typing import List, Dict
import httpx
from openai import OpenAI
from app.core.config import settings


def _client() -> OpenAI | None:
    if settings.openai_api_key:
        return OpenAI(api_key=settings.openai_api_key)
    return None


async def chat(messages: List[Dict]) -> str:
    client = _client()
    if client:
        resp = client.chat.completions.create(
            model=settings.openai_model, messages=messages, temperature=0.6
        )
        content = resp.choices[0].message.content
        assert content is not None
        return content

    # Try multiple OpenAI-compatible proxy endpoints and header styles
    base = settings.weg_base_url.rstrip("/")
    candidate_paths = [
        "/v1/chat/completions",
        "/openai/v1/chat/completions",
        "/v1/openai/chat/completions",
    ]
    candidate_headers = []
    # Authorization header
    if settings.weg_api_key:
        candidate_headers.append({"Authorization": f"Bearer {settings.weg_api_key}", "Content-Type": "application/json"})
        candidate_headers.append({"x-api-key": settings.weg_api_key, "Content-Type": "application/json"})
    else:
        candidate_headers.append({"Content-Type": "application/json"})

    last_error = None
    async with httpx.AsyncClient(timeout=60) as http:
        for path in candidate_paths:
            url = f"{base}{path}"
            for hdrs in candidate_headers:
                try:
                    r = await http.post(
                        url,
                        json={"model": settings.openai_model, "messages": messages, "temperature": 0.6},
                        headers=hdrs,
                    )
                    r.raise_for_status()
                    data = r.json()
                    content = (
                        data.get("choices", [{}])[0].get("message", {}).get("content")
                        or data.get("content")
                    )
                    if content:
                        return content
                    last_error = f"No content in response at {url}"
                except Exception as e:
                    last_error = f"{url} -> {e}"
                    continue
    raise RuntimeError(last_error or "Proxy request failed")

