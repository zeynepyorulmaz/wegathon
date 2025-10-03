from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from app.models.plan import PlanRequest, ReviseRequest, TripPlan
from app.models.parser_schemas import ParsePromptRequest, ParsedTripPrompt
from app.models.conversation import (
    ConversationSession, ChatStartRequest, ChatContinueRequest, ChatResponse
)
from app.services.planner import generate, revise
from app.services.prompt_parser import parse_prompt
from app.services.conversation_manager import process_conversation_turn
from app.tools.adapters import get_mcp_tools_schema
from app.core.logging import logger
import uuid

router = APIRouter(prefix="/api", tags=["planner"])

# In-memory storage for conversation sessions (use Redis/DB in production)
conversation_sessions: Dict[str, ConversationSession] = {}


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


@router.post("/chat/start", response_model=ChatResponse)
async def start_ai_chat(req: ChatStartRequest) -> ChatResponse:
    """
    Start a new conversational trip planning session.
    
    The AI will:
    - Parse your request for trip details
    - Ask questions for missing information
    - Create a plan when ready
    - Handle revisions to the plan
    
    Every response includes the latest plan (if available).
    """
    try:
        # Create new session
        session_id = str(uuid.uuid4())
        session = ConversationSession(session_id=session_id)
        
        # Process first turn
        ai_message, plan, needs_more_info = await process_conversation_turn(
            session=session,
            user_message=req.initial_message,
            language=req.language,
            currency=req.currency
        )
        
        # Store session
        conversation_sessions[session_id] = session
        
        # Build response
        response = ChatResponse(
            session_id=session_id,
            message=ai_message,
            plan=plan.model_dump() if plan else None,
            collected_data=session.collected_data,
            needs_more_info=needs_more_info,
            conversation_complete=not needs_more_info and plan is not None
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in start_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/continue", response_model=ChatResponse)
async def continue_ai_chat(req: ChatContinueRequest) -> ChatResponse:
    """
    Continue an existing conversation.
    
    Send your message to:
    - Answer AI's questions
    - Request plan revisions (e.g., "2. günü daha rahat yap")
    - Ask for changes (e.g., "Daha ucuz otel bul")
    
    Every response includes the latest plan (if available).
    """
    try:
        # Get session
        if req.session_id not in conversation_sessions:
            raise HTTPException(status_code=404, detail="Session not found. Please start a new conversation.")
        
        session = conversation_sessions[req.session_id]
        
        # Process conversation turn
        ai_message, plan, needs_more_info = await process_conversation_turn(
            session=session,
            user_message=req.message,
            language="tr",  # Could be stored in session
            currency="TRY"  # Could be stored in session
        )
        
        # Update session
        conversation_sessions[req.session_id] = session
        
        # Build response
        response = ChatResponse(
            session_id=req.session_id,
            message=ai_message,
            plan=plan.model_dump() if plan else None,
            collected_data=session.collected_data,
            needs_more_info=needs_more_info,
            conversation_complete=not needs_more_info and plan is not None
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in continue_chat: {e}")
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
