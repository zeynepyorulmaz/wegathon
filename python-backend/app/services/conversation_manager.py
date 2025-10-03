"""
Conversation manager - handles conversational trip planning with AI.
Collects missing information, creates plans, and handles revisions.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json

from app.models.conversation import ConversationSession, ChatMessage
from app.models.plan import TripPlan, PlanRequest, ReviseRequest
from app.services import anthropic_client
from app.services.planner import generate, revise
from app.services.prompt_parser import parse_prompt
from app.core.logging import logger


# System prompt for conversational AI
CONVERSATION_SYSTEM_PROMPT = """You are an expert travel planning assistant. Your role is to:

1. **Collect Information**: Gather all necessary trip details through natural conversation
2. **Create Plans**: Generate comprehensive travel plans when you have enough information
3. **Handle Revisions**: Update existing plans based on user requests

**Required Information for Planning:**
- Origin city (default: Istanbul if not specified)
- Destination city
- Travel dates (start and end, or duration)
- Number of travelers (adults + children)

**Conversation Strategy:**
- Be friendly and conversational
- Ask ONE question at a time for missing critical information
- If user provides partial info, acknowledge it and ask for what's missing
- When you have all info, confirm and say you'll create the plan
- For revisions, understand the change and explain what you'll update

**Response Format:**
Always respond in JSON format:
```json
{
  "message": "Your conversational response to the user",
  "action": "ask_question" | "create_plan" | "revise_plan" | "confirm",
  "collected_data": {
    "origin": "city",
    "destination": "city", 
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "adults": 2,
    "children": 0,
    "preferences": [],
    "budget": null
  },
  "missing_fields": ["field1", "field2"],
  "revision_instruction": "what to change" // only for revise_plan
}
```

**Important:**
- ALWAYS return valid JSON
- Use Turkish if user speaks Turkish, English otherwise
- Be concise but warm
- Don't ask for non-essential info (budget, preferences) unless user mentions them
"""


async def process_conversation_turn(
    session: ConversationSession,
    user_message: str,
    language: str = "tr",
    currency: str = "TRY"
) -> Tuple[str, Optional[TripPlan], bool]:
    """
    Process one turn of conversation.
    
    Returns:
        (ai_message, current_plan, needs_more_info)
    """
    # Add user message to history
    session.history.append(ChatMessage(role="user", content=user_message))
    
    # Build conversation context for AI
    messages = [{"role": msg.role, "content": msg.content} for msg in session.history]
    
    # Add context about current state
    context = {
        "has_plan": session.plan_created,
        "collected_data": session.collected_data,
        "language": language,
        "currency": currency,
    }
    
    system_prompt = CONVERSATION_SYSTEM_PROMPT + f"\n\nContext: {json.dumps(context, ensure_ascii=False)}"
    
    try:
        # Call Anthropic for conversational response
        response = await anthropic_client.chat_with_tools(
            messages=messages,
            tools=[],  # No tools needed for conversation management
            system=system_prompt
        )
        
        # Extract AI response
        ai_text = ""
        for block in response.get("content", []):
            if block.get("type") == "text":
                ai_text = block.get("text", "")
                break
        
        if not ai_text:
            raise ValueError("No response from AI")
        
        logger.info(f"AI response: {ai_text[:200]}...")
        
        # Parse AI's JSON response
        try:
            # Extract JSON from response
            start = ai_text.find("{")
            end = ai_text.rfind("}") + 1
            if start != -1 and end > start:
                ai_data = json.loads(ai_text[start:end])
            else:
                # Fallback: treat as plain text
                ai_data = {"message": ai_text, "action": "confirm"}
        except json.JSONDecodeError:
            # Fallback: use text as-is
            ai_data = {"message": ai_text, "action": "confirm"}
        
        ai_message = ai_data.get("message", "")
        action = ai_data.get("action", "ask_question")
        collected_data = ai_data.get("collected_data", {})
        revision_instruction = ai_data.get("revision_instruction")
        
        # Update collected data
        if collected_data:
            session.collected_data.update(collected_data)
        
        # Add AI message to history
        session.history.append(ChatMessage(role="assistant", content=ai_message))
        
        # Handle action
        current_plan = None
        needs_more_info = True
        
        if action == "create_plan":
            # We have enough info - create the plan with bookings
            logger.info("Creating plan with collected data...")
            
            # Get bookings in parallel (flight + hotel)
            from app.services.booking_service import get_bookings_parallel
            
            bookings = await get_bookings_parallel(
                origin=session.collected_data.get("origin", "Istanbul"),
                destination=session.collected_data.get("destination"),
                start_date=session.collected_data.get("start_date"),
                end_date=session.collected_data.get("end_date"),
                adults=session.collected_data.get("adults", 2),
                children=session.collected_data.get("children", 0)
            )
            
            # Get activities with flight/hotel time constraints
            from app.services.activity_service import plan_activities
            
            # Extract flight times safely
            flight_arrival = None
            flight_departure = None
            
            try:
                if bookings and isinstance(bookings, dict):
                    flights = bookings.get("flights", {})
                    
                    if flights and isinstance(flights, dict):
                        # Get arrival from outbound
                        outbound = flights.get("outbound")
                        if outbound and isinstance(outbound, dict):
                            segments = outbound.get("segments", [])
                            if segments and isinstance(segments, list) and len(segments) > 0:
                                arrive_iso = segments[-1].get("arriveISO", "")
                                if arrive_iso:
                                    # Handle both Z and +00:00 timezone formats
                                    arrive_iso_clean = arrive_iso.replace("Z", "+00:00")
                                    arrive_dt = datetime.fromisoformat(arrive_iso_clean)
                                    flight_arrival = arrive_dt.strftime("%H:%M")
                                    logger.info(f"Flight arrival time: {flight_arrival}")
                        
                        # Get departure from inbound (if exists)
                        inbound = flights.get("inbound")
                        if inbound and isinstance(inbound, dict):
                            segments = inbound.get("segments", [])
                            if segments and isinstance(segments, list) and len(segments) > 0:
                                depart_iso = segments[0].get("departISO", "")
                                if depart_iso:
                                    depart_iso_clean = depart_iso.replace("Z", "+00:00")
                                    depart_dt = datetime.fromisoformat(depart_iso_clean)
                                    flight_departure = depart_dt.strftime("%H:%M")
                                    logger.info(f"Flight departure time: {flight_departure}")
            except Exception as e:
                logger.warning(f"Could not extract flight times: {e}")
            
            activities = await plan_activities(
                destination=session.collected_data.get("destination"),
                start_date=session.collected_data.get("start_date"),
                end_date=session.collected_data.get("end_date"),
                adults=session.collected_data.get("adults", 2),
                children=session.collected_data.get("children", 0),
                preferences=session.collected_data.get("preferences", []),
                budget=session.collected_data.get("budget"),
                flight_arrival_time=flight_arrival,
                flight_departure_time=flight_departure,
                language=language
            )
            
            # Build complete plan with defaults selected
            plan_data = {
                "bookings": bookings,
                "activities": activities,
                "selected": {
                    "flight": bookings["flights"]["outbound"],
                    "hotel": bookings["hotels"]["selected"]
                },
                "alternatives": {
                    "flights": bookings["flights"].get("alternatives", []),
                    "hotels": bookings["hotels"].get("alternatives", [])
                }
            }
            
            session.current_plan = plan_data
            session.plan_created = True
            session.needs_more_info = False
            
            # Try to parse the initial message for better context
            try:
                initial_msg = session.history[0].content
                parsed = await parse_prompt(initial_msg, locale="tr-TR" if language == "tr" else "en-US")
                if not session.collected_data.get("destination"):
                    session.collected_data["destination"] = parsed.destination.city
                if not session.collected_data.get("start_date"):
                    session.collected_data["start_date"] = parsed.dates.start_date
                if not session.collected_data.get("end_date"):
                    session.collected_data["end_date"] = parsed.dates.end_date
                if not session.collected_data.get("adults"):
                    session.collected_data["adults"] = parsed.travelers.count or 1
            except Exception as e:
                logger.warning(f"Could not parse prompt: {e}")
            
            # Build prompt from collected data
            prompt_parts = []
            if session.collected_data.get("origin"):
                prompt_parts.append(f"From {session.collected_data['origin']}")
            if session.collected_data.get("destination"):
                prompt_parts.append(f"to {session.collected_data['destination']}")
            if session.collected_data.get("start_date"):
                prompt_parts.append(f"starting {session.collected_data['start_date']}")
            if session.collected_data.get("end_date"):
                prompt_parts.append(f"until {session.collected_data['end_date']}")
            if session.collected_data.get("adults"):
                prompt_parts.append(f"for {session.collected_data['adults']} adults")
            
            prompt = ", ".join(prompt_parts)
            
            # Generate plan using new parallel API
            plan_request = PlanRequest(
                prompt=prompt,
                language=language,
                currency=currency
            )
            
            trip_plan = await generate(plan_request)
            
            # Store plan in session
            session.current_plan = trip_plan.model_dump()
            session.plan_created = True
            current_plan = trip_plan
            needs_more_info = False
            
            # Add helpful message about alternatives
            if language == "tr":
                ai_message += "\n\n💡 İpucu: İsterseniz 'uçuşu değiştir' veya 'oteli değiştir' diyerek alternatifleri görebilirsiniz!"
            else:
                ai_message += "\n\n💡 Tip: You can say 'change flight' or 'change hotel' to see alternatives!"
            
            logger.info("Plan created successfully")
            
        elif action == "revise_plan" and session.current_plan and revision_instruction:
            # Handle change requests
            logger.info(f"Revising plan: {revision_instruction}")
            
            instruction_lower = revision_instruction.lower()
            
            # Check if user wants to change flight or hotel
            if "uçuş" in instruction_lower or "flight" in instruction_lower and ("değiştir" in instruction_lower or "change" in instruction_lower):
                # Show flight alternatives safely
                plan_alts = session.current_plan.get("alternatives", {}) if session.current_plan else {}
                alternatives = plan_alts.get("flights", []) if isinstance(plan_alts, dict) else []
                
                if alternatives:
                    if language == "tr":
                        ai_message = "✈️ Alternatif uçuşlar:\n\n"
                        for i, flight in enumerate(alternatives[:3], 1):
                            price = flight.get("price", 0)
                            airline = flight.get("airline", "")
                            ai_message += f"{i}. {airline} - {price} TRY\n"
                        ai_message += "\nHangisini seçmek istersiniz? (Örn: '2. uçuşu seç')"
                    else:
                        ai_message = "✈️ Alternative flights:\n\n"
                        for i, flight in enumerate(alternatives[:3], 1):
                            price = flight.get("price", 0)
                            airline = flight.get("airline", "")
                            ai_message += f"{i}. {airline} - {price} TRY\n"
                        ai_message += "\nWhich would you like? (e.g., 'select flight 2')"
                else:
                    ai_message = "Üzgünüm, alternatif uçuş bulunamadı." if language == "tr" else "Sorry, no alternative flights found."
                
                current_plan = TripPlan.model_validate(session.current_plan) if session.current_plan else None
                needs_more_info = False
                
            elif "otel" in instruction_lower or "hotel" in instruction_lower and ("değiştir" in instruction_lower or "change" in instruction_lower):
                # Show hotel alternatives safely
                plan_alts = session.current_plan.get("alternatives", {}) if session.current_plan else {}
                alternatives = plan_alts.get("hotels", []) if isinstance(plan_alts, dict) else []
                
                if alternatives:
                    if language == "tr":
                        ai_message = "🏨 Alternatif oteller:\n\n"
                        for i, hotel in enumerate(alternatives[:3], 1):
                            name = hotel.get("name", "Hotel")
                            price = hotel.get("priceTotal", 0)
                            ai_message += f"{i}. {name} - {price} TRY\n"
                        ai_message += "\nHangisini seçmek istersiniz? (Örn: '1. oteli seç')"
                    else:
                        ai_message = "🏨 Alternative hotels:\n\n"
                        for i, hotel in enumerate(alternatives[:3], 1):
                            name = hotel.get("name", "Hotel")
                            price = hotel.get("priceTotal", 0)
                            ai_message += f"{i}. {name} - {price} TRY\n"
                        ai_message += "\nWhich would you like? (e.g., 'select hotel 1')"
                else:
                    ai_message = "Üzgünüm, alternatif otel bulunamadı." if language == "tr" else "Sorry, no alternative hotels found."
                
                current_plan = TripPlan.model_validate(session.current_plan) if session.current_plan else None
                needs_more_info = False
                
            elif "seç" in instruction_lower or "select" in instruction_lower:
                # User selecting an alternative
                import re
                numbers = re.findall(r'\d+', revision_instruction)
                
                if numbers and session.current_plan:
                    selection = int(numbers[0]) - 1  # 0-indexed
                    
                    if "uçuş" in instruction_lower or "flight" in instruction_lower:
                        plan_alts = session.current_plan.get("alternatives", {}) if session.current_plan else {}
                        alternatives = plan_alts.get("flights", []) if isinstance(plan_alts, dict) else []
                        
                        if 0 <= selection < len(alternatives):
                            if "selected" not in session.current_plan:
                                session.current_plan["selected"] = {}
                            session.current_plan["selected"]["flight"] = alternatives[selection]
                            ai_message = "✅ Uçuş seçiminiz güncellendi! Plan güncel haliyle gösteriliyor." if language == "tr" else "✅ Flight updated! Showing updated plan."
                        else:
                            ai_message = f"Geçersiz seçim. Lütfen 1-{len(alternatives)} arası bir numara girin." if language == "tr" else f"Invalid selection. Please choose 1-{len(alternatives)}."
                    
                    elif "otel" in instruction_lower or "hotel" in instruction_lower:
                        plan_alts = session.current_plan.get("alternatives", {}) if session.current_plan else {}
                        alternatives = plan_alts.get("hotels", []) if isinstance(plan_alts, dict) else []
                        
                        if 0 <= selection < len(alternatives):
                            if "selected" not in session.current_plan:
                                session.current_plan["selected"] = {}
                            session.current_plan["selected"]["hotel"] = alternatives[selection]
                            ai_message = "✅ Otel seçiminiz güncellendi! Plan güncel haliyle gösteriliyor." if language == "tr" else "✅ Hotel updated! Showing updated plan."
                        else:
                            ai_message = f"Geçersiz seçim. Lütfen 1-{len(alternatives)} arası bir numara girin." if language == "tr" else f"Invalid selection. Please choose 1-{len(alternatives)}."
                else:
                    ai_message = "Lütfen seçmek istediğiniz numarayı belirtin (örn: '2. uçuşu seç')" if language == "tr" else "Please specify the number (e.g., 'select flight 2')"
                
                # Return updated plan
                current_plan = TripPlan.model_validate(session.current_plan) if session.current_plan else None
                needs_more_info = False
                
            else:
                # Other revision - use standard revise
                revise_request = ReviseRequest(
                    planId=session.session_id,
                    instruction=revision_instruction
                )
                
                trip_plan = await revise(session.current_plan, revise_request)
                
                # Update plan in session
                session.current_plan = trip_plan.model_dump()
                current_plan = trip_plan
                needs_more_info = False
            
            logger.info("Plan revision handled")
            
        elif action == "ask_question":
            # Still collecting information
            needs_more_info = True
            
            # If we have a plan, return it too
            if session.current_plan:
                current_plan = TripPlan.model_validate(session.current_plan)
            
        elif action == "confirm":
            # Just confirming, return current plan if exists
            needs_more_info = False
            if session.current_plan:
                current_plan = TripPlan.model_validate(session.current_plan)
        
        return ai_message, current_plan, needs_more_info
        
    except Exception as e:
        logger.error(f"Error in conversation turn: {e}")
        error_message = "Üzgünüm, bir hata oluştu. Lütfen tekrar dener misiniz?" if language == "tr" else "Sorry, an error occurred. Please try again."
        session.history.append(ChatMessage(role="assistant", content=error_message))
        
        # Return current plan if we have one
        current_plan = None
        if session.current_plan:
            current_plan = TripPlan.model_validate(session.current_plan)
        
        return error_message, current_plan, True

