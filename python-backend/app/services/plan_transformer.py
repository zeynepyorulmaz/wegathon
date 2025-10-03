"""
Transform TripPlan to InteractivePlan format for frontend.
Generates multiple options for each time slot using AI.
"""
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta

from app.models.interactive_plan import InteractivePlan, TimeSlot, ActivityOption
from app.services import anthropic_client
from app.core.logging import logger


# Time block to time range mapping
BLOCK_TIME_RANGES = {
    "morning": ("08:00", "12:00"),
    "afternoon": ("12:00", "17:00"),
    "evening": ("17:00", "22:00"),
    "late-night": ("22:00", "02:00"),
    "check-in": ("14:00", "15:00"),
    "check-out": ("10:00", "11:00"),
    "transit": ("06:00", "08:00"),
}


async def generate_time_slot_options(
    day_num: int,
    block_label: str,
    existing_items: List[Dict[str, Any]],
    destination: str,
    language: str = "tr"
) -> List[ActivityOption]:
    """
    Generate multiple activity options for a time slot using AI.
    Takes existing activities and expands them into 4 varied options.
    """
    # If we already have multiple items, use them as options
    if len(existing_items) >= 3:
        options = []
        for item in existing_items[:4]:
            if item.get("title"):  # Only if title exists
                options.append(ActivityOption(
                    text=item.get("title", ""),
                    description=item.get("description", "Explore this activity"),
                    price=item.get("price"),
                    duration=item.get("duration"),
                    location=item.get("location")
                ))
        if options:
            return options
    
    # Generate new options using AI (even if items exist, we'll enhance them)
    existing_activity = existing_items[0] if existing_items and existing_items[0].get("title") else None
    
    # Generate template-based options for different traveler types
    templates = get_activity_templates(block_label, destination, day_num, language)
    
    # If we have an existing activity, use it as first option
    options = []
    if existing_activity and existing_activity.get("title"):
        options.append(ActivityOption(
            text=existing_activity.get("title", ""),
            description=existing_activity.get("description", "Tavsiye edilen aktivite" if language == "tr" else "Recommended activity")
        ))
    
    # Add template options
    for template in templates[:4 - len(options)]:
        options.append(ActivityOption(
            text=template["text"],
            description=template["description"]
        ))
    
    # Ensure we have at least 4 options
    while len(options) < 4:
        options.append(ActivityOption(
            text="Serbest zaman" if language == "tr" else "Free time",
            description="Kendi keşfinize çıkın" if language == "tr" else "Explore at your own pace"
        ))
    
    return options[:4]


def get_activity_templates(
    block_label: str,
    destination: str,
    day_num: int,
    language: str = "tr"
) -> List[Dict[str, str]]:
    """Get template activities based on time of day."""
    
    if language == "tr":
        if block_label == "morning":
            return [
                {
                    "text": f"{destination}'da yerel bir kafede kahvaltı",
                    "description": "Yerel lezzetleri deneyimlemek isteyenler için ideal."
                },
                {
                    "text": f"Otelde kahvaltı sonrası şehir yürüyüşü",
                    "description": "Rahat başlangıç; şehri tanımak isteyenler için mükemmel."
                },
                {
                    "text": f"{destination}'nın ünlü müzelerini ziyaret",
                    "description": "Kültür ve sanat meraklıları için harika bir seçenek."
                },
                {
                    "text": f"Yerel pazarları keşfetme turu",
                    "description": "Otantik deneyim arayanlar için eğlenceli bir başlangıç."
                }
            ]
        elif block_label == "afternoon":
            return [
                {
                    "text": f"{destination}'nın tarihi yerlerini gezme",
                    "description": "Tarih meraklıları için kapsamlı bir tur."
                },
                {
                    "text": f"Yerel restoranlarda öğle yemeği ve alışveriş",
                    "description": "Rahat ve keyifli bir öğleden sonra geçirmek isteyenler için."
                },
                {
                    "text": f"Şehir parklarında piknik ve dinlenme",
                    "description": "Doğa ve huzur arayanlar için ideal."
                },
                {
                    "text": f"Rehberli şehir turu",
                    "description": "Şehri detaylı öğrenmek isteyenler için bilgilendirici."
                }
            ]
        elif block_label == "evening":
            return [
                {
                    "text": f"{destination}'da yerel mutfak restoranında akşam yemeği",
                    "description": "Yerel lezzetleri tatmak isteyenler için mükemmel."
                },
                {
                    "text": f"Gece manzara turu",
                    "description": "Şehrin gece güzelliğini görmek isteyenler için unutulmaz."
                },
                {
                    "text": f"Canlı müzik barı veya lounge",
                    "description": "Gece hayatını deneyimlemek isteyenler için eğlenceli."
                },
                {
                    "text": f"Otelde dinlenme ve kahve keyfi",
                    "description": "Sakin bir akşam geçirmek isteyenler için rahat seçenek."
                }
            ]
        else:  # late-night, check-in, etc.
            return [
                {
                    "text": "Otelde dinlenme",
                    "description": "Enerji toplamak için ideal."
                },
                {
                    "text": f"{destination} sokak lezzetlerini deneme",
                    "description": "Hafif atıştırmalık arayanlar için."
                },
                {
                    "text": "Yakın çevrede yürüyüş",
                    "description": "Rahatlamak ve ortamı tanımak için uygun."
                },
                {
                    "text": "Otel çevresinde keşif",
                    "description": "Yakın alanı öğrenmek isteyenler için."
                }
            ]
    else:  # English
        if block_label == "morning":
            return [
                {
                    "text": f"Breakfast at local café in {destination}",
                    "description": "Ideal for experiencing local flavors."
                },
                {
                    "text": f"Hotel breakfast followed by city walk",
                    "description": "Perfect for a relaxed start and getting to know the city."
                },
                {
                    "text": f"Visit famous museums in {destination}",
                    "description": "Great option for culture and art enthusiasts."
                },
                {
                    "text": f"Explore local markets tour",
                    "description": "Fun start for those seeking authentic experiences."
                }
            ]
        elif block_label == "afternoon":
            return [
                {
                    "text": f"Explore historical sites in {destination}",
                    "description": "Comprehensive tour for history buffs."
                },
                {
                    "text": f"Lunch at local restaurants and shopping",
                    "description": "For those wanting a relaxed and enjoyable afternoon."
                },
                {
                    "text": f"Picnic and relaxation in city parks",
                    "description": "Ideal for nature and peace seekers."
                },
                {
                    "text": f"Guided city tour",
                    "description": "Informative for those wanting to learn the city in detail."
                }
            ]
        elif block_label == "evening":
            return [
                {
                    "text": f"Dinner at local cuisine restaurant in {destination}",
                    "description": "Perfect for tasting local flavors."
                },
                {
                    "text": f"Night sightseeing tour",
                    "description": "Unforgettable for seeing the city's night beauty."
                },
                {
                    "text": f"Live music bar or lounge",
                    "description": "Fun for experiencing nightlife."
                },
                {
                    "text": f"Relax at hotel with coffee",
                    "description": "Comfortable option for a quiet evening."
                }
            ]
        else:
            return [
                {
                    "text": "Rest at hotel",
                    "description": "Ideal for recharging."
                },
                {
                    "text": f"Try {destination} street food",
                    "description": "For those looking for light snacks."
                },
                {
                    "text": "Walk in nearby area",
                    "description": "Suitable for relaxing and exploring the surroundings."
                },
                {
                    "text": "Explore hotel vicinity",
                    "description": "For those wanting to learn the nearby area."
                }
            ]


def split_block_into_time_slots(
    block_label: str,
    items: List[Dict[str, Any]]
) -> List[tuple]:
    """
    Split a block into hourly time slots.
    Returns list of (start_time, end_time) tuples.
    """
    base_start, base_end = BLOCK_TIME_RANGES.get(block_label, ("09:00", "12:00"))
    
    # Parse times
    start_h, start_m = map(int, base_start.split(":"))
    end_h, end_m = map(int, base_end.split(":"))
    
    # Calculate duration
    total_minutes = (end_h * 60 + end_m) - (start_h * 60 + start_m)
    
    # For long blocks, split into 2-3 hour chunks
    if total_minutes > 180:  # More than 3 hours
        chunk_duration = 120  # 2 hour chunks
    else:
        chunk_duration = total_minutes  # Use whole block
    
    slots = []
    current_h, current_m = start_h, start_m
    
    while (current_h * 60 + current_m) < (end_h * 60 + end_m):
        slot_start = f"{current_h:02d}:{current_m:02d}"
        
        # Calculate end time
        end_minutes = current_h * 60 + current_m + chunk_duration
        slot_end_h = end_minutes // 60
        slot_end_m = end_minutes % 60
        
        # Don't exceed block end
        if slot_end_h > end_h or (slot_end_h == end_h and slot_end_m > end_m):
            slot_end_h, slot_end_m = end_h, end_m
        
        slot_end = f"{slot_end_h:02d}:{slot_end_m:02d}"
        
        slots.append((slot_start, slot_end))
        
        # Move to next slot
        current_h = slot_end_h
        current_m = slot_end_m
    
    return slots


async def transform_to_interactive(
    trip_plan: Dict[str, Any],
    language: str = "tr"
) -> InteractivePlan:
    """
    Transform a TripPlan into InteractivePlan format.
    Each time slot will have multiple activity options.
    """
    days = trip_plan.get("days", [])
    destination = trip_plan.get("query", {}).get("parsed", {}).get("destinationCity", "")
    
    all_time_slots: List[TimeSlot] = []
    
    for day_idx, day in enumerate(days):
        day_num = day_idx + 1
        blocks = day.get("blocks", [])
        
        # If no blocks, create default blocks
        if not blocks or all(len(b.get("items", [])) == 0 for b in blocks):
            logger.info(f"Day {day_num} has empty blocks, creating default structure")
            blocks = [
                {"label": "morning", "items": []},
                {"label": "afternoon", "items": []},
                {"label": "evening", "items": []}
            ]
        
        for block in blocks:
            label = block.get("label", "morning")
            items = block.get("items", [])
            
            # Split block into time slots
            time_ranges = split_block_into_time_slots(label, items)
            
            for start_time, end_time in time_ranges:
                # Generate options for this time slot
                options = await generate_time_slot_options(
                    day_num=day_num,
                    block_label=label,
                    existing_items=items,
                    destination=destination,
                    language=language
                )
                
                time_slot = TimeSlot(
                    day=day_num,
                    startTime=start_time,
                    endTime=end_time,
                    options=options,
                    block_type=label
                )
                
                all_time_slots.append(time_slot)
    
    # Build interactive plan
    interactive_plan = InteractivePlan(
        trip_summary=trip_plan.get("summary", ""),
        destination=destination,
        start_date=trip_plan.get("query", {}).get("parsed", {}).get("startDateISO", ""),
        end_date=trip_plan.get("query", {}).get("parsed", {}).get("endDateISO", ""),
        total_days=len(days),
        time_slots=all_time_slots,
        flights=trip_plan.get("flights"),
        lodging=trip_plan.get("lodging"),
        pricing=trip_plan.get("pricing"),
        weather=trip_plan.get("weather")
    )
    
    return interactive_plan

