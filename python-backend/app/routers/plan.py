from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from app.models.plan import PlanRequest, ReviseRequest, TripPlan
from app.models.parser_schemas import ParsePromptRequest, ParsedTripPrompt
from app.models.conversation import (
    ConversationSession, ChatStartRequest, ChatContinueRequest, ChatResponse
)
from app.models.interactive_plan import InteractivePlan
from app.services.planner import generate, revise
from app.services.prompt_parser import parse_prompt
from app.services.conversation_manager import process_conversation_turn
from app.services.plan_transformer import transform_to_interactive
from app.tools.adapters import get_mcp_tools_schema
from app.core.logging import logger
import uuid

router = APIRouter(prefix="/api")

# In-memory storage for conversation sessions (use Redis/DB in production)
conversation_sessions: Dict[str, ConversationSession] = {}


@router.post(
    "/plan",
    response_model=TripPlan,
    tags=["Planning"],
    summary="Generate Travel Plan",
    description="Create a comprehensive travel plan from a natural language prompt",
    response_description="Complete trip plan with flights, hotels, activities, and itinerary"
)
async def plan_endpoint(req: PlanRequest):
    """
    Generate a complete travel plan from a text prompt.
    
    **Example Request:**
    ```json
    {
      "prompt": "Istanbul to Berlin, 3 days, 2 people, budget-friendly",
      "language": "tr",
      "currency": "EUR"
    }
    ```
    
    **Features:**
    - Real-time MCP data (flights, hotels, weather, bus)
    - AI-generated day-by-day itinerary
    - Price breakdown and total estimation
    - Weather-adapted activities
    """
    try:
        return await generate(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/revise",
    response_model=TripPlan,
    tags=["Planning"],
    summary="Revise Existing Plan",
    description="Modify an existing travel plan based on natural language instructions"
)
async def revise_endpoint(payload: Dict):
    """
    Revise an existing travel plan with natural language instructions.
    
    **Example Request:**
    ```json
    {
      "plan": { ...existing plan... },
      "instruction": "Make day 2 more relaxed, remove museums"
    }
    ```
    
    **Common Instructions:**
    - "Make it cheaper"
    - "Add more cultural activities"
    - "Find better hotels"
    - "Make day 2 more relaxed"
    """
    try:
        plan = payload.get("plan")
        req = ReviseRequest(planId=payload.get("planId", ""), instruction=payload["instruction"])  # type: ignore
        return await revise(plan, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tools",
    tags=["Tools"],
    summary="List Available MCP Tools",
    description="Get all available tools from the MCP server"
)
async def list_tools_endpoint() -> Dict[str, Any]:
    """
    List all available MCP tools from the server.
    
    Returns tool names, descriptions, and required parameters.
    Useful for debugging and discovering what tools are available.
    
    **Response Example:**
    ```json
    {
      "count": 4,
      "tools": [
        {
          "name": "flight_search",
          "description": "Search for flights",
          "parameters": ["origin", "destination", "departure_date", ...]
        }
      ]
    }
    ```
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


@router.post(
    "/tools/refresh",
    tags=["Tools"],
    summary="Refresh MCP Tools Cache",
    description="Clear cache and fetch fresh tools from MCP server"
)
async def refresh_tools_endpoint() -> Dict[str, Any]:
    """
    Clear the MCP tools cache and fetch fresh tools from the server.
    
    Useful during development when MCP server tools change.
    The tools are normally cached for performance.
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


@router.post(
    "/chat/start",
    response_model=ChatResponse,
    tags=["Conversation"],
    summary="Start AI Conversation",
    description="Begin a conversational trip planning session with AI guidance"
)
async def start_ai_chat(req: ChatStartRequest) -> ChatResponse:
    """
    Start a new conversational trip planning session.
    
    **Example Request:**
    ```json
    {
      "initial_message": "Berlin 3 gün",
      "language": "tr",
      "currency": "EUR"
    }
    ```
    
    **The AI will:**
    - Parse your request for trip details
    - Ask questions for missing information (dates, travelers, etc.)
    - Create a plan when all details are collected
    - Handle revisions to the plan
    
    Every response includes:
    - AI's message/question
    - Latest plan (if ready)
    - Collected data so far
    - Whether more info is needed
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


@router.post(
    "/chat/continue",
    response_model=ChatResponse,
    tags=["Conversation"],
    summary="Continue AI Conversation",
    description="Continue an existing conversation with the AI planner"
)
async def continue_ai_chat(req: ChatContinueRequest) -> ChatResponse:
    """
    Continue an existing conversation.
    
    **Example Request:**
    ```json
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "message": "20 Kasım"
    }
    ```
    
    **Use this to:**
    - Answer AI's questions
    - Request plan revisions (e.g., "2. günü daha rahat yap")
    - Ask for changes (e.g., "Daha ucuz otel bul")
    - Provide additional preferences
    
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


@router.post(
    "/parse",
    response_model=ParsedTripPrompt,
    tags=["Utilities"],
    summary="Parse Travel Prompt",
    description="Extract structured information from natural language travel requests"
)
async def parse_endpoint(req: ParsePromptRequest):
    """
    Parse a natural language travel prompt into structured data.
    
    **Example Input:**
    ```json
    {
      "input": "Eşimle 15 Ekim Berlin'e 3-4 gün gidelim, bütçe sonra.",
      "locale": "tr-TR"
    }
    ```
    
    **Returns detailed structured data:**
    - Departure and destination cities/countries
    - Travel dates and duration
    - Traveler composition and count
    - Budget information
    - Travel style and preferences
    - Special occasions
    """
    try:
        parsed = await parse_prompt(req.input, req.locale or "tr-TR")
        return parsed
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plan/interactive",
    response_model=InteractivePlan,
    tags=["Planning"],
    summary="Get Interactive Plan (Frontend Format)",
    description="Generate a travel plan with multiple options per time slot for interactive UI"
)
async def get_interactive_plan(req: PlanRequest) -> InteractivePlan:
    """
    Create a travel plan in interactive format.
    
    **Perfect for frontend!** Each time slot has multiple activity options for users to choose from.
    
    **Example Request:**
    ```json
    {
      "prompt": "Istanbul Berlin 3 gün 2 kişi",
      "language": "tr",
      "currency": "EUR"
    }
    ```
    
    Example response structure:
    ```json
    {
      "time_slots": [
        {
          "day": 2,
          "startTime": "08:00",
          "endTime": "09:00",
          "options": [
            {
              "text": "Traditional German breakfast at local café",
              "description": "Quick and delicious start; ideal for trying local flavors."
            },
            {
              "text": "Breakfast at hotel then walk to Tiergarten",
              "description": "Relaxed start; perfect for nature lovers."
            }
          ]
        }
      ]
    }
    ```
    """
    try:
        # Generate regular plan first
        logger.info("Generating base trip plan...")
        trip_plan = await generate(req)
        
        # Transform to interactive format
        logger.info("Transforming to interactive format...")
        interactive_plan = await transform_to_interactive(
            trip_plan.model_dump(),
            language=req.language or "tr"
        )
        
        return interactive_plan
        
    except Exception as e:
        logger.error(f"Error creating interactive plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/chat/interactive",
    tags=["Conversation"],
    summary="Get Interactive Plan from Conversation",
    description="Transform a conversational session's plan into interactive format"
)
async def get_interactive_from_chat(data: Dict[str, Any]) -> InteractivePlan:
    """
    Get interactive plan format from an existing conversation session.
    
    **Example Request:**
    ```json
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```
    
    **Use this after:**
    1. Starting a conversation with `/chat/start`
    2. Completing the conversation
    3. Receiving a plan in the response
    
    **Returns:**
    Interactive format with multiple options per time slot for frontend display.
    ```
    
    Returns the current plan in interactive format with multiple options per time slot.
    """
    try:
        session_id = data.get("session_id")
        
        if not session_id or session_id not in conversation_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = conversation_sessions[session_id]
        
        if not session.current_plan:
            raise HTTPException(status_code=400, detail="No plan available yet. Complete the conversation first.")
        
        # Transform to interactive format
        interactive_plan = await transform_to_interactive(
            session.current_plan,
            language="tr"  # Could be stored in session
        )
        
        return interactive_plan
        
    except Exception as e:
        logger.error(f"Error getting interactive plan from chat: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
