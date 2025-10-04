import httpx
import asyncio
from typing import List, Dict, Any
from app.core.config import settings
from app.core.logging import logger

class RateLimitError(Exception):
    """Raised when API rate limit is hit"""
    pass

async def chat_with_tools(
    messages: List[Dict[str, str]],
    tools: List[Dict[str, Any]],
    system: str | None = None,
    max_retries: int = 3,
    base_delay: float = 2.0
) -> Dict[str, Any]:
    """
    Call Anthropic's Messages API with tool use support.
    Implements exponential backoff for rate limiting.
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
    
    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited - exponential backoff
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited (429). Retry {attempt + 1}/{max_retries} after {delay}s...")
                
                # Check for retry-after header
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    try:
                        delay = float(retry_after)
                        logger.info(f"Using Retry-After header: {delay}s")
                    except ValueError:
                        pass
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    last_error = e
                    continue
                else:
                    logger.error(f"Max retries reached. Giving up.")
                    raise RateLimitError("API rate limit exceeded after retries") from e
            else:
                # Other HTTP errors - don't retry
                logger.error(f"HTTP error {e.response.status_code}: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error calling Anthropic API: {e}")
            raise
    
    # Should not reach here, but if we do, raise the last error
    if last_error:
        raise last_error
    raise Exception("Failed to call Anthropic API")


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

