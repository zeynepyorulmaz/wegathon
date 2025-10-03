import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.core.logging import logger

async def chat_with_tools(
    messages: List[Dict[str, str]],
    tools: List[Dict[str, Any]],
    system: str | None = None
) -> Dict[str, Any]:
    """
    Call Anthropic's Messages API with tool use support.
    Returns the raw response JSON.
    """
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload: Dict[str, Any] = {
        "model": settings.anthropic_model,
        "max_tokens": 4096,
        "messages": messages,
    }
    
    if system:
        payload["system"] = system
    
    if tools:
        payload["tools"] = tools
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


async def chat(messages: List[Dict[str, str]], system: str | None = None) -> str:
    """
    Simpler wrapper for text-only chat (no tools).
    Returns just the text content.
    """
    result = await chat_with_tools(messages, [], system)
    content = result.get("content", [])
    for block in content:
        if block.get("type") == "text":
            return block.get("text", "")
    return ""

