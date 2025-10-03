from typing import Any, Dict, Tuple, List
import time
import httpx
from datetime import datetime
from app.core.config import settings
from app.core.logging import logger

ToolResult = Tuple[Any, Dict[str, Any]]
_rpc_id = 1
_cached_mcp_tools: List[Dict[str, Any]] | None = None


async def get_mcp_tools_schema() -> List[Dict[str, Any]]:
    """
    Returns MCP tool definitions in Anthropic's tool schema format for function calling.
    Fetches available tools dynamically from MCP server and caches them.
    Falls back to hardcoded tools if server fetch fails.
    """
    global _cached_mcp_tools
    
    # Use cache if available
    if _cached_mcp_tools is not None:
        return _cached_mcp_tools
    
    # Try to fetch from MCP server
    logger.info("Fetching available tools from MCP server...")
    mcp_tools = await fetch_mcp_tools_from_server()
    
    if not mcp_tools:
        logger.warning("Failed to fetch tools from MCP server. Proceeding without MCP tools (plan will be AI-generated only).")
        _cached_mcp_tools = []
        return []
    
    # Convert MCP tools to Anthropic format
    anthropic_tools = [convert_mcp_tool_to_anthropic(tool) for tool in mcp_tools]
    _cached_mcp_tools = anthropic_tools
    logger.info(f"Successfully loaded {len(anthropic_tools)} tools from MCP server: {[t['name'] for t in anthropic_tools]}")
    return anthropic_tools


def _diag(tool: str, start: float, ok: bool, error: str | None = None) -> Dict[str, Any]:
    return {"tool": tool, "ok": ok, "ms": int((time.time() - start) * 1000), "error": error}


def _is_proxy(base_url: str) -> bool:
    u = base_url.lower()
    return "localhost" in u or "127.0.0.1" in u


def _headers() -> Dict[str, str]:
    base = settings.mcp_base_url
    if _is_proxy(base):
        # MCP proxy server expects specific headers
        hdrs = {
            "Content-Type": "application/json",
            "accept": "application/json, text/event-stream",
            "authorization": "123Bearer",  # Enuygun MCP proxy format
            "mcp-protocol-version": "2025-06-18"
        }
        if settings.mcp_api_key:
            hdrs["x-mcp-proxy-auth"] = f"Bearer {settings.mcp_api_key}"
        return hdrs
    # Direct mode (OAuth bearer)
    hdrs = {"Content-Type": "application/json"}
    if settings.mcp_api_key:
        hdrs["Authorization"] = f"Bearer {settings.mcp_api_key}"
    return hdrs


async def _mcp_call(tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call MCP tool using full MCP client with protocol handling.
    """
    try:
        from app.services.mcp_client import get_mcp_client
        mcp_client = get_mcp_client()
        result = await mcp_client.call_tool(tool, arguments)
        return result
    except Exception as e:
        logger.error(f"MCP tool call failed: {e}")
        return {"error": str(e)}


async def fetch_mcp_tools_from_server() -> List[Dict[str, Any]]:
    """
    Fetch available tools from MCP server using full MCP protocol.
    Returns list of tools in MCP format.
    """
    try:
        # Use full MCP client with initialize handshake
        from app.services.mcp_client import get_mcp_client
        mcp_client = get_mcp_client()
        tools = await mcp_client.list_tools()
        return tools
    except Exception as e:
        logger.warning(f"Failed to fetch MCP tools from server: {e}")
        return []


def convert_mcp_tool_to_anthropic(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MCP tool format to Anthropic tool schema format.
    MCP format: {name, description, inputSchema}
    Anthropic format: {name, description, input_schema}
    """
    return {
        "name": mcp_tool.get("name", "unknown_tool"),
        "description": mcp_tool.get("description", "No description available"),
        "input_schema": mcp_tool.get("inputSchema", {"type": "object", "properties": {}}),
    }


def _to_ddmmyyyy(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "")).strftime("%d.%m.%Y")
    except Exception:
        return iso


def _to_yyyymmdd(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "")).strftime("%Y-%m-%d")
    except Exception:
        return iso


async def flights_search(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
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
        args = {
            "destination_name": params.get("city") or params.get("destination") or "",
            "check_in_date": _to_ddmmyyyy(params.get("checkInISO", "")),
            "check_out_date": _to_ddmmyyyy(params.get("checkOutISO", "")),
            "adults": params.get("occupants") or params.get("adults") or 1,
            "children": params.get("children") or [],
            "rooms": params.get("rooms") or 1,
        }
        data = await _mcp_call("hotel_search", args)
        return data, _diag("hotels.search", t0, True)
    except Exception as e:
        return {}, _diag("hotels.search", t0, False, str(e))


async def activities_search(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        data = {"activities": []}
        return data, _diag("activities.search", t0, True)
    except Exception as e:
        return [], _diag("activities.search", t0, False, str(e))


async def transport_search_intercity(params: Dict[str, Any]) -> ToolResult:
    t0 = time.time()
    try:
        args = {
            "origin": params.get("originCity") or params.get("origin") or "",
            "destination": params.get("destinationCity") or params.get("destination") or "",
            "departure_date": _to_ddmmyyyy(params.get("dateISO", "")),
            "adults": params.get("adults", 1),
            "children": params.get("children", 0),
        }
        data = await _mcp_call("bus_search", args)
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
        args = {
            "location": params.get("city") or params.get("destination") or params.get("origin") or "",
            "start_date": _to_yyyymmdd(params.get("startDateISO", "")),
            "end_date": _to_yyyymmdd(params.get("endDateISO", "")) if params.get("endDateISO") else None,
        }
        data = await _mcp_call("flight_weather_forecast", args)
        return data, _diag("weather.forecast", t0, True)
    except Exception as e:
        return [], _diag("weather.forecast", t0, False, str(e))


async def geo_resolve_city(query: str) -> ToolResult:
    t0 = time.time()
    try:
        return {}, _diag("geo.resolveCity", t0, True)
    except Exception as e:
        return {}, _diag("geo.resolveCity", t0, False, str(e))


async def bus_search(params: Dict[str, Any]) -> ToolResult:
    """Search for intercity bus routes between cities."""
    t0 = time.time()
    try:
        args = {
            "origin": params.get("origin") or params.get("originCity") or "",
            "destination": params.get("destination") or params.get("destinationCity") or "",
            "departure_date": _to_ddmmyyyy(params.get("departDateISO") or params.get("dateISO", "")),
            "adults": params.get("adults", 1),
            "children": params.get("children") or [],
        }
        data = await _mcp_call("bus_search", args)
        return data, _diag("bus.search", t0, True)
    except Exception as e:
        return {}, _diag("bus.search", t0, False, str(e))
