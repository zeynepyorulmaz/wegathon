from typing import Any, Dict, Tuple
import time
import httpx
from app.core.config import settings

ToolResult = Tuple[Any, Dict[str, Any]]


def _diag(tool: str, start: float, ok: bool, error: str | None = None) -> Dict[str, Any]:
    return {"tool": tool, "ok": ok, "ms": int((time.time() - start) * 1000), "error": error}


def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.mcp_api_key:
        headers["Authorization"] = f"Bearer {settings.mcp_api_key}"
    return headers


async def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.post(settings.mcp_base_url + path, json=payload, headers=_headers())
        r.raise_for_status()
        return r.json()


async def flights_search(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _post(settings.mcp_flights_path, params)
        return data, _diag("flights.search", t0, True)
    except Exception as e:
        return {}, _diag("flights.search", t0, False, str(e))


async def hotels_search(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _post(settings.mcp_hotels_path, params)
        return data, _diag("hotels.search", t0, True)
    except Exception as e:
        return {}, _diag("hotels.search", t0, False, str(e))


async def activities_search(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _post(settings.mcp_activities_path, params)
        return data, _diag("activities.search", t0, True)
    except Exception as e:
        return [], _diag("activities.search", t0, False, str(e))


async def transport_search_intercity(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _post(settings.mcp_transport_intercity_path, params)
        return data, _diag("transport.searchIntercity", t0, True)
    except Exception as e:
        return [], _diag("transport.searchIntercity", t0, False, str(e))


async def transport_search_local_passes(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _post(settings.mcp_transport_localpasses_path, params)
        return data, _diag("transport.searchLocalPasses", t0, True)
    except Exception as e:
        return [], _diag("transport.searchLocalPasses", t0, False, str(e))


async def weather_forecast(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _post(settings.mcp_weather_path, params)
        return data, _diag("weather.forecast", t0, True)
    except Exception as e:
        return [], _diag("weather.forecast", t0, False, str(e))


async def geo_resolve_city(query: str) -> ToolResult:
    t0 = time.time()
    try:
        data = await _post(settings.mcp_geo_path, {"query": query})
        return data, _diag("geo.resolveCity", t0, True)
    except Exception as e:
        return {}, _diag("geo.resolveCity", t0, False, str(e))
