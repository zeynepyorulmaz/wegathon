from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from app.models.plan import PlanRequest, ReviseRequest, TripPlan
from app.models.parser_schemas import ParsePromptRequest, ParsedTripPrompt
from app.services.planner import generate, revise
from app.services.conversational_planner import chat_to_collect_trip_info, create_plan_from_conversation
from app.services.prompt_parser import parse_prompt
from app.tools.adapters import get_mcp_tools_schema
import uuid

router = APIRouter(prefix="/api", tags=["planner"])

# In-memory storage for AI-driven conversations (use Redis/DB in production)
ai_conversations: Dict[str, List[Dict[str, str]]] = {}


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


@router.post("/chat/start")
async def start_ai_chat(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start an AI-driven conversation to collect trip information.
    The AI will naturally ask for missing details.
    """
    try:
        user_message = data.get("message", "")
        language = data.get("language", "en")
        
        # Create new conversation
        session_id = str(uuid.uuid4())
        conversation_history = [
            {"role": "user", "content": user_message}
        ]
        
        # Get AI response
        ai_response, is_ready, collected_data = await chat_to_collect_trip_info(
            conversation_history,
            language
        )
        
        # Store conversation
        conversation_history.append({"role": "assistant", "content": ai_response})
        ai_conversations[session_id] = conversation_history
        
        return {
            "session_id": session_id,
            "message": ai_response,
            "ready_to_plan": is_ready,
            "collected_data": collected_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/continue")
async def continue_ai_chat(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Continue an AI-driven conversation.
    Send user's response and get next AI question or ready signal.
    """
    try:
        session_id = data.get("session_id")
        user_message = data.get("message", "")
        language = data.get("language", "en")
        
        if not session_id or session_id not in ai_conversations:
            raise HTTPException(status_code=404, detail="Session not found. Please start a new conversation.")
        
        # Get conversation history
        conversation_history = ai_conversations[session_id]
        
        # Add user message
        conversation_history.append({"role": "user", "content": user_message})
        
        # Get AI response
        ai_response, is_ready, collected_data = await chat_to_collect_trip_info(
            conversation_history,
            language
        )
        
        # Add AI response to history
        conversation_history.append({"role": "assistant", "content": ai_response})
        ai_conversations[session_id] = conversation_history
        
        return {
            "session_id": session_id,
            "message": ai_response,
            "ready_to_plan": is_ready,
            "collected_data": collected_data
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/create_plan")
async def create_plan_from_chat(data: Dict[str, Any]) -> TripPlan:
    """
    Create a travel plan from AI-collected conversation data.
    """
    try:
        collected_data = data.get("collected_data")
        language = data.get("language", "en")
        currency = data.get("currency", "TRY")
        
        if not collected_data:
            raise HTTPException(status_code=400, detail="No collected data provided")
        
        # Create the plan
        plan = await create_plan_from_conversation(
            collected_data,
            language,
            currency
        )
        
        return plan
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse", response_model=ParsedTripPrompt, summary="Parse natural language travel prompt")
async def parse_endpoint(req: ParsePromptRequest):
    """
    Parse a natural language travel prompt into structured data.
    
    Example input: "Eşimle 15 Ekim Berlin'e 3-4 gün gidelim, bütçe sonra."
    
    Returns detailed structured data including:
    - Departure and destination cities/countries
    - Travel dates and duration
    - Traveler composition and count
    - Budget information
    - Travel style and preferences
    """
    try:
        parsed = await parse_prompt(req.input, req.locale or "tr-TR")
        return parsed
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
