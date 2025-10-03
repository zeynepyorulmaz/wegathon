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


# Simple plan endpoint removed - use /chat/start instead for conversational planning


@router.post(
    "/bookings",
    tags=["Planning"],
    summary="Get Flight + Hotel Options (Parallel)",
    description="Fetch flights and hotels in parallel for optimal performance"
)
async def get_bookings(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get flight and hotel options in parallel.
    
    **Example Request:**
    ```json
    {
      "origin": "Istanbul",
      "destination": "Berlin",
      "start_date": "2025-11-20",
      "end_date": "2025-11-23",
      "adults": 2,
      "children": 0
    }
    ```
    
    **Returns:**
    - Flights (outbound + alternatives)
    - Hotels (selected + alternatives)
    - Pricing estimate
    
    **Performance:** Runs both searches in parallel!
    """
    from app.services.booking_service import get_bookings_parallel
    
    try:
        result = await get_bookings_parallel(
            origin=data.get("origin", "Istanbul"),
            destination=data.get("destination"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            adults=data.get("adults", 2),
            children=data.get("children", 0)
        )
        return result
    except Exception as e:
        logger.error(f"Booking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/activities",
    tags=["Planning"],
    summary="Plan Daily Activities",
    description="AI-generated day-by-day itinerary with activities"
)
async def get_activities(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Plan activities and daily itinerary.
    
    **Example Request:**
    ```json
    {
      "destination": "Berlin",
      "start_date": "2025-11-20",
      "end_date": "2025-11-23",
      "adults": 2,
      "children": 0,
      "preferences": ["museums", "food", "culture"],
      "budget": "mid",
      "language": "tr"
    }
    ```
    
    **Returns:**
    - Day-by-day itinerary
    - Morning/afternoon/evening blocks
    - Activity suggestions
    - Travel tips
    """
    from app.services.activity_service import plan_activities
    
    try:
        result = await plan_activities(
            destination=data.get("destination"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            adults=data.get("adults", 2),
            children=data.get("children", 0),
            preferences=data.get("preferences", []),
            budget=data.get("budget"),
            weather_data=data.get("weather_data"),
            language=data.get("language", "tr")
        )
        return result
    except Exception as e:
        logger.error(f"Activity planning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/select/flight",
    tags=["Planning"],
    summary="Select Alternative Flight",
    description="Change the selected flight option"
)
async def select_flight(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Select a different flight from alternatives.
    
    **Example:**
    ```json
    {
      "session_id": "...",
      "alternative_index": 1
    }
    ```
    """
    session_id = data.get("session_id")
    index = data.get("alternative_index", 0)
    
    if not session_id or session_id not in conversation_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = conversation_sessions[session_id]
    
    if not session.current_plan:
        raise HTTPException(status_code=400, detail="No plan found")
    
    alternatives = session.current_plan.get("alternatives", {}).get("flights", [])
    
    if 0 <= index < len(alternatives):
        session.current_plan["selected"]["flight"] = alternatives[index]
        return {"success": True, "message": "Flight updated", "selected": alternatives[index]}
    else:
        raise HTTPException(status_code=400, detail="Invalid alternative index")


@router.post(
    "/select/hotel",
    tags=["Planning"],
    summary="Select Alternative Hotel",
    description="Change the selected hotel option"
)
async def select_hotel(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Select a different hotel from alternatives.
    
    **Example:**
    ```json
    {
      "session_id": "...",
      "alternative_index": 0
    }
    ```
    """
    session_id = data.get("session_id")
    index = data.get("alternative_index", 0)
    
    if not session_id or session_id not in conversation_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = conversation_sessions[session_id]
    
    if not session.current_plan:
        raise HTTPException(status_code=400, detail="No plan found")
    
    alternatives = session.current_plan.get("alternatives", {}).get("hotels", [])
    
    if 0 <= index < len(alternatives):
        session.current_plan["selected"]["hotel"] = alternatives[index]
        return {"success": True, "message": "Hotel updated", "selected": alternatives[index]}
    else:
        raise HTTPException(status_code=400, detail="Invalid alternative index")


@router.post(
    "/select/activity",
    tags=["Planning"],
    summary="Select Alternative Activity",
    description="Change activity for a specific time slot"
)
async def select_activity(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Select a different activity for a time slot.
    
    **Example:**
    ```json
    {
      "session_id": "...",
      "day": 1,
      "time_slot": "09:00-12:00",
      "alternative_index": 2
    }
    ```
    """
    session_id = data.get("session_id")
    day = data.get("day")
    time_slot = data.get("time_slot")
    index = data.get("alternative_index", 0)
    
    if not session_id or session_id not in conversation_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = conversation_sessions[session_id]
    
    if not session.current_plan:
        raise HTTPException(status_code=400, detail="No plan found")
    
    # Find the time slot
    time_slots = session.current_plan.get("activities", {}).get("time_slots", [])
    
    for slot in time_slots:
        if slot.get("day") == day and slot.get("time") == time_slot:
            alternatives = slot.get("alternatives", [])
            if 0 <= index < len(alternatives):
                slot["selected"] = alternatives[index]
                return {"success": True, "message": "Activity updated", "selected": alternatives[index]}
            else:
                raise HTTPException(status_code=400, detail="Invalid alternative index")
    
    raise HTTPException(status_code=404, detail="Time slot not found")


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
    description="Begin conversational trip planning - AI will ask for missing information"
)
async def start_ai_chat(req: ChatStartRequest) -> ChatResponse:
    """
    Start a new conversational trip planning session.
    
    **Conversational Flow:**
    1. AI analyzes your message
    2. If information is missing, AI asks ONE question at a time
    3. Once ALL info is collected, AI creates the plan
    4. You can then revise the plan
    
    **Required Information:**
    - Origin city
    - Destination city
    - Start date
    - End date (or duration)
    - Number of adults
    
    **Example:**
    ```
    You: "Berlin 3 gün"
    AI: "Harika! Berlin için 3 günlük bir plan hazırlayayım. Nereden gideceksiniz?"
    You: "İstanbul"
    AI: "Teşekkürler! Hangi tarihte gitmek istersiniz?"
    You: "20 Kasım"
    AI: "Kaç kişi seyahat edeceksiniz?"
    You: "2 kişi"
    AI: "Mükemmel! Planınızı oluşturuyorum..." → [PLAN CREATED]
    ```
    """
    try:
        # Create new session
        session_id = str(uuid.uuid4())
        session = ConversationSession(session_id=session_id)
        session.language = req.language
        session.currency = req.currency
        
        logger.info(f"Chat started with: {req.initial_message}")
        
        # Process message with AI to collect info
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
        
        language = session.language or "tr"
        currency = session.currency or "TRY"
        
        logger.info(f"Chat continue with: {req.message}")
        
        # Process conversation turn (will either collect more info or create/revise plan)
        ai_message, plan, needs_more_info = await process_conversation_turn(
            session=session,
            user_message=req.message,
            language=language,
            currency=currency
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
