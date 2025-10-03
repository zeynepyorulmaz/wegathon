from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from app.models.plan import PlanRequest, ReviseRequest, TripPlan
from app.services.planner import generate, revise
from app.services.ask import ask_questions
from app.tools.adapters import get_mcp_tools_schema

router = APIRouter(prefix="/api", tags=["planner"])


@router.post("/plan", response_model=TripPlan)
async def plan_endpoint(req: PlanRequest):
    try:
        return await generate(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/revise", response_model=TripPlan)
async def revise_endpoint(payload: Dict):
    try:
        plan = payload.get("plan")
        req = ReviseRequest(planId=payload.get("planId", ""), instruction=payload["instruction"])  # type: ignore
        return await revise(plan, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask_questions")
async def ask_endpoint(history: List[Dict]):
    try:
        content = await ask_questions(history)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools_endpoint() -> Dict[str, Any]:
    """
    List all available MCP tools from the server.
    Useful for debugging and discovering what tools are available.
    """
    try:
        tools = await get_mcp_tools_schema()
        return {
            "count": len(tools),
            "tools": [
                {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "parameters": list(tool.get("input_schema", {}).get("properties", {}).keys())
                }
                for tool in tools
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/refresh")
async def refresh_tools_endpoint() -> Dict[str, Any]:
    """
    Clear the MCP tools cache and fetch fresh tools from the server.
    Useful during development when MCP server tools change.
    """
    try:
        import app.tools.adapters as adapters
        adapters._cached_mcp_tools = None
        tools = await get_mcp_tools_schema()
        return {
            "success": True,
            "message": "Tools cache refreshed successfully",
            "count": len(tools),
            "tool_names": [tool.get("name") for tool in tools]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

