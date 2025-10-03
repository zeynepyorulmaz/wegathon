from typing import Any, Dict, Tuple
import time
import httpx
from datetime import datetime
from app.core.config import settings

ToolResult = Tuple[Any, Dict[str, Any]]


def _diag(tool: str, start: float, ok: bool, error: str | None = None) -> Dict[str, Any]:
    return {"tool": tool, "ok": ok, "ms": int((time.time() - start) * 1000), "error": error}


def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.mcp_api_key:
        headers["Authorization"] = f"Bearer {settings.mcp_api_key}"
    return headers


async def _mcp_call(tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    url = settings.mcp_base_url.rstrip("/") + "/mcp"
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.post(url, json={"tool": tool, "arguments": arguments}, headers=_headers())
        r.raise_for_status()
        return r.json()


def _to_ddmmyyyy(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "")).strftime("%d.%m.%Y")
    except Exception:
        return iso


async def flights_search(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        # Map to MCP sample keys
        args = {
            "origin": params.get("origin"),
            "destination": params.get("destination"),
            "departure_date": _to_ddmmyyyy(params.get("departDateISO", "")),
            "return_date": _to_ddmmyyyy(params.get("returnDateISO", "")),
            "adults": params.get("adults", 1),
            "direct_flight": True,
        }
        data = await _mcp_call("flight_search", args)
        return data, _diag("flights.search", t0, True)
    except Exception as e:
        return {}, _diag("flights.search", t0, False, str(e))


async def hotels_search(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _mcp_call("hotel_search", params)
        return data, _diag("hotels.search", t0, True)
    except Exception as e:
        return {}, _diag("hotels.search", t0, False, str(e))


async def activities_search(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _mcp_call("activity_search", params)
        return data, _diag("activities.search", t0, True)
    except Exception as e:
        return [], _diag("activities.search", t0, False, str(e))


async def transport_search_intercity(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _mcp_call("bus_search", params)
        return data, _diag("transport.searchIntercity", t0, True)
    except Exception as e:
        return [], _diag("transport.searchIntercity", t0, False, str(e))


async def transport_search_local_passes(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = {"passes": []}
        return data, _diag("transport.searchLocalPasses", t0, True)
    except Exception as e:
        return [], _diag("transport.searchLocalPasses", t0, False, str(e))


async def weather_forecast(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = await _mcp_call("flight_weather_forecast", params)
        return data, _diag("weather.forecast", t0, True)
    except Exception as e:
        return [], _diag("weather.forecast", t0, False, str(e))


async def geo_resolve_city(query: str) -> ToolResult:
    t0 = time.time()
    try:
        data = await _mcp_call("geo_resolve_city", {"query": query})
        return data, _diag("geo.resolveCity", t0, True)
    except Exception as e:
        return {}, _diag("geo.resolveCity", t0, False, str(e))
