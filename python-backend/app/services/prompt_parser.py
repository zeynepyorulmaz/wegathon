"""
Natural language prompt parser using LLM to extract structured travel data.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.models.parser_schemas import ParsedTripPrompt
from app.services import anthropic_client
from app.core.logging import logger


# Country code mapping
_COUNTRY_MAP = {
    # Turkish
    "türkiye": "TR",
    "turkiye": "TR",
    "turkey": "TR",
    "almanya": "DE",
    "almanca": "DE",
    "alm": "DE",
    "almanya cumhuriyeti": "DE",
    "fransa": "FR",
    "france": "FR",
    "ingiltere": "GB",
    "united kingdom": "GB",
    "uk": "GB",
    "ispanya": "ES",
    "spain": "ES",
    "italya": "IT",
    "italy": "IT",
    "yunanistan": "GR",
    "greece": "GR",
    # English common
    "germany": "DE",
    "deutschland": "DE",
    "united states": "US",
    "usa": "US",
}


PARSING_SYSTEM_PROMPT = """You are an expert travel prompt parser. Extract structured information from natural language travel requests.

**Output a strict JSON object** with these fields:

```json
{
  "departure": {
    "city": "İstanbul",
    "country": "TR",
    "detected": false
  },
  "destination": {
    "city": "Berlin",
    "country": "DE",
    "detected": true
  },
  "dates": {
    "start_date": "2025-10-15",
    "duration": 4,
    "end_date": "2025-10-18",
    "flexible": false
  },
  "travelers": {
    "composition": "couple",
    "count": 2,
    "children": []
  },
  "budget": {
    "amount": null,
    "currency": "TRY",
    "per_person": false,
    "specified": false
  },
  "travel_style": {
    "type": "mid_range",
    "luxury_level": "mid_range",
    "tempo": "balanced"
  },
  "preferences": [],
  "special_occasions": []
}
```

**Rules:**
1. **departure.detected**: false if not mentioned or assumed (default: İstanbul), true if explicitly stated
2. **destination.detected**: true if mentioned
3. **dates.start_date**: YYYY-MM-DD format
   - **CRITICAL**: Today is 2025-10-04. Use the CURRENT YEAR (2025) for all dates!
   - If a date like "9 Ekim" or "Dec 25" is mentioned WITHOUT year:
     * If the date is in the PAST (before today), assume NEXT YEAR (2026)
     * If the date is in the FUTURE (after today), use CURRENT YEAR (2025)
   - Examples:
     * "9 Ekim" → 2025-10-09 (5 days from today, use 2025)
     * "1 Ocak" → 2026-01-01 (past this year, use next year)
   - If no specific date mentioned, use 7 days from today (2025-10-11)
   - If "next week", use 7-14 days from today
   - If "next month", use 30 days from today
   - NEVER use today's date unless explicitly stated "today" or "tomorrow"
4. **dates.duration**: integer days
5. **dates.end_date**: YYYY-MM-DD calculated from start + duration
6. **travelers.composition**: "solo", "couple", "family", "friends", "group"
7. **travelers.count**: total adults + children
8. **travelers.children**: array of {"age": N} if mentioned
9. **budget.specified**: true if amount mentioned, false otherwise
10. **budget.currency**: ISO code (TRY, USD, EUR)
11. **travel_style.type**: "budget", "mid_range", "luxury", "backpacker"
12. **travel_style.luxury_level**: "budget", "mid_range", "luxury"
13. **travel_style.tempo**: "relaxed", "balanced", "packed"
14. **preferences**: array of interests ["museums", "food", "nightlife", "nature", "adventure", "culture"]
15. **special_occasions**: array ["honeymoon", "anniversary", "birthday", "business"]

**IMPORTANT**: Return ONLY valid JSON. No explanations.
"""


def _iso_country(value: Optional[str]) -> Optional[str]:
    """Convert country name to ISO 2-letter code."""
    if not value:
        return value
    v = value.strip()
    if len(v) == 2 and v.isalpha() and v.upper() == v:
        return v
    key = v.lower()
    return _COUNTRY_MAP.get(key, v[:2].upper() if len(v) >= 2 else v)


def _parse_duration_to_int(value: Any) -> Optional[int]:
    """Extract integer duration from various formats."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        # Extract all integers in the string, e.g. "3-4 gün" -> [3, 4]
        nums = [int(n) for n in re.findall(r"\d+", value)]
        if not nums:
            return None
        # If a range is given, choose the max to be conservative
        return max(nums)
    return None


def _compute_end_date_if_missing(d: Dict[str, Any]) -> None:
    """Calculate end_date from start_date + duration if missing."""
    start = d.get("start_date")
    duration = d.get("duration")
    if start and duration and not d.get("end_date"):
        try:
            dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = dt + timedelta(days=int(duration) - 1 if int(duration) > 0 else 0)
            d["end_date"] = end_dt.strftime("%Y-%m-%d")
        except Exception:
            pass


def _normalize_to_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize parsed data to expected schema."""
    out = dict(data)

    # Departure
    departure = dict(out.get("departure") or {})
    if departure:
        if "country" in departure:
            departure["country"] = _iso_country(departure.get("country"))
        if "detected" not in departure:
            city = (departure.get("city") or "").lower()
            country = (departure.get("country") or "").upper()
            assumed_istanbul = city in {"istanbul", "i̇stanbul"} and country in {"TR", ""}
            departure["detected"] = False if assumed_istanbul else True
        out["departure"] = departure

    # Destination
    destination = dict(out.get("destination") or {})
    if destination:
        if "country" in destination:
            destination["country"] = _iso_country(destination.get("country"))
        if "detected" not in destination:
            destination["detected"] = True
        out["destination"] = destination

    # Dates
    dates = dict(out.get("dates") or {})
    if dates:
        if dates.get("duration") is not None and not isinstance(dates.get("duration"), int):
            dur = _parse_duration_to_int(dates.get("duration"))
            if dur is not None:
                dates["duration"] = dur
        _compute_end_date_if_missing(dates)
        out["dates"] = dates

    # Budget defaults
    budget = dict(out.get("budget") or {})
    if budget is not None:
        if budget.get("currency") in (None, ""):
            budget["currency"] = "TRY"
        if budget.get("amount") in (None, ""):
            budget["specified"] = False if budget.get("specified") is None else budget.get("specified")
        if budget.get("per_person") is None:
            budget["per_person"] = False
        out["budget"] = budget

    # Travelers
    travelers = dict(out.get("travelers") or {})
    if travelers:
        children_val = travelers.get("children")
        if not isinstance(children_val, list):
            travelers["children"] = []
        count_val = travelers.get("count")
        if isinstance(count_val, str):
            try:
                travelers["count"] = int(count_val)
            except Exception:
                pass
        elif isinstance(count_val, float):
            travelers["count"] = int(count_val)
        out["travelers"] = travelers

    # Travel style
    travel_style = dict(out.get("travel_style") or {})
    out["travel_style"] = travel_style

    # Arrays
    out["preferences"] = out.get("preferences") if isinstance(out.get("preferences"), list) else []
    out["special_occasions"] = out.get("special_occasions") if isinstance(out.get("special_occasions"), list) else []

    # Remove metadata
    out.pop("parsing_metadata", None)

    return out


def _extract_first_json_block(text: str) -> str:
    """Extract first JSON object from text."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in response")
    return text[start : end + 1]


async def parse_prompt(user_input: str, locale: str = "tr-TR") -> ParsedTripPrompt:
    """
    Parse natural language travel prompt into structured data using Anthropic.
    
    Args:
        user_input: Natural language travel request
        locale: Locale hint (default: tr-TR)
    
    Returns:
        ParsedTripPrompt with structured travel data
    """
    logger.info(f"parse_prompt: Parsing input: {user_input[:100]}...")
    
    # Get today's date dynamically
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year
    
    # Build dynamic system prompt with today's date
    dynamic_prompt = PARSING_SYSTEM_PROMPT.replace("2025-10-04", today).replace("CURRENT YEAR (2025)", f"CURRENT YEAR ({current_year})")
    
    # Call Anthropic with parsing prompt
    messages = [{"role": "user", "content": user_input}]
    
    try:
        response = await anthropic_client.chat_with_tools(
            messages=messages,
            tools=[],  # No tools needed for parsing
            system=dynamic_prompt
        )
        
        # Extract text from response
        content_blocks = response.get("content", [])
        raw_text = ""
        for block in content_blocks:
            if block.get("type") == "text":
                raw_text = block.get("text", "")
                break
        
        if not raw_text:
            raise ValueError("No text content in Anthropic response")
        
        logger.debug(f"parse_prompt: Raw response: {raw_text[:500]}...")
        
        # Parse JSON
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Try extracting JSON block
            data = json.loads(_extract_first_json_block(raw_text))
        
        # Normalize and validate
        normalized = _normalize_to_schema(data)
        parsed = ParsedTripPrompt.model_validate(normalized)
        
        logger.info(f"parse_prompt: Successfully parsed - {parsed.destination.city}, {parsed.dates.start_date}, {parsed.travelers.count} travelers")
        
        return parsed
        
    except Exception as e:
        logger.error(f"parse_prompt: Failed to parse prompt: {e}")
        raise ValueError(f"Failed to parse travel prompt: {str(e)}")

