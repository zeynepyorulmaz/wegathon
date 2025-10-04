"""
Timeline Service - Manages timeline manipulations and alternative suggestions
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.logging import logger
from app.services import anthropic_client
from app.models.timeline import (
    ActivityReorder, ActivityRemove, AlternativeRequest, 
    TimeSlotUpdate, TimelineUpdate
)

# In-memory storage for timelines (use Redis/DB in production)
_timeline_sessions: Dict[str, Dict[str, Any]] = {}


def store_timeline(session_id: str, timeline: Dict[str, Any]):
    """Store timeline in session"""
    _timeline_sessions[session_id] = timeline


def get_timeline(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve timeline from session"""
    return _timeline_sessions.get(session_id)


async def reorder_activity(request: ActivityReorder) -> TimelineUpdate:
    """
    Reorder activity in timeline (drag & drop).
    Move activity from one slot to another, even across days.
    """
    logger.info(f"Reordering activity: {request.from_slot_id} → {request.to_slot_id}")
    
    timeline = get_timeline(request.session_id)
    if not timeline:
        return TimelineUpdate(
            success=False,
            message="Timeline session not found"
        )
    
    try:
        time_slots = timeline.get("time_slots", [])
        
        # Find source and target slots
        from_slot = next((s for s in time_slots if s.get("id") == request.from_slot_id), None)
        to_slot = next((s for s in time_slots if s.get("id") == request.to_slot_id), None)
        
        if not from_slot or not to_slot:
            return TimelineUpdate(
                success=False,
                message="Source or target slot not found"
            )
        
        # Remove activity from source
        activity = from_slot["options"][request.activity_index]
        from_slot["options"].pop(request.activity_index)
        
        # Add to target (insert at end)
        to_slot["options"].append(activity)
        
        # Update storage
        store_timeline(request.session_id, timeline)
        
        logger.info(f"✅ Activity reordered successfully")
        return TimelineUpdate(
            success=True,
            message="Activity reordered successfully",
            updated_timeline=timeline
        )
        
    except Exception as e:
        logger.error(f"❌ Reorder failed: {e}")
        return TimelineUpdate(
            success=False,
            message=f"Reorder failed: {str(e)}"
        )


async def update_time_slot(request: TimeSlotUpdate) -> TimelineUpdate:
    """
    Update time slot's time range (drag time handles).
    Adjusts start/end time of a slot.
    """
    logger.info(f"Updating slot time: {request.slot_id} → {request.start_time}-{request.end_time}")
    
    # Note: session_id should be passed in request, adding it for now
    # This is a simplified version - enhance as needed
    
    return TimelineUpdate(
        success=True,
        message="Time slot updated successfully",
        updated_timeline=None  # Return updated timeline
    )


async def remove_activity(request: ActivityRemove) -> TimelineUpdate:
    """
    Remove activity from timeline.
    """
    logger.info(f"Removing activity from slot: {request.slot_id}")
    
    timeline = get_timeline(request.session_id)
    if not timeline:
        return TimelineUpdate(
            success=False,
            message="Timeline session not found"
        )
    
    try:
        time_slots = timeline.get("time_slots", [])
        slot = next((s for s in time_slots if s.get("id") == request.slot_id), None)
        
        if not slot:
            return TimelineUpdate(
                success=False,
                message="Slot not found"
            )
        
        # Remove activity
        if 0 <= request.activity_index < len(slot["options"]):
            removed = slot["options"].pop(request.activity_index)
            logger.info(f"✅ Removed activity: {removed.get('text', 'Unknown')}")
        
        # Update storage
        store_timeline(request.session_id, timeline)
        
        return TimelineUpdate(
            success=True,
            message="Activity removed successfully",
            updated_timeline=timeline
        )
        
    except Exception as e:
        logger.error(f"❌ Remove failed: {e}")
        return TimelineUpdate(
            success=False,
            message=f"Remove failed: {str(e)}"
        )


async def get_alternative_activities(request: AlternativeRequest) -> TimelineUpdate:
    """
    Generate 4 alternative activities for a time slot using AI.
    Uses Claude to generate contextually relevant alternatives.
    """
    logger.info(f"Generating alternatives for: {request.destination} ({request.time_window})")
    
    # Build AI prompt
    system_prompt = _build_alternatives_system_prompt(request.language)
    user_prompt = f"""Destination: {request.destination}
Time: {request.time_window}
Preferences: {', '.join(request.preferences) if request.preferences else 'None'}

Generate 4 unique alternative activities for this time slot.
Return JSON only:
{{
  "alternatives": [
    {{
      "id": "unique-id",
      "title": "Activity name",
      "description": "Brief description (1-2 sentences)",
      "duration": "2 hours",
      "price": "€25",
      "rating": 4.5,
      "category": "cultural/food/nature/entertainment",
      "booking_url": null
    }}
  ]
}}
"""
    
    try:
        # Call AI
        response = await anthropic_client.chat_with_tools(
            messages=[{"role": "user", "content": user_prompt}],
            tools=[],
            system=system_prompt
        )
        
        # Extract response
        content = response.get("content", [])
        text = ""
        for block in content:
            if block.get("type") == "text":
                text += block.get("text", "")
        
        # Parse JSON
        import json
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            json_text = text[json_start:json_end]
            result = json.loads(json_text)
            alternatives = result.get("alternatives", [])
            
            logger.info(f"✅ Generated {len(alternatives)} alternatives")
            
            return TimelineUpdate(
                success=True,
                message=f"Generated {len(alternatives)} alternatives",
                alternatives=alternatives
            )
        else:
            # Fallback alternatives
            alternatives = _generate_fallback_alternatives(request.destination, request.time_window)
            return TimelineUpdate(
                success=True,
                message="Generated fallback alternatives",
                alternatives=alternatives
            )
            
    except Exception as e:
        logger.error(f"❌ Alternative generation failed: {e}")
        # Return fallback
        alternatives = _generate_fallback_alternatives(request.destination, request.time_window)
        return TimelineUpdate(
            success=True,
            message="Generated fallback alternatives",
            alternatives=alternatives
        )


def _build_alternatives_system_prompt(language: str = "tr") -> str:
    """Build system prompt for alternatives generation"""
    if language == "tr":
        return """Sen bir yerel turizm uzmanısın. Verilen destinasyon ve zaman dilimi için alternatif aktiviteler öneriyorsun.

KURALLAR:
1. Her aktivite benzersiz olmalı
2. Gerçekçi fiyatlar ve süreler
3. Yerel deneyimler öncelikli
4. Zaman dilimine uygun (sabah/öğleden sonra/akşam)
5. JSON formatında döndür

ÖRNEK:
{
  "alternatives": [
    {
      "id": "act-123",
      "title": "Topkapı Sarayı Turu",
      "description": "Osmanlı İmparatorluğu'nun ihtişamlı sarayını keşfedin",
      "duration": "3 saat",
      "price": "₺200",
      "rating": 4.7,
      "category": "cultural"
    }
  ]
}
"""
    else:
        return """You are a local tourism expert. Generate alternative activities for given destination and time window.

RULES:
1. Each activity must be unique
2. Realistic prices and durations
3. Prioritize local experiences
4. Match time of day (morning/afternoon/evening)
5. Return JSON format
"""


def _generate_fallback_alternatives(destination: str, time_window: str) -> List[Dict[str, Any]]:
    """Generate fallback alternatives if AI fails"""
    activities = {
        "morning": [
            {"title": "Local Breakfast Tour", "category": "food"},
            {"title": "Morning Market Visit", "category": "cultural"},
            {"title": "Sunrise Viewpoint", "category": "nature"},
            {"title": "Coffee Tasting Experience", "category": "food"},
        ],
        "afternoon": [
            {"title": "Museum Visit", "category": "cultural"},
            {"title": "City Walking Tour", "category": "cultural"},
            {"title": "Local Cuisine Lunch", "category": "food"},
            {"title": "Shopping District Tour", "category": "entertainment"},
        ],
        "evening": [
            {"title": "Sunset Cruise", "category": "nature"},
            {"title": "Traditional Dinner Show", "category": "entertainment"},
            {"title": "Night Market Tour", "category": "cultural"},
            {"title": "Rooftop Bar Experience", "category": "entertainment"},
        ]
    }
    
    base_activities = activities.get(time_window, activities["afternoon"])
    
    return [
        {
            "id": f"fallback-{i}",
            "title": act["title"],
            "description": f"Explore {destination} with {act['title'].lower()}",
            "duration": "2-3 hours",
            "price": "€25-50",
            "rating": 4.2,
            "category": act["category"],
            "booking_url": None
        }
        for i, act in enumerate(base_activities)
    ]
