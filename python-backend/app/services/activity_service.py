"""
Activity Service - Plans daily itineraries and activities.
Uses AI to create day-by-day schedules based on destination, dates, and preferences.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio

from app.core.logging import logger
from app.services import anthropic_client
from app.models.plan import TripPlan

# Cache for AI-generated activities (key: f"{destination}_{num_days}_{language}")
_ACTIVITY_CACHE: Dict[str, Dict[str, Any]] = {}


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
    flight_arrival_time: Optional[str] = None,  # NEW: First day start time
    flight_departure_time: Optional[str] = None,  # NEW: Last day end time
    hotel_checkin_time: str = "14:00",  # NEW: Hotel check-in
    hotel_checkout_time: str = "11:00"  # NEW: Hotel check-out
) -> Dict[str, Any]:
    """
    Plan daily activities with REAL time constraints from flights/hotels.
    
    **SMART SCHEDULING:**
    - Day 1: Activities start AFTER flight arrival + hotel check-in
    - Last Day: Activities end BEFORE hotel checkout + flight departure
    - Middle days: Full day activities
    
    Args:
        destination: City/destination name
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        flight_arrival_time: First day flight arrival (HH:MM)
        flight_departure_time: Last day flight departure (HH:MM)
        hotel_checkin_time: Hotel check-in time (HH:MM)
        hotel_checkout_time: Hotel check-out time (HH:MM)
        adults: Number of adults
        children: Number of children
        preferences: User preferences
        budget: Budget level
        weather_data: Weather forecast
        language: Response language
    
    Returns:
        {
            "time_slots": [...],  # Each with 4 REAL activity options
            "summary": "...",
            "constraints": {
                "day1_start": "15:00",  # After arrival + check-in
                "last_day_end": "10:00"  # Before checkout
            }
        }
    """
    logger.info(f"Planning activities for {destination}: {start_date} to {end_date}")
    logger.info(f"Flight times - Arrival: {flight_arrival_time}, Departure: {flight_departure_time}")
    
    # Calculate number of days
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    num_days = (end - start).days + 1
    
    # Calculate activity start/end times for each day
    day_constraints = _calculate_day_constraints(
        num_days=num_days,
        flight_arrival_time=flight_arrival_time,
        flight_departure_time=flight_departure_time,
        hotel_checkin_time=hotel_checkin_time,
        hotel_checkout_time=hotel_checkout_time
    )
    
    # Generate activities with real constraints
    return await _generate_activities_with_constraints(
        destination=destination,
        num_days=num_days,
        start_date=start_date,
        adults=adults,
        children=children,
        preferences=preferences,
        budget=budget,
        day_constraints=day_constraints,
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


def _calculate_day_constraints(
    num_days: int,
    flight_arrival_time: Optional[str],
    flight_departure_time: Optional[str],
    hotel_checkin_time: str,
    hotel_checkout_time: str
) -> List[Dict[str, str]]:
    """
    Calculate start/end times for each day based on flights and hotel.
    
    Returns: [{"day": 1, "start": "16:00", "end": "22:00"}, ...]
    """
    constraints = []
    
    for day in range(1, num_days + 1):
        if day == 1:
            # First day: Start after flight arrival + check-in
            if flight_arrival_time:
                # Parse arrival time and add 2 hours for immigration/transport/check-in
                try:
                    hour, minute = map(int, flight_arrival_time.split(":"))
                    arrival_minutes = hour * 60 + minute
                    start_minutes = arrival_minutes + 120  # +2 hours buffer
                    
                    # Ensure not before hotel check-in
                    checkin_h, checkin_m = map(int, hotel_checkin_time.split(":"))
                    checkin_minutes = checkin_h * 60 + checkin_m
                    start_minutes = max(start_minutes, checkin_minutes + 30)  # 30min after check-in
                    
                    start_h = start_minutes // 60
                    start_m = start_minutes % 60
                    day_start = f"{start_h:02d}:{start_m:02d}"
                except:
                    day_start = "16:00"  # Default late afternoon
            else:
                day_start = hotel_checkin_time
            
            constraints.append({"day": day, "start": day_start, "end": "22:00"})
            
        elif day == num_days:
            # Last day: End before checkout + flight
            if flight_departure_time:
                try:
                    hour, minute = map(int, flight_departure_time.split(":"))
                    depart_minutes = hour * 60 + minute
                    end_minutes = depart_minutes - 180  # -3 hours before flight
                    
                    # Ensure not after hotel checkout
                    checkout_h, checkout_m = map(int, hotel_checkout_time.split(":"))
                    checkout_minutes = checkout_h * 60 + checkout_m
                    end_minutes = min(end_minutes, checkout_minutes - 30)  # 30min before checkout
                    
                    end_h = end_minutes // 60
                    end_m = end_minutes % 60
                    day_end = f"{end_h:02d}:{end_m:02d}"
                except:
                    day_end = "10:00"  # Default morning
            else:
                day_end = hotel_checkout_time
            
            constraints.append({"day": day, "start": "08:00", "end": day_end})
        else:
            # Middle days: Full day
            constraints.append({"day": day, "start": "08:00", "end": "22:00"})
    
    return constraints


async def _generate_activities_with_constraints(
    destination: str,
    num_days: int,
    start_date: str,
    adults: int,
    children: int,
    preferences: List[str],
    budget: Optional[str],
    day_constraints: List[Dict[str, str]],
    language: str
) -> Dict[str, Any]:
    """Generate activities respecting flight/hotel time constraints."""
    
    # Check cache
    cache_key = f"{destination}_{num_days}_{language}_{','.join(sorted(preferences))}"
    if cache_key in _ACTIVITY_CACHE:
        logger.info(f"✅ Using cached activities for {destination}")
        return _ACTIVITY_CACHE[cache_key]
    
    # Build smart AI prompt with time constraints
    constraints_desc = "\n".join([
        f"Day {c['day']}: Activities from {c['start']} to {c['end']}" 
        for c in day_constraints
    ])
    
    system_prompt = f"""You are a local travel expert in {destination}. Create REAL, SPECIFIC activity options.

**TIME CONSTRAINTS (CRITICAL):**
{constraints_desc}

Day 1: Limited time (flight arrival + hotel check-in)
Day {num_days}: Limited time (hotel checkout + flight departure)

**RULES:**
- Use REAL place names in {destination}
- "Brandenburg Gate", "Curry 36", "Museum Island" not "generic museum"
- Include address/neighborhood
- Respect time constraints above
- 4 options per time slot
- Mix popular + hidden gems

Return JSON:
{{"time_slots": [
  {{
    "day": 1,
    "time": "16:00-18:00",
    "label": "evening",
    "options": [
      {{"text": "Real place name", "description": "Why visit", "location": "Area"}},
      ...4 options
    ]
  }}
]}}

Language: {"Turkish" if language == "tr" else "English"}"""

    user_prompt = f"""Plan {destination} activities:
Days: {num_days} ({start_date})
Travelers: {adults} adults, {children} children
Preferences: {', '.join(preferences) if preferences else 'varied'}
Budget: {budget or 'mid'}

Time constraints:
{constraints_desc}

Generate realistic time slots with 4 REAL options each."""

    try:
        # AI call with retry
        for attempt in range(3):
            try:
                response = await anthropic_client.chat_with_tools(
                    messages=[{"role": "user", "content": user_prompt}],
                    tools=[],
                    system=system_prompt
                )
                break
            except Exception as e:
                if "429" in str(e):
                    if attempt < 2:
                        await asyncio.sleep(2 * (attempt + 1))
                    else:
                        raise
                else:
                    raise
        
        # Parse AI response
        text = "".join([b.get("text", "") for b in response.get("content", []) if b.get("type") == "text"])
        
        import json
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        
        if json_start != -1 and json_end > json_start:
            data = json.loads(text[json_start:json_end])
            slots = data.get("time_slots", [])
            
            formatted = []
            for slot in slots:
                opts = slot.get("options", [])
                formatted.append({
                    "day": slot.get("day"),
                    "date": (datetime.fromisoformat(start_date) + timedelta(days=slot.get("day", 1) - 1)).isoformat(),
                    "time": slot.get("time"),
                    "label": slot.get("label"),
                    "selected": opts[0] if opts else None,
                    "alternatives": opts[1:4] if len(opts) > 1 else []
                })
            
            result = {
                "time_slots": formatted,
                "summary": f"{num_days} günlük {destination} - Gerçek yerler, uçuş/otel saatlerine göre" if language == "tr" else f"{num_days}-day {destination} - Real places, flight/hotel adjusted",
                "tips": _get_destination_tips(destination, language),
                "constraints": day_constraints
            }
            
            _ACTIVITY_CACHE[cache_key] = result
            logger.info(f"✅ AI activities generated and cached for {destination}")
            return result
            
    except Exception as e:
        logger.error(f"AI failed ({e}), using fallback")
    
    # Fallback to templates if AI fails
    return _generate_template_activities(destination, num_days, start_date, day_constraints, language)


def _generate_template_activities(
    destination: str,
    num_days: int,
    start_date: str,
    day_constraints: List[Dict[str, str]],
    language: str
) -> Dict[str, Any]:
    """Fallback: template-based activities."""
    time_slots = []
    
    for constraint in day_constraints:
        day = constraint["day"]
        day_date = datetime.fromisoformat(start_date) + timedelta(days=day - 1)
        
        # Simple time blocks for fallback
        blocks = [("09:00-12:00", "morning"), ("14:00-18:00", "afternoon"), ("19:00-22:00", "evening")]
        
        for time_range, label in blocks:
            alternatives = _get_activity_alternatives(
                destination=destination,
                day=day,
                time_label=label,
                preferences=[],
                children=0,
                language=language
            )
            
            time_slots.append({
                "day": day,
                "date": day_date.isoformat(),
                "time": time_range,
                "label": label,
                "selected": alternatives[0] if alternatives else None,
                "alternatives": alternatives[1:] if len(alternatives) > 1 else []
            })
    
    return {
        "time_slots": time_slots,
        "summary": f"{num_days} günlük {destination}" if language == "tr" else f"{num_days}-day {destination}",
        "tips": _get_destination_tips(destination, language)
    }



def _get_destination_tips(destination: str, language: str) -> List[str]:
    """Get helpful tips based on destination."""
    if language == "tr":
        return [
            f"{destination} için önceden rezervasyon önerilir",
            "Rahat ayakkabı giyin - çok yürüyeceksiniz",
            "Yerel para birimi kullanın"
        ]
    else:
        return [
            f"Pre-booking recommended for {destination}",
            "Wear comfortable shoes - lots of walking",
            "Use local currency"
        ]


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

