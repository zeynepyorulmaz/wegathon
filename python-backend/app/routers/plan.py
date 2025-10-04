from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
from app.services import anthropic_client
from app.tools.adapters import get_mcp_tools_schema
from app.core.logging import logger
import uuid
import asyncio
import json

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
async def get_interactive_plan(
    req: PlanRequest, 
    session_id: str = None
) -> InteractivePlan:
    """
    Create a travel plan in interactive format with real-time progress updates.
    
    **Perfect for frontend!** Each time slot has multiple activity options for users to choose from.
    
    **Real-time progress:**
    - Pass ?session_id=xxx query parameter
    - Connect to GET /api/plan/progress/{session_id} for live updates
    
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
    
    async def send_progress(stage: str, message: str, data: Dict[str, Any] = None):
        """Send progress update via SSE if session_id provided"""
        if session_id and session_id in progress_queues:
            event = {"stage": stage, "message": message}
            if data:
                event["data"] = data
            await progress_queues[session_id].put(event)
    
    try:
        # Only validate prompt is not empty - let AI handle the rest
        prompt = req.prompt.strip()
        if len(prompt) < 3:
            raise HTTPException(
                status_code=400, 
                detail="Please provide a travel request"
            )
        
        await send_progress("parsing", "İsteğiniz anlaşılıyor...")
        
        # Generate regular plan first - AI will handle parsing and validation
        logger.info("Generating base trip plan...")
        await send_progress("planning", "Seyahat planı oluşturuluyor...")
        trip_plan = await generate(req, session_id=session_id)
        
        # Transform to interactive format
        logger.info("Transforming to interactive format...")
        await send_progress("formatting", "Plan hazırlanıyor...")
        interactive_plan = await transform_to_interactive(
            trip_plan.model_dump(),
            language=req.language or "tr"
        )
        
        await send_progress("complete", "Plan hazır!", {"plan_id": str(uuid.uuid4())})
        return interactive_plan
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        await send_progress("error", "Hata oluştu")
        raise
        
    except anthropic_client.RateLimitError as e:
        logger.error(f"Rate limit error: {e}")
        await send_progress("error", "AI servisi meşgul, lütfen tekrar deneyin")
        raise HTTPException(
            status_code=429,
            detail="AI service is temporarily busy. Please try again in a few seconds."
        )
        
    except Exception as e:
        logger.error(f"Error creating interactive plan: {e}")
        await send_progress("error", "Plan oluşturulurken hata oluştu")
        # Check if it's a JSON parsing error (invalid prompt response)
        error_msg = str(e)
        if "No valid JSON found" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Unable to understand your request. Please provide: origin city, destination, and dates. Example: 'Istanbul to Paris, May 15-20'"
            )
        elif "validation errors" in error_msg or "float_parsing" in error_msg:
            # Data format issue - log it but give user-friendly message
            logger.error(f"Data validation error: {error_msg[:500]}")
            raise HTTPException(
                status_code=500,
                detail="The travel plan was generated but had formatting issues. Please try again or contact support."
            )
        raise HTTPException(status_code=500, detail="An error occurred while generating your plan. Please try again.")


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


# ==================== TIMELINE MANIPULATION ====================

from app.models.timeline import (
    ActivityReorder, ActivityRemove, AlternativeRequest,
    TimeSlotUpdate, TimelineUpdate
)
from app.services import timeline_service


@router.post(
    "/timeline/reorder",
    tags=["Timeline"],
    summary="Reorder Activity (Drag & Drop)",
    description="Move activity between time slots, even across days"
)
async def reorder_activity(request: ActivityReorder) -> TimelineUpdate:
    """
    Reorder activity via drag & drop.
    
    **Example:**
    ```json
    {
      "session_id": "abc-123",
      "from_slot_id": "day1-morning",
      "to_slot_id": "day2-afternoon",
      "from_day": 1,
      "to_day": 2,
      "activity_index": 0
    }
    ```
    """
    return await timeline_service.reorder_activity(request)


@router.post(
    "/timeline/update-time",
    tags=["Timeline"],
    summary="Update Time Slot Range",
    description="Adjust start/end time of a slot (drag time handles)"
)
async def update_time_slot(request: TimeSlotUpdate) -> TimelineUpdate:
    """
    Update time slot's time range.
    
    **Example:**
    ```json
    {
      "slot_id": "day1-morning",
      "day": 1,
      "start_time": "09:00",
      "end_time": "12:30"
    }
    ```
    """
    return await timeline_service.update_time_slot(request)


@router.post(
    "/timeline/remove",
    tags=["Timeline"],
    summary="Remove Activity",
    description="Remove activity from timeline"
)
async def remove_activity(request: ActivityRemove) -> TimelineUpdate:
    """
    Remove activity from slot.
    
    **Example:**
    ```json
    {
      "session_id": "abc-123",
      "slot_id": "day1-morning",
      "day": 1,
      "activity_index": 0
    }
    ```
    """
    return await timeline_service.remove_activity(request)


@router.post(
    "/timeline/alternatives",
    tags=["Timeline"],
    summary="Get Alternative Activities",
    description="Generate 4 AI-powered alternative activities for a slot"
)
async def get_alternatives(request: AlternativeRequest) -> TimelineUpdate:
    """
    Get 4 alternative activities using AI.
    
    **Example:**
    ```json
    {
      "session_id": "abc-123",
      "slot_id": "day1-afternoon",
      "day": 1,
      "destination": "Paris",
      "time_window": "afternoon",
      "preferences": ["culture", "art"],
      "exclude_ids": ["act-123"],
      "language": "tr"
    }
    ```
    
    **Returns:**
    4 unique alternative activities with ratings, prices, and descriptions.
    """
    return await timeline_service.get_alternative_activities(request)


# Global progress tracking
progress_queues: Dict[str, asyncio.Queue] = {}


@router.get(
    "/plan/progress/{session_id}",
    tags=["Planning"],
    summary="Real-time Plan Generation Progress (SSE)",
    description="Server-Sent Events stream for real-time plan generation progress"
)
async def plan_progress(session_id: str):
    """
    Real-time progress updates via Server-Sent Events.
    
    **How to use:**
    1. Frontend calls POST /api/plan/interactive with ?session_id=xxx
    2. Immediately connect to GET /api/plan/progress/xxx
    3. Receive real-time events:
       - stage: "parsing", "flights", "hotels", "weather", "itinerary", "complete"
       - message: Human-readable progress message
       - data: Optional data payload
    
    **Example events:**
    ```
    data: {"stage": "parsing", "message": "Understanding your request..."}
    
    data: {"stage": "flights", "message": "Searching for flights...", "data": {"found": 5}}
    
    data: {"stage": "complete", "message": "Plan ready!", "data": {"plan_id": "abc-123"}}
    ```
    """
    async def event_generator():
        # Create queue for this session
        queue = asyncio.Queue()
        progress_queues[session_id] = queue
        
        try:
            while True:
                # Wait for progress events
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
                
                if event is None:  # Completion signal
                    break
                
                # Send SSE formatted event
                yield f"data: {json.dumps(event)}\n\n"
                
                # Check if this is final event
                if event.get("stage") == "complete" or event.get("stage") == "error":
                    break
                    
        except asyncio.TimeoutError:
            logger.warning(f"SSE timeout for session {session_id}")
            yield f"data: {json.dumps({'stage': 'error', 'message': 'Timeout'})}\n\n"
        finally:
            # Cleanup
            if session_id in progress_queues:
                del progress_queues[session_id]
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# In-memory storage for shared plans (use Redis/DB in production)
shared_plans: Dict[str, Dict[str, Any]] = {}


@router.post(
    "/plan/share",
    tags=["Planning"],
    summary="Share Plan Publicly",
    description="Generate a shareable link for a travel plan (with optional password)"
)
async def share_plan(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a public shareable link for a travel plan.
    
    **Example Request:**
    ```json
    {
      "session_id": "session_123",
      "plan": { /* full plan object */ },
      "title": "Rome Adventure - 3 Days",
      "description": "Amazing trip to Rome with cultural experiences",
      "password": "secret123",
      "allow_edit": true
    }
    ```
    
    **Returns:**
    ```json
    {
      "share_id": "abc-xyz-123",
      "share_url": "https://yourapp.com/shared/abc-xyz-123",
      "has_password": true,
      "allow_edit": true
    }
    ```
    """
    try:
        # Generate unique share ID
        share_id = str(uuid.uuid4())[:12]
        
        # Get password if provided
        password = data.get("password")
        allow_edit = data.get("allow_edit", False)
        
        # Store plan with metadata
        shared_plans[share_id] = {
            "id": share_id,
            "session_id": data.get("session_id"),
            "plan": data.get("plan"),
            "title": data.get("title", "Shared Travel Plan"),
            "description": data.get("description", ""),
            "password": password,  # Store password (in production, use hashing!)
            "allow_edit": allow_edit,  # Allow collaborators to edit
            "created_at": str(uuid.uuid1().time),
            "views": 0,
            "is_public": password is None  # Public only if no password
        }
        
        logger.info(f"✅ Plan shared with ID: {share_id}, password protected: {password is not None}, editable: {allow_edit}")
        
        return {
            "success": True,
            "share_id": share_id,
            "share_url": f"/shared/{share_id}",
            "has_password": password is not None,
            "allow_edit": allow_edit,
            "message": "Plan başarıyla paylaşıldı!"
        }
    except Exception as e:
        logger.error(f"Share plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/plan/shared/{share_id}",
    tags=["Planning"],
    summary="Get Shared Plan",
    description="Retrieve a shared travel plan (with password if required)"
)
async def get_shared_plan(share_id: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get a shared plan by its ID.
    
    **Example:**
    POST /api/plan/shared/abc-xyz-123
    ```json
    {
      "password": "secret123"
    }
    ```
    
    **Returns:**
    Full plan object with metadata, or 401 if password is incorrect
    """
    if share_id not in shared_plans:
        raise HTTPException(status_code=404, detail="Shared plan not found")
    
    shared_plan = shared_plans[share_id]
    
    # Check if password is required
    if shared_plan.get("password"):
        provided_password = data.get("password") if data else None
        
        if not provided_password:
            raise HTTPException(
                status_code=401, 
                detail="Bu plan şifre ile korunmaktadır"
            )
        
        if provided_password != shared_plan["password"]:
            raise HTTPException(
                status_code=403, 
                detail="Yanlış şifre"
            )
    
    # Increment view count
    shared_plans[share_id]["views"] += 1
    
    # Return plan without password field
    result = {k: v for k, v in shared_plan.items() if k != "password"}
    
    return result


@router.get(
    "/plan/shared/{share_id}/info",
    tags=["Planning"],
    summary="Get Shared Plan Info (no auth)",
    description="Check if plan exists and if password is required"
)
async def get_shared_plan_info(share_id: str) -> Dict[str, Any]:
    """
    Get basic info about a shared plan without authentication.
    Used to check if password is required before showing the plan.
    
    **Example:**
    GET /api/plan/shared/abc-xyz-123/info
    
    **Returns:**
    ```json
    {
      "exists": true,
      "requires_password": true,
      "title": "Rome Adventure",
      "description": "3-day cultural tour",
      "allow_edit": true
    }
    ```
    """
    if share_id not in shared_plans:
        raise HTTPException(status_code=404, detail="Shared plan not found")
    
    shared_plan = shared_plans[share_id]
    
    return {
        "exists": True,
        "requires_password": shared_plan.get("password") is not None,
        "title": shared_plan.get("title", "Shared Plan"),
        "description": shared_plan.get("description", ""),
        "allow_edit": shared_plan.get("allow_edit", False),
        "views": shared_plan.get("views", 0)
    }


# Template storage with JSON file persistence
import os
from pathlib import Path

TEMPLATES_FILE = Path(__file__).parent.parent / "data" / "templates.json"

def load_templates() -> Dict[str, Dict[str, Any]]:
    """Load templates from JSON file"""
    try:
        if TEMPLATES_FILE.exists():
            with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load templates: {e}")
    return {}

def save_templates(templates_data: Dict[str, Dict[str, Any]]):
    """Save templates to JSON file"""
    try:
        TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save templates: {e}")

# Load templates on startup
templates: Dict[str, Dict[str, Any]] = load_templates()


@router.post(
    "/plan/save-template",
    tags=["Templates"],
    summary="Save Plan as Template",
    description="Save a travel plan as a reusable template"
)
async def save_template(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save plan as template for future use.
    
    **Example Request:**
    ```json
    {
      "session_id": "session_123",
      "plan": { /* full plan object */ },
      "title": "3-Day Rome Cultural Tour",
      "description": "Perfect for art and history lovers",
      "tags": ["culture", "art", "history", "europe"],
      "is_public": true
    }
    ```
    
    **Returns:**
    ```json
    {
      "success": true,
      "template_id": "tpl-abc-123",
      "message": "Template saved successfully!"
    }
    ```
    """
    try:
        # Generate unique template ID
        template_id = f"tpl-{str(uuid.uuid4())[:8]}"
        
        # Store template
        templates[template_id] = {
            "id": template_id,
            "session_id": data.get("session_id"),
            "plan": data.get("plan"),
            "title": data.get("title", "Untitled Template"),
            "description": data.get("description", ""),
            "destination": data.get("destination", "Unknown"),
            "tags": data.get("tags", []),
            "is_public": data.get("is_public", True),
            "created_at": str(uuid.uuid1().time),
            "usage_count": 0,
            "likes": 0,
            "rating": 0.0,
            "uses": 0,
            "creator": "user"  # TODO: Add user authentication
        }
        
        # Save to file
        save_templates(templates)
        
        logger.info(f"✅ Template saved with ID: {template_id}")
        
        return {
            "success": True,
            "template_id": template_id,
            "message": "Şablon başarıyla kaydedildi!"
        }
    except Exception as e:
        logger.error(f"Save template error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates",
    tags=["Templates"],
    summary="List Templates",
    description="Get all available templates"
)
async def list_templates(
    tag: str = None,
    search: str = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    List all public templates with optional filtering.
    
    **Query Params:**
    - tag: Filter by tag (e.g., "culture", "adventure")
    - search: Search in title/description
    - limit: Max results (default: 20)
    
    **Returns:**
    Array of template objects
    """
    results = list(templates.values())
    
    # Filter by public only
    results = [t for t in results if t.get("is_public", True)]
    
    # Filter by tag
    if tag:
        results = [t for t in results if tag in t.get("tags", [])]
    
    # Search
    if search:
        search_lower = search.lower()
        results = [
            t for t in results
            if search_lower in t.get("title", "").lower()
            or search_lower in t.get("description", "").lower()
        ]
    
    # Limit
    results = results[:limit]
    
    return {
        "templates": results,
        "total": len(results)
    }


@router.get(
    "/templates/{template_id}",
    tags=["Templates"],
    summary="Get Template",
    description="Get a specific template by ID"
)
async def get_template(template_id: str) -> Dict[str, Any]:
    """
    Get template details.
    
    **Example:**
    GET /api/templates/tpl-abc-123
    """
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Increment use count
    templates[template_id]["uses"] += 1
    
    return {"template": templates[template_id]}


@router.post(
    "/templates/{template_id}/like",
    tags=["Templates"],
    summary="Like Template",
    description="Like or unlike a template"
)
async def like_template(template_id: str) -> Dict[str, Any]:
    """
    Toggle like on a template.
    
    **Example:**
    POST /api/templates/tpl-abc-123/like
    """
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Toggle like (in real app, track per-user likes)
    templates[template_id]["likes"] = templates[template_id].get("likes", 0) + 1
    save_templates(templates)
    
    return {
        "success": True,
        "likes": templates[template_id]["likes"]
    }


@router.post(
    "/templates/{template_id}/unlike",
    tags=["Templates"],
    summary="Unlike Template"
)
async def unlike_template(template_id: str) -> Dict[str, Any]:
    """Unlike a template."""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    templates[template_id]["likes"] = max(0, templates[template_id].get("likes", 0) - 1)
    save_templates(templates)
    
    return {
        "success": True,
        "likes": templates[template_id]["likes"]
    }
