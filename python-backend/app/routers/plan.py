from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from app.models.plan import PlanRequest, ReviseRequest, TripPlan
from app.models.conversation import ConversationState, QuestionResponse, UserAnswer
from app.services.planner import generate, revise
from app.services.ask import ask_questions
from app.services.trip_parser import parse_trip_prompt, validate_and_complete_trip_data, format_trip_prompt
from app.services.conversational_planner import chat_to_collect_trip_info, create_plan_from_conversation
from app.tools.adapters import get_mcp_tools_schema
import uuid

router = APIRouter(prefix="/api", tags=["planner"])

# Simple in-memory storage for conversation states (use Redis/DB in production)
conversation_store: Dict[str, ConversationState] = {}
# Storage for AI-driven conversations
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


@router.post("/plan/validate")
async def validate_trip_prompt(req: PlanRequest) -> Dict[str, Any]:
    """
    Validate trip prompt and ask for missing required information.
    If all information is present, returns ready_to_plan=True.
    Otherwise, returns the first missing field as a question.
    """
    try:
        # Parse the prompt to extract known information
        extracted_data, missing_fields = parse_trip_prompt(req.prompt, req.language or "en")
        
        # If all required fields are present, ready to plan
        if not missing_fields:
            # Validate and complete the data
            complete_data = validate_and_complete_trip_data(extracted_data)
            
            return {
                "ready_to_plan": True,
                "message": "All required information collected. Ready to create your travel plan!",
                "collected_data": complete_data,
                "session_id": None
            }
        
        # Create a conversation session
        session_id = str(uuid.uuid4())
        conversation_state = ConversationState(
            session_id=session_id,
            original_prompt=req.prompt,
            collected_data=extracted_data,
            remaining_fields=missing_fields,
            current_question=missing_fields[0],
            ready_to_plan=False
        )
        
        # Store the state
        conversation_store[session_id] = conversation_state
        
        # Return the first question
        return {
            "ready_to_plan": False,
            "message": f"I need some more information to create your perfect travel plan.",
            "question": missing_fields[0].dict(),
            "session_id": session_id,
            "collected_so_far": extracted_data,
            "remaining_questions": len(missing_fields) - 1
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan/answer")
async def answer_trip_question(answer_data: UserAnswer) -> Dict[str, Any]:
    """
    Submit an answer to a trip planning question.
    Returns the next question or ready_to_plan=True when all info is collected.
    """
    try:
        session_id = answer_data.session_id
        
        # Retrieve conversation state
        if session_id not in conversation_store:
            raise HTTPException(status_code=404, detail="Session not found. Please start a new conversation.")
        
        state = conversation_store[session_id]
        
        # Store the answer
        if state.current_question:
            state.collected_data[state.current_question.field] = answer_data.answer
            
            # Remove the answered question from remaining
            state.remaining_fields = state.remaining_fields[1:]
        
        # Check if we have more questions
        if state.remaining_fields:
            state.current_question = state.remaining_fields[0]
            
            # Update store
            conversation_store[session_id] = state
            
            return {
                "ready_to_plan": False,
                "message": "Got it! One more question:",
                "question": state.current_question.dict(),
                "session_id": session_id,
                "collected_so_far": state.collected_data,
                "remaining_questions": len(state.remaining_fields) - 1
            }
        
        # All questions answered!
        state.ready_to_plan = True
        state.current_question = None
        
        # Validate and complete the data
        complete_data = validate_and_complete_trip_data(state.collected_data)
        state.collected_data = complete_data
        
        # Update store
        conversation_store[session_id] = state
        
        return {
            "ready_to_plan": True,
            "message": "Perfect! I have all the information I need. Ready to create your travel plan!",
            "collected_data": complete_data,
            "session_id": session_id,
            "remaining_questions": 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan/create")
async def create_plan_from_session(data: Dict[str, Any]) -> TripPlan:
    """
    Create a travel plan from a completed conversation session.
    """
    try:
        session_id = data.get("session_id")
        
        if not session_id or session_id not in conversation_store:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = conversation_store[session_id]
        
        if not state.ready_to_plan:
            raise HTTPException(status_code=400, detail="Session not ready. Please answer all questions first.")
        
        # Format the collected data into a prompt
        formatted_prompt = format_trip_prompt(state.collected_data, data.get("language", "en"))
        
        # Create plan request
        req = PlanRequest(
            prompt=formatted_prompt,
            currency=data.get("currency", "TRY"),
            language=data.get("language", "en")
        )
        
        # Generate the plan
        plan = await generate(req)
        
        # Clean up session (optional - you might want to keep for history)
        # del conversation_store[session_id]
        
        return plan
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

