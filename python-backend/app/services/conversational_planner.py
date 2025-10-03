"""
Conversational Travel Planner
AI-driven conversation to collect trip requirements naturally
"""

import json
from typing import Dict, Any, List, Tuple
from app.core.logging import logger
from app.services import anthropic_client
from app.services.planner import generate
from app.models.plan import PlanRequest, TripPlan


CONVERSATION_SYSTEM = """You are a friendly and professional Travel Planning Assistant. Your goal is to collect ALL necessary information to plan a perfect trip.

## REQUIRED INFORMATION:
1. **Origin City** - Where the traveler is departing from
2. **Destination City** - Where they want to go
3. **Start Date** - When they want to begin the trip (format: DD.MM.YYYY or YYYY-MM-DD)
4. **End Date OR Duration** - When they return OR how many days/nights
5. **Number of Adults** - How many people are traveling

## YOUR CONVERSATION STYLE:
- Be warm, friendly, and conversational (not robotic)
- Ask ONE question at a time
- If the user provides multiple pieces of information at once, acknowledge them all
- Use natural language, not forms
- Be encouraging and excited about their trip
- Adapt your language to match theirs (formal/casual)

## CONVERSATION FLOW:
1. **Initial Message**: Greet warmly and ask what trip they're planning
2. **Collect Missing Info**: Ask for missing details one by one, naturally
3. **Confirm & Summarize**: Once you have everything, summarize and confirm
4. **Signal Ready**: Return JSON with "ready_to_plan": true when all info is collected

## RESPONSE FORMAT:
While collecting information, respond naturally in conversational text.

When ALL required info is collected, respond with this EXACT JSON structure:
```json
{
  "ready_to_plan": true,
  "collected_data": {
    "origin": "Istanbul",
    "destination": "Paris", 
    "start_date": "15.11.2025",
    "end_date": "20.11.2025",
    "duration": 5,
    "adults": 2,
    "preferences": ["budget-friendly", "museums"],
    "original_prompt": "full conversation context"
  },
  "summary": "5 days in Paris from Istanbul, November 15-20, 2 adults, interested in budget-friendly options and museums"
}
```

## EXAMPLES:

User: "I want to visit Paris"
You: "Paris! What a wonderful choice! 🗼 Where will you be traveling from?"

User: "Istanbul"
You: "Great! And when are you thinking of going? Do you have specific dates in mind?"

User: "Maybe mid November"
You: "Perfect! November is lovely in Paris. Could you give me specific dates? For example, November 15th?"

User: "Yes, November 15 to 20"
You: "Excellent! November 15-20, 2025. And how many people will be traveling?"

User: "Just me and my wife, 2 people"
You: "Wonderful! Let me make sure I have everything:
- From Istanbul to Paris
- November 15-20, 2025 (5 days)
- 2 adults

Is this correct? Any special interests or budget preferences?"

User: "Yes that's right, we like museums and want something budget-friendly"
You: [Return ready_to_plan JSON with all collected data]

## IMPORTANT:
- NEVER return JSON until you have ALL 5 required fields
- Be patient and conversational while collecting info
- Make the experience delightful, not like filling a form
"""


async def chat_to_collect_trip_info(
    conversation_history: List[Dict[str, str]],
    language: str = "en"
) -> Tuple[str, bool, Dict[str, Any] | None]:
    """
    Have a conversation with the user to collect trip planning information.
    
    Returns:
        (response_message, is_ready_to_plan, collected_data_or_none)
    """
    
    system = CONVERSATION_SYSTEM
    if language == "tr":
        system += "\n\n**IMPORTANT: Respond in Turkish (Türkçe). Be warm and friendly in Turkish.**"
    
    try:
        # Call Claude for conversation
        response = await anthropic_client.chat(conversation_history, system)
        
        logger.info(f"Conversation response length: {len(response)}")
        logger.debug(f"Response preview: {response[:200]}...")
        
        # Check if response contains the ready_to_plan JSON
        if "ready_to_plan" in response and "{" in response:
            # Try to extract JSON
            try:
                # Find JSON in response
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    data = json.loads(json_str)
                    
                    if data.get("ready_to_plan"):
                        logger.info("✅ All trip info collected, ready to plan!")
                        return response, True, data.get("collected_data")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse ready_to_plan JSON: {e}")
        
        # Still collecting information
        return response, False, None
        
    except Exception as e:
        logger.error(f"Error in conversation: {e}")
        error_msg = "I apologize, I encountered an error. Could you please repeat that?" if language == "en" else "Özür dilerim, bir hata oluştu. Tekrar edebilir misiniz?"
        return error_msg, False, None


async def create_plan_from_conversation(
    collected_data: Dict[str, Any],
    language: str = "en",
    currency: str = "TRY"
) -> TripPlan:
    """
    Create a travel plan from conversationally collected data.
    """
    
    # Format into a comprehensive prompt
    parts = []
    
    if collected_data.get("duration"):
        parts.append(f"{collected_data['duration']} day trip")
    
    if collected_data.get("origin"):
        parts.append(f"from {collected_data['origin']}")
    
    if collected_data.get("destination"):
        parts.append(f"to {collected_data['destination']}")
    
    if collected_data.get("start_date") and collected_data.get("end_date"):
        parts.append(f"{collected_data['start_date']} to {collected_data['end_date']}")
    elif collected_data.get("start_date"):
        parts.append(f"starting {collected_data['start_date']}")
    
    if collected_data.get("adults"):
        parts.append(f"{collected_data['adults']} adult(s)")
    
    if collected_data.get("preferences"):
        prefs = ", ".join(collected_data['preferences'])
        parts.append(f"preferences: {prefs}")
    
    # Use summary if provided, otherwise construct from parts
    prompt = collected_data.get("summary") or " ".join(parts)
    
    logger.info(f"Creating plan from conversation with prompt: {prompt}")
    
    # Create the plan
    req = PlanRequest(
        prompt=prompt,
        language=language,
        currency=currency
    )
    
    return await generate(req)

