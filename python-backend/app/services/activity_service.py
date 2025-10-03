"""
Activity Service - Plans daily itineraries and activities.
Uses AI to create day-by-day schedules based on destination, dates, and preferences.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.logging import logger
from app.services import anthropic_client
from app.models.plan import TripPlan


async def plan_activities(
    destination: str,
    start_date: str,
    end_date: str,
    adults: int = 2,
    children: int = 0,
    preferences: List[str] = [],
    budget: Optional[str] = None,
    weather_data: Optional[List[Dict]] = None,
    language: str = "tr",
    with_alternatives: bool = True
) -> Dict[str, Any]:
    """
    Plan daily activities and itinerary with ALTERNATIVES for each time slot.
    
    Args:
        destination: City/destination name
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        adults: Number of adults
        children: Number of children
        preferences: User preferences (e.g., ["museums", "food", "nature"])
        budget: Budget level ("low", "mid", "high")
        weather_data: Weather forecast data
        language: Response language
        with_alternatives: If True, generate multiple options per time slot
    
    Returns:
        {
            "time_slots": [
                {
                    "day": 1,
                    "time": "09:00-12:00",
                    "label": "morning",
                    "selected": {...},  # Default selected activity
                    "alternatives": [{...}, {...}, {...}]  # Alternative activities
                }
            ],
            "summary": "...",
            "tips": [...]
        }
    """
    logger.info(f"Planning activities for {destination}: {start_date} to {end_date} (with_alternatives={with_alternatives})")
    
    # Calculate number of days
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    num_days = (end - start).days + 1
    
    # If alternatives requested, use template-based generation
    if with_alternatives:
        return await _generate_activities_with_alternatives(
            destination=destination,
            num_days=num_days,
            start_date=start_date,
            adults=adults,
            children=children,
            preferences=preferences,
            budget=budget,
            language=language
        )
    
    # Build AI prompt
    system_prompt = _build_activity_system_prompt(language)
    user_prompt = _build_activity_user_prompt(
        destination=destination,
        num_days=num_days,
        start_date=start_date,
        adults=adults,
        children=children,
        preferences=preferences,
        budget=budget,
        weather_data=weather_data,
        language=language
    )
    
    # Call AI
    try:
        response = await anthropic_client.chat_with_tools(
            messages=[{"role": "user", "content": user_prompt}],
            tools=[],  # No tools needed, just text generation
            system=system_prompt
        )
        
        # Extract response
        content = response.get("content", [])
        text = ""
        for block in content:
            if block.get("type") == "text":
                text += block.get("text", "")
        
        # Parse JSON response
        import json
        
        # Try to extract JSON from response
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            json_text = text[json_start:json_end]
            result = json.loads(json_text)
        else:
            result = {"days": [], "summary": text, "tips": []}
        
        logger.info(f"✅ Activities planned: {num_days} days")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Activity planning failed: {e}")
        return {
            "days": _generate_fallback_itinerary(destination, num_days, start_date),
            "summary": f"{num_days} günlük {destination} seyahati planı",
            "tips": [],
            "error": str(e)
        }


def _build_activity_system_prompt(language: str = "tr") -> str:
    """Build system prompt for activity planning AI."""
    if language == "tr":
        return """Sen bir uzman seyahat planlayıcısısın. Günlük aktivite programları oluşturuyorsun.

GÖREV: Verilen destinasyon için gün gün detaylı itinerary oluştur.

FORMAT: Sadece JSON döndür:
```json
{
  "summary": "Seyahat özeti (2-3 cümle)",
  "days": [
    {
      "day": 1,
      "title": "Gün başlığı",
      "description": "Gün özeti",
      "blocks": [
        {
          "label": "morning",
          "time": "09:00-12:00",
          "description": "Ne yapılacak",
          "items": [
            {
              "title": "Aktivite başlığı",
              "description": "Aktivite detayı",
              "location": "Konum",
              "duration": "2 saat"
            }
          ]
        }
      ]
    }
  ],
  "tips": ["İpucu 1", "İpucu 2"]
}
```

KURALLAR:
- Her gün için: morning, afternoon, evening blokları
- Gerçekçi zamanlamalar
- Yerel öneriler
- Ulaşım süreleri dahil
- Çocuklu ailelere uygun (eğer çocuk varsa)
- Hava durumuna göre uyarla (eğer bilgi varsa)
"""
    else:
        return """You are an expert travel planner creating daily activity itineraries.

TASK: Create detailed day-by-day itinerary for given destination.

FORMAT: Return only JSON:
```json
{
  "summary": "Trip summary (2-3 sentences)",
  "days": [
    {
      "day": 1,
      "title": "Day title",
      "description": "Day summary",
      "blocks": [
        {
          "label": "morning",
          "time": "09:00-12:00",
          "description": "What to do",
          "items": [
            {
              "title": "Activity title",
              "description": "Activity details",
              "location": "Location",
              "duration": "2 hours"
            }
          ]
        }
      ]
    }
  ],
  "tips": ["Tip 1", "Tip 2"]
}
```

RULES:
- Each day: morning, afternoon, evening blocks
- Realistic timing
- Local recommendations
- Include travel times
- Family-friendly if kids present
- Adapt to weather if data available
"""


def _build_activity_user_prompt(
    destination: str,
    num_days: int,
    start_date: str,
    adults: int,
    children: int,
    preferences: List[str],
    budget: Optional[str],
    weather_data: Optional[List[Dict]],
    language: str
) -> str:
    """Build user prompt for activity planning."""
    
    if language == "tr":
        prompt = f"""Destinasyon: {destination}
Süre: {num_days} gün
Başlangıç tarihi: {start_date}
Yolcular: {adults} yetişkin"""
        
        if children > 0:
            prompt += f", {children} çocuk"
        
        if preferences:
            prompt += f"\nTercihler: {', '.join(preferences)}"
        
        if budget:
            prompt += f"\nBütçe: {budget}"
        
        if weather_data:
            prompt += f"\n\nHava durumu:\n"
            for w in weather_data[:num_days]:
                prompt += f"- {w.get('dateISO', '')}: {w.get('highC', '')}°C, yağmur ihtimali: {w.get('precipitationChance', 0)}%\n"
        
        prompt += f"\n\n{num_days} günlük detaylı aktivite programı oluştur. JSON formatında döndür."
        
    else:
        prompt = f"""Destination: {destination}
Duration: {num_days} days
Start date: {start_date}
Travelers: {adults} adults"""
        
        if children > 0:
            prompt += f", {children} children"
        
        if preferences:
            prompt += f"\nPreferences: {', '.join(preferences)}"
        
        if budget:
            prompt += f"\nBudget: {budget}"
        
        if weather_data:
            prompt += f"\n\nWeather forecast:\n"
            for w in weather_data[:num_days]:
                prompt += f"- {w.get('dateISO', '')}: {w.get('highC', '')}°C, precipitation: {w.get('precipitationChance', 0)}%\n"
        
        prompt += f"\n\nCreate detailed {num_days}-day activity itinerary. Return as JSON."
    
    return prompt


async def _generate_activities_with_alternatives(
    destination: str,
    num_days: int,
    start_date: str,
    adults: int,
    children: int,
    preferences: List[str],
    budget: Optional[str],
    language: str
) -> Dict[str, Any]:
    """
    Generate activities with multiple alternatives per time slot.
    Template-based for reliability and speed.
    """
    time_slots = []
    
    # Time blocks per day
    blocks = [
        ("09:00-12:00", "morning"),
        ("12:00-14:00", "lunch"),
        ("14:00-18:00", "afternoon"),
        ("18:00-22:00", "evening")
    ]
    
    for day_num in range(1, num_days + 1):
        day_date = datetime.fromisoformat(start_date) + timedelta(days=day_num - 1)
        
        for time_range, label in blocks:
            # Generate 4 alternatives for this time slot
            alternatives = _get_activity_alternatives(
                destination=destination,
                day=day_num,
                time_label=label,
                preferences=preferences,
                children=children,
                language=language
            )
            
            # First one is default selected
            time_slots.append({
                "day": day_num,
                "date": day_date.isoformat(),
                "time": time_range,
                "label": label,
                "selected": alternatives[0] if alternatives else None,
                "alternatives": alternatives[1:] if len(alternatives) > 1 else []
            })
    
    summary = f"{num_days} günlük {destination} seyahati" if language == "tr" else f"{num_days}-day trip to {destination}"
    
    return {
        "time_slots": time_slots,
        "summary": summary,
        "tips": [
            "Her aktiviteyi değiştirebilirsiniz" if language == "tr" else "You can change any activity",
            "Hava durumuna göre uyarlayın" if language == "tr" else "Adapt to weather conditions"
        ]
    }


def _get_activity_alternatives(
    destination: str,
    day: int,
    time_label: str,
    preferences: List[str],
    children: int,
    language: str
) -> List[Dict[str, Any]]:
    """Get 4 alternative activities for a time slot."""
    
    # Template alternatives based on time of day
    templates = {
        "morning": [
            {"type": "breakfast", "icon": "☕"},
            {"type": "museum", "icon": "🏛️"},
            {"type": "walking_tour", "icon": "🚶"},
            {"type": "market", "icon": "🛍️"}
        ],
        "lunch": [
            {"type": "local_restaurant", "icon": "🍽️"},
            {"type": "street_food", "icon": "🌮"},
            {"type": "cafe", "icon": "☕"},
            {"type": "picnic", "icon": "🧺"}
        ],
        "afternoon": [
            {"type": "attraction", "icon": "🎯"},
            {"type": "shopping", "icon": "🛍️"},
            {"type": "park", "icon": "🌳"},
            {"type": "cultural", "icon": "🎭"}
        ],
        "evening": [
            {"type": "dinner", "icon": "🍷"},
            {"type": "night_tour", "icon": "🌃"},
            {"type": "entertainment", "icon": "🎭"},
            {"type": "relax", "icon": "🛋️"}
        ]
    }
    
    alternatives = []
    
    for template in templates.get(time_label, templates["morning"]):
        activity = _generate_activity_from_template(
            destination=destination,
            template_type=template["type"],
            icon=template["icon"],
            day=day,
            time_label=time_label,
            children=children,
            language=language
        )
        alternatives.append(activity)
    
    return alternatives


def _generate_activity_from_template(
    destination: str,
    template_type: str,
    icon: str,
    day: int,
    time_label: str,
    children: int,
    language: str
) -> Dict[str, Any]:
    """Generate activity from template with localization."""
    
    # Activity templates (TR/EN)
    templates_tr = {
        "breakfast": ("Yerel kahvaltı", "Yerel lezzetleri tadın", "1-2 saat"),
        "museum": ("Müze ziyareti", "Kültür ve sanat keşfi", "2-3 saat"),
        "walking_tour": ("Yürüyüş turu", "Şehir merkezini keşfedin", "2-3 saat"),
        "market": ("Yerel pazarlar", "Otantik deneyim", "2 saat"),
        "local_restaurant": ("Yerel restoran", "Geleneksel mutfak", "1-2 saat"),
        "street_food": ("Sokak lezzetleri", "Hızlı ve otantik", "1 saat"),
        "cafe": ("Kafe molası", "Rahat bir ara", "1 saat"),
        "picnic": ("Park pikniği", "Doğada yemek", "2 saat"),
        "attraction": ("Önemli yerler", "Must-see attractions", "3-4 saat"),
        "shopping": ("Alışveriş", "Yerel mağazalar", "2-3 saat"),
        "park": ("Park gezisi", "Doğada dinlenme", "2 saat"),
        "cultural": ("Kültürel aktivite", "Yerel kültür", "2-3 saat"),
        "dinner": ("Akşam yemeği", "Yerel mutfak", "2 saat"),
        "night_tour": ("Gece turu", "Şehrin gece güzelliği", "2-3 saat"),
        "entertainment": ("Eğlence", "Gece hayatı", "3-4 saat"),
        "relax": ("Otelde dinlenme", "Rahat bir akşam", "Esnek"),
    }
    
    templates_en = {
        "breakfast": ("Local breakfast", "Taste local flavors", "1-2 hours"),
        "museum": ("Museum visit", "Culture and art", "2-3 hours"),
        "walking_tour": ("Walking tour", "Explore city center", "2-3 hours"),
        "market": ("Local markets", "Authentic experience", "2 hours"),
        "local_restaurant": ("Local restaurant", "Traditional cuisine", "1-2 hours"),
        "street_food": ("Street food", "Quick and authentic", "1 hour"),
        "cafe": ("Café break", "Relaxed pause", "1 hour"),
        "picnic": ("Park picnic", "Nature dining", "2 hours"),
        "attraction": ("Attractions", "Must-see sights", "3-4 hours"),
        "shopping": ("Shopping", "Local stores", "2-3 hours"),
        "park": ("Parks", "Nature relaxation", "2 hours"),
        "cultural": ("Cultural activity", "Local culture", "2-3 hours"),
        "dinner": ("Dinner", "Local cuisine", "2 hours"),
        "night_tour": ("Night tour", "City by night", "2-3 hours"),
        "entertainment": ("Entertainment", "Nightlife", "3-4 hours"),
        "relax": ("Hotel rest", "Quiet evening", "Flexible"),
    }
    
    templates = templates_tr if language == "tr" else templates_en
    title_text, desc_text, duration = templates.get(template_type, ("Activity", "Explore", "2 hours"))
    
    return {
        "title": f"{icon} {title_text} - {destination}" if "restaurant" not in template_type and "breakfast" not in template_type else f"{icon} {title_text}",
        "description": desc_text,
        "duration": duration
    }


def _generate_fallback_itinerary(destination: str, num_days: int, start_date: str) -> List[Dict[str, Any]]:
    """Generate simple fallback itinerary if AI fails."""
    days = []
    
    for i in range(num_days):
        day_date = datetime.fromisoformat(start_date) + timedelta(days=i)
        
        days.append({
            "day": i + 1,
            "dateISO": day_date.isoformat(),
            "title": f"Gün {i + 1}: {destination} Keşfi",
            "description": f"{destination}'da {i + 1}. gün aktiviteleri",
            "blocks": [
                {
                    "label": "morning",
                    "time": "09:00-12:00",
                    "description": "Sabah aktiviteleri",
                    "items": []
                },
                {
                    "label": "afternoon",
                    "time": "14:00-18:00",
                    "description": "Öğleden sonra aktiviteleri",
                    "items": []
                },
                {
                    "label": "evening",
                    "time": "19:00-22:00",
                    "description": "Akşam aktiviteleri",
                    "items": []
                }
            ]
        })
    
    return days

