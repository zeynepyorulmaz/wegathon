import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from app.models.plan import TripPlan, PlanRequest, ReviseRequest
from app.core.logging import logger
from app.services import anthropic_client
from app.tools import adapters
from app.tools.adapters import get_mcp_tools_schema


def _normalize_block_item_types(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Claude's sometimes-wrong type names to match our schema."""
    type_mapping = {
        "transport": "transfer",
        "accommodation": "lodging",
        "hotel": "lodging",
        "arrival": "flight",
        "departure": "flight",
    }
    
    days = data.get("days", [])
    for day in days:
        blocks = day.get("blocks", [])
        for block in blocks:
            items = block.get("items", [])
            for item in items:
                if "type" in item:
                    original_type = item["type"]
                    normalized_type = type_mapping.get(original_type, original_type)
                    if original_type != normalized_type:
                        logger.info(f"_normalize_block_item_types: Normalizing type '{original_type}' -> '{normalized_type}'")
                        item["type"] = normalized_type
    
    return data


def _json_only_guard(text: str) -> Dict[str, Any]:
    try:
        if not text or not text.strip():
            logger.error("_json_only_guard: Empty text received")
            raise ValueError("Empty text received")
        data = json.loads(text)
        return _normalize_block_item_types(data)
    except json.JSONDecodeError as e:
        logger.warning(f"_json_only_guard: Initial JSON parse failed, trying to extract JSON block. Error: {e}")
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1:
            extracted = text[s : e + 1]
            logger.info(f"_json_only_guard: Extracted JSON block (length: {len(extracted)})")
            data = json.loads(extracted)
            return _normalize_block_item_types(data)
        logger.error(f"_json_only_guard: No JSON found in text: {text[:200]}...")
        raise ValueError(f"No valid JSON found in response: {text[:200]}...")


def _as_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def normalize_to_contract(obj: Dict[str, Any]) -> Dict[str, Any]:
    now_iso = datetime.utcnow().isoformat() + "Z"

    query = obj.get("query") or {}
    if not isinstance(query, dict):
        query = {}
    raw = query.get("raw") or obj.get("prompt") or ""
    parsed = query.get("parsed") or {}
    if not isinstance(parsed, dict):
        parsed = {}
    # City name translation helper
    def normalize_city_name(city_name: str) -> str:
        if not city_name:
            return ""
        city_translations = {
            "istanbul": "Istanbul", "i̇stanbul": "Istanbul",
            "ankara": "Ankara", "izmir": "Izmir", "i̇zmir": "Izmir",
            "antalya": "Antalya", "roma": "Rome", "milano": "Milan",
            "venedik": "Venice", "floransa": "Florence", "napoli": "Naples",
            "paris": "Paris", "londra": "London", "barselona": "Barcelona",
            "madrid": "Madrid", "berlin": "Berlin", "münih": "Munich",
            "viyana": "Vienna", "prag": "Prague", "amsterdam": "Amsterdam",
            "brüksel": "Brussels", "cenevre": "Geneva", "zürih": "Zurich",
        }
        normalized = city_name.strip()
        lower_name = normalized.lower()
        return city_translations.get(lower_name, normalized)
    
    origin_raw = parsed.get("from") or obj.get("from") or parsed.get("originCity") or parsed.get("origin") or ""
    dest_raw = parsed.get("to") or obj.get("to") or parsed.get("destinationCity") or parsed.get("destination") or ""
    
    parsed.setdefault("originCity", normalize_city_name(origin_raw))
    parsed.setdefault("destinationCity", normalize_city_name(dest_raw))
    parsed.setdefault("startDateISO", parsed.get("startDate") or obj.get("startDate") or obj.get("date") or obj.get("start_date") or "")
    parsed.setdefault("endDateISO", parsed.get("endDate") or obj.get("endDate") or obj.get("end_date") or "")
    parsed.setdefault("nights", parsed.get("nights") or obj.get("nights") or 0)
    parsed.setdefault("adults", parsed.get("adults") or obj.get("adults") or 1)

    flights = obj.get("flights") or {}
    if not isinstance(flights, dict):
        flights = {}

    def ensure_segment_fields(seg: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "fromIata": seg.get("fromIata") or seg.get("from") or "",
            "toIata": seg.get("toIata") or seg.get("to") or "",
            "departISO": seg.get("departISO") or seg.get("depart") or "",
            "arriveISO": seg.get("arriveISO") or seg.get("arrival") or "",
            "airline": seg.get("airline") or "",
            "flightNumber": seg.get("flightNumber") or seg.get("number") or "",
            "durationMinutes": int(seg.get("durationMinutes") or seg.get("duration") or 0),
            "cabin": seg.get("cabin") or None,
        }

    def coerce_flight(val):
        if not isinstance(val, dict):
            return None
        segs_in = _as_list(val.get("segments"))
        if not segs_in:
            seg = {}
            for k in ("fromIata","toIata","departISO","arriveISO","airline","flightNumber","durationMinutes","cabin"):
                if k in val:
                    seg[k] = val[k]
            if seg:
                segs_in = [seg]
        segs = [ensure_segment_fields(s if isinstance(s, dict) else {}) for s in segs_in]
        provider = val.get("provider") or val.get("airline") or "unknown"
        
        # Normalize price - handle "7,880 TL" or similar formats
        price = val.get("price")
        if isinstance(price, str):
            # Remove currency symbols, commas, and extract just the number
            import re
            cleaned = re.sub(r'[^\d.]', '', price)
            try:
                price = float(cleaned) if cleaned else None
            except (ValueError, TypeError):
                price = None
        elif price is not None:
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = None
        
        return {"provider": provider, "currency": val.get("currency"), "price": price, "segments": segs, "bookingUrl": val.get("bookingUrl")}

    flights_norm = {
        "outbound": coerce_flight(flights.get("outbound") or flights.get("go") or flights.get("flight")),
        "inbound": coerce_flight(flights.get("inbound") or flights.get("return")),
        "alternatives": _as_list(flights.get("alternatives")) or None,
    }

    lodging_src = obj.get("lodging") or obj.get("hotel") or {}
    if not isinstance(lodging_src, dict):
        lodging_src = {}

    def coerce_hotel(val):
        if not isinstance(val, dict):
            return None
        
        # Normalize rating - handle "9.4/10" or string format
        rating = val.get("rating")
        if isinstance(rating, str):
            if "/" in rating:
                try:
                    rating = float(rating.split("/")[0])
                except (ValueError, TypeError):
                    rating = None
            else:
                try:
                    rating = float(rating)
                except (ValueError, TypeError):
                    rating = None
        elif rating is not None:
            try:
                rating = float(rating)
            except (ValueError, TypeError):
                rating = None
        
        # Normalize priceTotal - handle "62,286 TRY" or similar formats
        price = val.get("priceTotal") or val.get("price")
        if isinstance(price, str):
            import re
            cleaned = re.sub(r'[^\d.]', '', price)
            try:
                price = float(cleaned) if cleaned else None
            except (ValueError, TypeError):
                price = None
        elif price is not None:
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = None
        
        return {
            "provider": val.get("provider") or "unknown",
            "name": val.get("name") or val.get("hotel") or "",
            "address": val.get("address"),
            "checkInISO": val.get("checkInISO") or val.get("checkIn") or "",
            "checkOutISO": val.get("checkOutISO") or val.get("checkOut") or "",
            "priceTotal": price,
            "currency": val.get("currency"),
            "rating": rating,
            "amenities": val.get("amenities"),
            "neighborhood": val.get("neighborhood"),
            "bookingUrl": val.get("bookingUrl"),
        }

    lodging_norm = {
        "selected": coerce_hotel(lodging_src.get("selected") or lodging_src),
        "alternatives": _as_list(lodging_src.get("alternatives")) or None,
    }

    transport_src = obj.get("transport") or {}
    if not isinstance(transport_src, dict):
        transport_src = {}
    transport_norm = {
        "localPasses": _as_list(transport_src.get("localPasses")),
        "intercity": _as_list(transport_src.get("intercity")),
    }

    weather_src = obj.get("weather")
    weather_list = _as_list(weather_src)
    weather_norm = []
    for w in weather_list:
        if not isinstance(w, dict):
            continue
        weather_norm.append({
            "dateISO": w.get("dateISO") or w.get("date") or parsed.get("startDateISO") or "",
            "highC": w.get("highC") or w.get("high") or None,
            "lowC": w.get("lowC") or w.get("low") or None,
            "precipitationChance": w.get("precipitationChance") or w.get("precipChance") or None,
            "source": w.get("source") or "LLM",
            "isForecast": bool(w.get("isForecast", True)),
        })
    if not weather_norm:
        weather_norm = []

    days_src = _as_list(obj.get("days"))

    def coerce_block(b):
        if not isinstance(b, dict):
            return {"label": "transit", "items": []}
        
        # Normalize label - handle Turkish, time strings, or invalid values
        label = b.get("label") or b.get("time") or "morning"
        
        label_map = {
            "sabah": "morning",
            "öğleden sonra": "afternoon",
            "öğle": "afternoon",
            "akşam": "evening",
            "gece": "late-night",
            "check-in": "check-in",
            "check-out": "check-out",
            "transit": "transit",
            "ulaşım": "transit",
            "varış": "transit",
            "dönüş": "transit",
        }
        
        if isinstance(label, str):
            label_lower = label.lower().strip()
            
            # Check mapping
            if label_lower in label_map:
                label = label_map[label_lower]
            # Check if it's a time (HH:MM format)
            elif ":" in label and len(label) <= 5:
                try:
                    hour = int(label.split(":")[0])
                    if hour < 6:
                        label = "late-night"
                    elif hour < 12:
                        label = "morning"
                    elif hour < 18:
                        label = "afternoon"
                    else:
                        label = "evening"
                except:
                    label = "morning"
            # If not in valid labels, default to morning
            elif label_lower not in ["morning", "afternoon", "evening", "late-night", "transit", "check-in", "check-out"]:
                label = "morning"
        
        # Normalize items - convert to BlockItem format: {type, data}
        items_raw = _as_list(b.get("items"))
        items_normalized = []
        for item in items_raw:
            if isinstance(item, str):
                # Claude returned plain string like "09:50 - Flight departure"
                # Convert to BlockItem schema: {type: "activity", data: {}}
                items_normalized.append({
                    "type": "activity",
                    "data": {
                        "provider": "manual",
                        "title": item,
                        "notes": item
                    }
                })
            elif isinstance(item, dict):
                # Check if already has type/data format
                if "type" in item and "data" in item:
                    items_normalized.append(item)
                else:
                    # Old format or partial - normalize to BlockItem schema
                    item_type = item.get("type", "activity")
                    items_normalized.append({
                        "type": item_type,
                        "data": item.get("data", {
                            "provider": "manual",
                            "title": item.get("text") or item.get("title") or str(item),
                            "notes": item.get("description") or item.get("notes")
                        })
                    })
            else:
                # Unknown type, convert to activity
                items_normalized.append({
                    "type": "activity",
                    "data": {
                        "provider": "manual",
                        "title": str(item),
                        "notes": None
                    }
                })
        
        return {"label": label, "items": items_normalized, "notes": b.get("notes")}

    def coerce_day(d):
        if not isinstance(d, dict):
            return {"dateISO": "", "blocks": []}
        dateISO = d.get("dateISO") or d.get("date") or ""
        blocks = [coerce_block(b) for b in _as_list(d.get("blocks") or d.get("timeline") or d.get("blocksList"))]
        return {"dateISO": dateISO, "blocks": blocks, "dailyTips": d.get("dailyTips")}

    days_norm = [coerce_day(d) for d in days_src]

    pricing_src = obj.get("pricing") or {}
    if not isinstance(pricing_src, dict):
        pricing_src = {}
    
    # Helper to extract amount from nested objects or strings
    def extract_amount(val):
        if isinstance(val, dict):
            return val.get("total") or val.get("amount") or val.get("price")
        elif isinstance(val, str):
            # Handle "2349 TL" or "1,234.56 EUR" formats
            import re
            cleaned = re.sub(r'[^\d.]', '', val)
            try:
                return float(cleaned) if cleaned else None
            except (ValueError, TypeError):
                return None
        return val
    
    breakdown = pricing_src.get("breakdown")
    if not isinstance(breakdown, dict):
        breakdown = {
            "flights": extract_amount(pricing_src.get("flights") or pricing_src.get("flights_try")),
            "lodging": extract_amount(pricing_src.get("lodging") or pricing_src.get("lodging_try")),
            "activities": extract_amount(pricing_src.get("activities") or pricing_src.get("activities_try")),
            "transport": extract_amount(pricing_src.get("transport") or pricing_src.get("transport_try")),
            "feesAndTaxes": extract_amount(pricing_src.get("feesAndTaxes") or pricing_src.get("fees_try")),
        }
    else:
        # Already have breakdown, just normalize amounts
        breakdown = {
            "flights": extract_amount(breakdown.get("flights")),
            "lodging": extract_amount(breakdown.get("lodging")),
            "activities": extract_amount(breakdown.get("activities")),
            "transport": extract_amount(breakdown.get("transport")),
            "feesAndTaxes": extract_amount(breakdown.get("feesAndTaxes")),
        }
    # Normalize totalEstimated - handle if Claude returns nested object or string
    total_estimated = pricing_src.get("totalEstimated") or pricing_src.get("total")
    if isinstance(total_estimated, dict):
        # If it's a nested object like {"amount": 123, "currency": "USD"}, extract amount
        total_estimated = total_estimated.get("amount")
    elif isinstance(total_estimated, str):
        # Handle "50000 TRY" or "1,234.56" formats
        import re
        cleaned = re.sub(r'[^\d.]', '', total_estimated)
        try:
            total_estimated = float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            total_estimated = None
    
    # Normalize confidence - handle if Claude returns number (90) instead of string ("high")
    confidence_raw = pricing_src.get("confidence")
    if isinstance(confidence_raw, (int, float)):
        # Convert percentage to low/medium/high
        if confidence_raw >= 75:
            confidence = "high"
        elif confidence_raw >= 50:
            confidence = "medium"
        else:
            confidence = "low"
    elif isinstance(confidence_raw, str):
        # Already string, validate it
        confidence_lower = confidence_raw.lower()
        if confidence_lower in ["low", "medium", "high"]:
            confidence = confidence_lower
        else:
            confidence = "low"
    else:
        confidence = "low"
    
    pricing_norm = {
        "currency": pricing_src.get("currency") or obj.get("currency") or "USD",
        "breakdown": breakdown,
        "totalEstimated": total_estimated,
        "confidence": confidence,
        "notes": _as_list(pricing_src.get("notes")) or None,
    }

    metadata_src = obj.get("metadata") or {}
    if not isinstance(metadata_src, dict):
        metadata_src = {}
    sources = metadata_src.get("sources")
    if sources and isinstance(sources, list) and sources and isinstance(sources[0], str):
        sources = [{"provider": s} for s in sources]
    metadata_norm = {
        "generatedAtISO": metadata_src.get("generatedAtISO") or now_iso,
        "sources": sources or [],
        "toolDiagnostics": metadata_src.get("toolDiagnostics") or [],
        "warnings": metadata_src.get("warnings") or [],
        "revisionOf": metadata_src.get("revisionOf") or None,
        "planId": metadata_src.get("planId") or now_iso,
    }

    summary = obj.get("summary") or obj.get("overview") or ""

    normalized = {
        "query": {"raw": raw, "parsed": parsed},
        "summary": summary,
        "flights": flights_norm,
        "lodging": lodging_norm,
        "transport": transport_norm,
        "weather": weather_norm,
        "days": days_norm,
        "pricing": pricing_norm,
        "metadata": metadata_norm,
    }
    return normalized


def _parse_dt(date_str: str | None, time_str: str | None) -> str:
    try:
        if not date_str or not time_str:
            # If no date/time provided, return empty string to indicate missing data
            # Frontend should handle this case and not show today's date
            return ""
        # incoming format DD.MM.YYYY and HH:MM
        dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        return dt.isoformat() + "Z"
    except Exception as e:
        logger.warning(f"_parse_dt: Failed to parse date '{date_str}' time '{time_str}': {e}")
        return ""


def _map_mcp_flights(data: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        logger.info(f"_map_mcp_flights: Raw MCP data: {json.dumps(data, indent=2)}")
        # Handle MCP content array format
        if "content" in data and isinstance(data["content"], list):
            for item in data["content"]:
                if item.get("type") == "text":
                    import json as json_lib
                    try:
                        data = json_lib.loads(item.get("text", "{}"))
                        logger.info(f"_map_mcp_flights: Parsed content text: {json.dumps(data, indent=2)}")
                    except:
                        pass
        
        # Support both direct and wrapped under "data"
        root = data.get("data") if isinstance(data, dict) and "data" in data else data
        flights = root.get("flights") if isinstance(root, dict) else None
        logger.info(f"_map_mcp_flights: flights data: {flights}")
        if not flights:
            logger.warning("_map_mcp_flights: No flights data found!")
            return None
        dep_list = _as_list(flights.get("departure"))
        ret_list = _as_list(flights.get("return"))
        logger.info(f"_map_mcp_flights: departure count: {len(dep_list)}, return count: {len(ret_list)}")

        def map_option(opt: Dict[str, Any]) -> Dict[str, Any]:
            segs = []
            for s in _as_list(opt.get("segments")):
                dep = s.get("departure_datetime", {})
                arr = s.get("arrival_datetime", {})
                logger.info(f"_map_mcp_flights: Segment - dep: {dep}, arr: {arr}")
                depart_iso = _parse_dt(dep.get("date"), dep.get("time"))
                arrive_iso = _parse_dt(arr.get("date"), arr.get("time"))
                logger.info(f"_map_mcp_flights: Parsed ISO - departISO: {depart_iso}, arriveISO: {arrive_iso}")
                segs.append({
                    "fromIata": s.get("origin") or "",
                    "toIata": s.get("destination") or "",
                    "departISO": depart_iso,
                    "arriveISO": arrive_iso,
                    "airline": s.get("marketing_airline") or s.get("operating_airline") or "",
                    "flightNumber": s.get("flight_number") or "",
                    "durationMinutes": int((s.get("duration") or {}).get("total_minutes") or 0),
                    "cabin": s.get("cabin_class") or None,
                })
            price_info = opt.get("price_breakdown") or {}
            return {
                "provider": opt.get("booking_provider") or "mcp",
                "price": price_info.get("total"),
                "currency": price_info.get("currency") or root.get("currency"),
                "segments": segs or [{"fromIata":"","toIata":"","departISO":"","arriveISO":"","airline":"","flightNumber":"","durationMinutes":0,"cabin":None}],
                "bookingUrl": root.get("short_search_url") or root.get("search_url"),
            }

        mapped_out = map_option(dep_list[0]) if dep_list else None
        mapped_in = map_option(ret_list[0]) if ret_list else None
        alts = [map_option(o) for o in dep_list[1:4]] if len(dep_list) > 1 else None
        return {"outbound": mapped_out, "inbound": mapped_in, "alternatives": alts}
    except Exception:
        return None


def _map_mcp_hotels(data: Dict[str, Any], check_in_iso: str = "", check_out_iso: str = "") -> Dict[str, Any] | None:
    try:
        logger.info(f"_map_mcp_hotels: Raw MCP data: {json.dumps(data, indent=2)}")
        logger.info(f"_map_mcp_hotels: Check-in/out dates: {check_in_iso} → {check_out_iso}")
        # Handle MCP content array format
        if "content" in data and isinstance(data["content"], list):
            for item in data["content"]:
                if item.get("type") == "text":
                    import json as json_lib
                    try:
                        data = json_lib.loads(item.get("text", "{}"))
                        logger.info(f"_map_mcp_hotels: Parsed content text: {json.dumps(data, indent=2)}")
                    except:
                        pass
        
        options = data.get("options") or data.get("results") or data.get("hotels") or []
        logger.info(f"_map_mcp_hotels: Found {len(options)} hotel options")
        if not options:
            return None
        first = options[0]
        logger.info(f"_map_mcp_hotels: First hotel: {json.dumps(first, indent=2)}")
        
        # Normalize rating - handle "9.4/10" or string format
        rating = first.get("rating")
        logger.info(f"_map_mcp_hotels: Raw rating value: {rating} (type: {type(rating)})")
        if isinstance(rating, str):
            if "/" in rating:
                rating = float(rating.split("/")[0])
                logger.info(f"_map_mcp_hotels: Parsed rating from '/' format: {rating}")
            else:
                try:
                    rating = float(rating)
                    logger.info(f"_map_mcp_hotels: Parsed rating from string: {rating}")
                except (ValueError, TypeError):
                    rating = None
                    logger.warning("_map_mcp_hotels: Could not parse rating string")
        elif rating is not None:
            try:
                rating = float(rating)
                logger.info(f"_map_mcp_hotels: Converted rating to float: {rating}")
            except (ValueError, TypeError):
                rating = None
                logger.warning("_map_mcp_hotels: Could not convert rating to float")
        
        # Use dates from MCP response first, fallback to provided dates
        final_check_in = first.get("checkInISO") or check_in_iso or ""
        final_check_out = first.get("checkOutISO") or check_out_iso or ""
        logger.info(f"_map_mcp_hotels: Final dates - checkIn={final_check_in}, checkOut={final_check_out}")
        
        return {
            "selected": {
                "provider": first.get("provider") or "mcp",
                "name": first.get("name") or "",
                "address": first.get("address"),
                "checkInISO": final_check_in,
                "checkOutISO": final_check_out,
                "priceTotal": first.get("priceTotal") or first.get("price"),
                "currency": first.get("currency"),
                "rating": rating,
                "amenities": first.get("amenities"),
                "neighborhood": first.get("neighborhood"),
                "bookingUrl": first.get("bookingUrl"),
            },
            "alternatives": None,
        }
    except Exception:
        return None


def _map_mcp_weather(data: Dict[str, Any], start: str, end: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        days = data.get("days") or data.get("forecast") or []
        for d in days:
            out.append({
                "dateISO": d.get("dateISO") or d.get("date") or "",
                "highC": d.get("highC") or d.get("high") or None,
                "lowC": d.get("lowC") or d.get("low") or None,
                "precipitationChance": d.get("precipitationChance") or d.get("precipChance") or None,
                "source": d.get("source") or "MCP",
                "isForecast": True,
            })
    except Exception:
        pass
    return out


def _map_mcp_bus(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map MCP bus search response to transport intercity format."""
    out: List[Dict[str, Any]] = []
    try:
        # Handle MCP content array format
        if "content" in data and isinstance(data["content"], list):
            for item in data["content"]:
                if item.get("type") == "text":
                    import json as json_lib
                    try:
                        data = json_lib.loads(item.get("text", "{}"))
                    except:
                        pass
        
        # Extract bus options
        buses = data.get("buses") or data.get("options") or data.get("results") or []
        
        for bus in buses[:5]:  # Limit to top 5 options
            out.append({
                "mode": "bus",
                "operator": bus.get("operator") or bus.get("company") or "Unknown",
                "departureTime": bus.get("departure_time") or bus.get("departureTime"),
                "arrivalTime": bus.get("arrival_time") or bus.get("arrivalTime"),
                "duration": bus.get("duration") or bus.get("duration_minutes"),
                "price": bus.get("price"),
                "currency": bus.get("currency"),
                "bookingUrl": bus.get("booking_url") or bus.get("bookingUrl"),
            })
    except Exception as e:
        logger.error(f"_map_mcp_bus: Error mapping bus data: {e}")
    
    return out


async def _enrich_with_mcp(plan: Dict[str, Any], parsed_input=None, tool_call_context=None) -> Dict[str, Any]:
    """
    Enrich plan with real MCP data.
    Can use tool_call_context (from previous successful tool calls), parsed_input (from prompt_parser), or plan data.
    """
    # PRIORITY 1: Use tool call context (most reliable - from actual successful tool calls)
    if tool_call_context:
        flight_input = tool_call_context.get("flight_search", {})
        hotel_input = tool_call_context.get("hotel_search", {})
        
        if flight_input:
            logger.info(f"_enrich_with_mcp: Using flight_search tool context: {flight_input}")
            origin = flight_input.get("origin") or ""
            dest = flight_input.get("destination") or ""
            depart = flight_input.get("departure_date") or ""
            ret = flight_input.get("return_date") or ""
            adults = flight_input.get("adults") or 1
            
            # Convert date format if needed (DD.MM.YYYY -> YYYY-MM-DD)
            def convert_date(date_str: str) -> str:
                if not date_str:
                    return ""
                try:
                    if "." in date_str:  # DD.MM.YYYY format
                        from datetime import datetime
                        dt = datetime.strptime(date_str, "%d.%m.%Y")
                        return dt.strftime("%Y-%m-%d")
                    return date_str
                except:
                    return date_str
            
            depart = convert_date(depart)
            ret = convert_date(ret)
            
            logger.info(f"_enrich_with_mcp: ✅ Extracted from tool context - origin={origin}, dest={dest}, depart={depart}, ret={ret}, adults={adults}")
        elif hotel_input:
            # If only hotel search was done, extract dates from there
            logger.info(f"_enrich_with_mcp: Using hotel_search tool context: {hotel_input}")
            dest = hotel_input.get("destination_name") or ""
            depart = hotel_input.get("check_in_date") or ""
            ret = hotel_input.get("check_out_date") or ""
            adults = hotel_input.get("adults") or 1
            origin = ""  # Not available in hotel search
            
            # Convert date format if needed
            def convert_date(date_str: str) -> str:
                if not date_str:
                    return ""
                try:
                    if "." in date_str:  # DD.MM.YYYY format
                        from datetime import datetime
                        dt = datetime.strptime(date_str, "%d.%m.%Y")
                        return dt.strftime("%Y-%m-%d")
                    return date_str
                except:
                    return date_str
            
            depart = convert_date(depart)
            ret = convert_date(ret)
            
            logger.info(f"_enrich_with_mcp: ✅ Extracted from hotel context - dest={dest}, depart={depart}, ret={ret}, adults={adults}")
        else:
            logger.warning("_enrich_with_mcp: Tool context provided but no flight_search or hotel_search found")
            origin = dest = depart = ret = ""
            adults = 1
    # PRIORITY 2: Use parsed_input if available
    elif parsed_input:
        origin = parsed_input.departure.city
        dest = parsed_input.destination.city
        depart = parsed_input.dates.start_date or ""
        ret = parsed_input.dates.end_date or ""
        adults = parsed_input.travelers.count or 1
        logger.info(f"_enrich_with_mcp: Using parsed input - {origin} → {dest}, {depart} to {ret}, {adults} adults")
        
        # Update plan's parsed section with our better parsing
        # Calculate nights
        nights = parsed_input.dates.duration or 4
        if depart and ret:
            try:
                from datetime import datetime
                start_dt = datetime.strptime(depart, "%Y-%m-%d")
                end_dt = datetime.strptime(ret, "%Y-%m-%d")
                nights = (end_dt - start_dt).days
            except Exception:
                pass
        
        plan.setdefault("query", {})
        plan["query"]["parsed"] = {
            "originCity": origin,
            "originIata": origin,  # Will be resolved by MCP
            "destinationCity": dest,
            "destinationIata": dest,  # Will be resolved by MCP
            "startDateISO": depart,
            "endDateISO": ret,
            "nights": nights,
            "adults": adults,
            "children": len(parsed_input.travelers.children) if parsed_input.travelers.children else 0,
            "composition": parsed_input.travelers.composition,
            "budget_amount": parsed_input.budget.amount,
            "budget_currency": parsed_input.budget.currency,
            "travel_style": parsed_input.travel_style.type,
            "preferences": parsed_input.preferences,
        }
    else:
        # Fallback to plan's parsed data
        parsed = plan.get("query", {}).get("parsed", {})
        
        # City name translation map (Turkish -> English)
        city_translations = {
            "istanbul": "Istanbul",
            "i̇stanbul": "Istanbul",
            "ankara": "Ankara",
            "izmir": "Izmir",
            "i̇zmir": "Izmir",
            "antalya": "Antalya",
            "roma": "Rome",
            "milano": "Milan",
            "venedik": "Venice",
            "floransa": "Florence",
            "napoli": "Naples",
            "paris": "Paris",
            "londra": "London",
            "barselona": "Barcelona",
            "madrid": "Madrid",
            "berlin": "Berlin",
            "münih": "Munich",
            "viyana": "Vienna",
            "prag": "Prague",
            "amsterdam": "Amsterdam",
            "brüksel": "Brussels",
            "cenevre": "Geneva",
            "zürih": "Zurich",
        }
        
        def normalize_city(city_name: str) -> str:
            if not city_name:
                return ""
            # Try exact match first
            normalized = city_name.strip()
            lower_name = normalized.lower()
            if lower_name in city_translations:
                return city_translations[lower_name]
            # Return as-is if no translation found
            return normalized
        
        origin_raw = parsed.get("originIata") or parsed.get("originCity") or ""
        dest_raw = parsed.get("destinationIata") or parsed.get("destinationCity") or ""
        origin = normalize_city(origin_raw)
        dest = normalize_city(dest_raw)
        depart = parsed.get("startDateISO") or ""
        ret = parsed.get("endDateISO") or ""
        adults = parsed.get("adults") or 1
        logger.info(f"_enrich_with_mcp: Using plan data - origin={origin} (from: {origin_raw}), dest={dest} (from: {dest_raw}), depart={depart}, ret={ret}")

    diagnostics: List[Dict[str, Any]] = []

    # 🚀 PARALLEL MCP CALLS - All at once!
    logger.info("_enrich_with_mcp: 🚀 Starting PARALLEL MCP calls (flights + hotels + weather)...")
    import asyncio
    
    async def fetch_flights():
        try:
            logger.info("_enrich_with_mcp: → Calling flight_search...")
            flights_data, flights_diag = await adapters.flights_search({
                "origin": origin,
                "destination": dest,
                "departDateISO": depart,
                "returnDateISO": ret,
                "adults": adults,
            })
            logger.info(f"_enrich_with_mcp: ✓ flight_search completed ({len(str(flights_data))} bytes)")
            mapped = _map_mcp_flights(flights_data) or plan.get("flights")
            return mapped, flights_diag
        except Exception as e:
            logger.error(f"_enrich_with_mcp: ✗ flight_search error: {e}")
            return None, {"tool":"flights.search","ok":False,"error":str(e)}
    
    async def fetch_hotels():
        try:
            logger.info("_enrich_with_mcp: → Calling hotel_search...")
            hotels_data, hotels_diag = await adapters.hotels_search({
                "city": dest,
                "checkInISO": depart,
                "checkOutISO": ret,
                "rooms": 1,
                "occupants": adults,
            })
            logger.info(f"_enrich_with_mcp: ✓ hotel_search completed ({len(str(hotels_data))} bytes)")
            mapped_h = _map_mcp_hotels(hotels_data, depart, ret) or plan.get("lodging")
            return mapped_h, hotels_diag
        except Exception as e:
            logger.error(f"_enrich_with_mcp: ✗ hotel_search error: {e}")
            return None, {"tool":"hotels.search","ok":False,"error":str(e)}
    
    async def fetch_weather():
        try:
            logger.info("_enrich_with_mcp: → Calling weather_forecast...")
            weather_data, weather_diag = await adapters.weather_forecast({
                "city": dest,
                "startDateISO": depart,
                "endDateISO": ret,
            })
            logger.info(f"_enrich_with_mcp: ✓ weather_forecast completed")
            mapped_w = _map_mcp_weather(weather_data, depart, ret)
            return mapped_w, weather_diag
        except Exception as e:
            logger.error(f"_enrich_with_mcp: ✗ weather_forecast error: {e}")
            return None, {"tool":"weather.forecast","ok":False,"error":str(e)}
    
    # Execute all in parallel
    results = await asyncio.gather(
        fetch_flights(),
        fetch_hotels(),
        fetch_weather(),
        return_exceptions=True
    )
    
    logger.info("_enrich_with_mcp: ✅ All parallel calls completed!")
    
    # Process results
    if not isinstance(results[0], Exception):
        flights_mapped, flights_diag = results[0]
        diagnostics.append(flights_diag)
        if flights_mapped:
            logger.info(f"_enrich_with_mcp: Mapped flights: {flights_mapped.get('outbound', {}).get('provider', 'N/A')}")
            plan["flights"] = flights_mapped
    
    if not isinstance(results[1], Exception):
        hotels_mapped, hotels_diag = results[1]
        diagnostics.append(hotels_diag)
        if hotels_mapped:
            logger.info(f"_enrich_with_mcp: Mapped hotel: {hotels_mapped.get('selected', {}).get('name', 'N/A')}")
            plan["lodging"] = hotels_mapped
    
    if not isinstance(results[2], Exception):
        weather_mapped, weather_diag = results[2]
        diagnostics.append(weather_diag)
        if weather_mapped:
            plan["weather"] = weather_mapped

    plan.setdefault("metadata", {})
    md = plan["metadata"]
    md["toolDiagnostics"] = _as_list(md.get("toolDiagnostics")) + diagnostics
    return plan


async def generate(req: PlanRequest, session_id: str = None) -> TripPlan:
    """
    Uses Anthropic with tool use to generate a TripPlan, calling MCP tools as needed.
    
    WORKFLOW:
    1. Parse natural language prompt into structured data
    2. Use parsed data to make targeted MCP calls (flights, hotels, weather)
    3. Generate comprehensive plan with Claude using real MCP data
    
    Args:
        req: Plan request with prompt, language, currency
        session_id: Optional session ID for real-time progress updates via SSE
    """
    
    async def send_progress(stage: str, message: str, data: dict = None):
        """Send progress update if session_id provided"""
        if session_id:
            # Import here to avoid circular dependency
            from app.routers import plan as plan_router
            if session_id in plan_router.progress_queues:
                event = {"stage": stage, "message": message}
                if data:
                    event["data"] = data
                await plan_router.progress_queues[session_id].put(event)
    
    # Check cache first
    from app.services.cache_service import get_cache
    cache = get_cache()
    cache_key = cache._generate_key("plan", {
        "prompt": req.prompt,
        "language": req.language or "en",
        "currency": req.currency or "USD"
    })
    
    cached_plan = cache.get(cache_key)
    if cached_plan:
        logger.info(f"generate: Using cached plan for prompt: {req.prompt[:50]}...")
        await send_progress("cache", "Önbellekten plan yükleniyor...")
        return TripPlan.model_validate(cached_plan)
    
    # Step 1: Parse the prompt for better understanding
    logger.info(f"generate: Parsing prompt: {req.prompt[:100]}...")
    try:
        from app.services.prompt_parser import parse_prompt
        parsed_input = await parse_prompt(req.prompt, locale="tr-TR")
        logger.info(f"generate: ✅ PARSED DATES - start: {parsed_input.dates.start_date}, end: {parsed_input.dates.end_date}, duration: {parsed_input.dates.duration}")
        logger.info(f"generate: ✅ PARSED LOCATIONS - from: {parsed_input.departure.city}, to: {parsed_input.destination.city}, travelers: {parsed_input.travelers.count}")
    except Exception as e:
        logger.warning(f"generate: Prompt parsing failed: {e}. Continuing with basic flow...")
        parsed_input = None
    
    system = (
        "You are an Expert Travel Planner AI with deep knowledge of global destinations, travel logistics, and cultural insights. "
        "Your goal is to create COMPREHENSIVE, REALISTIC, and DELIGHTFUL travel plans that consider ALL aspects of the journey.\n\n"
        
        "**CRITICAL: You MUST ALWAYS return a complete JSON object matching the TripPlan schema, even if information is incomplete. "
        "NEVER ask questions or return plain text. If dates are missing, assume reasonable defaults (e.g., 7 days from today). "
        "If tool calls fail, use your knowledge to provide estimated/example data.**\n\n"
        
        "## PLANNING PHILOSOPHY:\n"
        "1. **Traveler-Centric**: Understand traveler preferences, budget, energy levels, and travel style\n"
        "2. **Holistic Thinking**: Consider flights, accommodation, weather, local transport, activities, food, culture, safety, and practicalities\n"
        "3. **Time-Aware**: Account for jet lag, flight times, check-in/out times, realistic travel durations, and buffer times\n"
        "4. **Budget-Conscious**: Balance cost and value; offer alternatives when possible\n"
        "5. **Weather-Responsive**: Adapt activities and recommendations based on forecasted weather\n"
        "6. **Culturally Informed**: Include local customs, etiquette, best times to visit attractions, local food recommendations\n\n"
        
        "## TOOL USAGE STRATEGY (MANDATORY):\n"
        "**YOU MUST USE THE AVAILABLE TOOLS** to get real flight, hotel, and weather data. Do NOT make up prices or availability.\n\n"
        "1. **ALWAYS call flight_search** with origin, destination, departure_date, return_date, adults\n"
        "   - **CRITICAL**: Use ENGLISH city names for origin/destination (e.g., 'Istanbul' NOT 'İstanbul', 'Rome' NOT 'Roma', 'Munich' NOT 'Münih')\n"
        "   - Use standard IATA codes when known (e.g., IST, FCO, MUC)\n"
        "2. **ALWAYS call hotel_search** with destination_name, check_in_date, check_out_date, adults\n"
        "   - **CRITICAL**: Use ENGLISH city names (e.g., 'Rome' NOT 'Roma', 'Venice' NOT 'Venedik')\n"
        "3. **ALWAYS call flight_weather_forecast** (or appropriate weather tool) with location, start_date, end_date\n"
        "   - **CRITICAL**: Use ENGLISH city names\n"
        "4. **Use the REAL DATA from tool results** to create your plan\n"
        "5. If a tool fails, note it in warnings but continue with estimated data\n\n"
        "**IMPORTANT: You have access to real-time MCP tools. USE THEM FIRST before generating the final JSON plan.**\n\n"
        
        "## DAY-BY-DAY PLANNING RULES:\n"
        "- **Day 1**: Arrival day - factor in actual flight landing time, immigration/baggage (add 1-2h buffer), hotel check-in, light activities if energy permits\n"
        "- **Middle Days**: Full activity days - balance morning/afternoon/evening activities, include meal breaks, realistic travel times between locations\n"
        "- **Last Day**: Departure day - hotel checkout (usually 11am-12pm), travel to airport (2-3h before international flights), consider luggage storage if late flight\n"
        "- **Activity Pacing**: Mix high-energy and low-energy activities; don't over-schedule; include rest/free time\n"
        "- **Local Transport**: Suggest metro passes, taxi estimates, walking distances, and travel times between activities\n\n"
        
        "## WEATHER ADAPTATION:\n"
        "- Rainy days → indoor museums, cafes, shopping, covered markets\n"
        "- Hot days → early morning activities, midday break, evening strolls\n"
        "- Cold days → shorter outdoor time, warm cafes, indoor attractions\n"
        "- Always include appropriate packing suggestions\n\n"
        
        "## BUDGET OPTIMIZATION:\n"
        "- Prioritize direct flights if budget allows; otherwise suggest best-value connections\n"
        "- Balance hotel location vs. price (central = more expensive but saves transport time/cost)\n"
        "- Include free/low-cost activities (parks, walking tours, local markets)\n"
        "- Suggest local food spots vs. tourist restaurants\n\n"
        
        "## OUTPUT FORMAT:\n"
        "After using tools and gathering data, return ONLY a strict JSON object matching the TripPlan schema.\n"
        "Required top-level keys: query, summary, flights, lodging, transport, weather, days, pricing, metadata.\n"
        "- **summary**: 2-3 sentence overview highlighting trip highlights and key logistics\n"
        "- **days**: MUST be an array with at least one day object. Each day MUST have 'dateISO' and 'blocks' array\n"
        "  Example: `\"days\": [{\"dateISO\": \"2025-12-21T00:00:00Z\", \"blocks\": [{\"label\": \"morning\", \"items\": [\"Breakfast at hotel\", \"Visit Colosseum\"]}]}]`\n"
        "  NOTE: Items can be simple strings OR objects with {text, description, time, location, price, booking}\n"
        "- **pricing**: Breakdown with confidence level ('low', 'medium', or 'high') and notes about variable costs\n"
        "- **metadata.warnings**: Include any important notes (visa requirements, peak season, health advisories, etc.)\n\n"
        
        "**CRITICAL DATA FORMAT RULES:**\n"
        "- ALL prices MUST be pure numbers (not strings like '26922 TRY')\n"
        "- Use: `\"price\": 26922` NOT `\"price\": \"26922 TRY\"`\n"
        "- For pricing.breakdown: `{\"flights\": 26922, \"transport\": 600}` (numbers only!)\n"
        "- For pricing.confidence: Use string 'low', 'medium', or 'high' (NOT numbers like 90)\n"
        "- For ratings: `\"rating\": 9.4` NOT `\"rating\": \"9.4/10\"`\n"
        "- For days[].blocks[].items: Can be strings OR objects, both work\n"
        "- Currency symbols go in separate 'currency' field, NOT in the number\n\n"
        
        "Be thorough, realistic, and delightful. Create a plan the traveler will be excited to follow!"
    )
    
    # Add parsed information to user message if available
    parsed_info = ""
    if parsed_input:
        # Convert dates to DD.MM.YYYY format for MCP tools
        from datetime import datetime
        try:
            start_dt = datetime.strptime(parsed_input.dates.start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(parsed_input.dates.end_date, "%Y-%m-%d")
            departure_date_ddmmyyyy = start_dt.strftime("%d.%m.%Y")
            return_date_ddmmyyyy = end_dt.strftime("%d.%m.%Y")
        except:
            departure_date_ddmmyyyy = parsed_input.dates.start_date
            return_date_ddmmyyyy = parsed_input.dates.end_date
            
        parsed_info = (
            f"\n**PRE-PARSED TRAVEL INFORMATION (USE THESE EXACT VALUES):**\n"
            f"- Origin: {parsed_input.departure.city}\n"
            f"- Destination: {parsed_input.destination.city}\n"
            f"- Start Date: {parsed_input.dates.start_date} (for flight_search use: {departure_date_ddmmyyyy})\n"
            f"- End Date: {parsed_input.dates.end_date} (for flight_search use: {return_date_ddmmyyyy})\n"
            f"- Duration: {parsed_input.dates.duration} days\n"
            f"- Travelers: {parsed_input.travelers.count} ({parsed_input.travelers.composition})\n\n"
            f"**CRITICAL: When calling flight_search, use:**\n"
            f"```\n"
            f"flight_search({{\n"
            f"  origin: '{parsed_input.departure.city}',\n"
            f"  destination: '{parsed_input.destination.city}',\n"
            f"  departure_date: '{departure_date_ddmmyyyy}',\n"
            f"  return_date: '{return_date_ddmmyyyy}',\n"
            f"  adults: {parsed_input.travelers.count}\n"
            f"}})\n"
            f"```\n\n"
        )
    
    user_msg = (
        f"Create a comprehensive travel plan for: {req.prompt}\n\n"
        f"{parsed_info}"
        f"Language for responses: {req.language or 'en'}\n"
        f"Currency for pricing: {req.currency or 'TRY'}\n\n"
        "**WORKFLOW EXAMPLE:**\n"
        "For a request like 'Istanbul to Paris, Nov 15-20, 2 adults', you should:\n\n"
        "Step 1: Parse and identify:\n"
        "- origin: Istanbul (IST)\n"
        "- destination: Paris (CDG/ORY)\n"
        "- departure_date: 15.11.2025\n"
        "- return_date: 20.11.2025\n"
        "- adults: 2\n\n"
        "Step 2: **USE TOOLS** (MANDATORY):\n"
        "```\n"
        "flight_search({\n"
        "  origin: 'Istanbul',\n"
        "  destination: 'Paris',\n"
        "  departure_date: '15.11.2025',\n"
        "  return_date: '20.11.2025',\n"
        "  adults: 2\n"
        "})\n\n"
        "hotel_search({\n"
        "  destination_name: 'Paris',\n"
        "  check_in_date: '15.11.2025',\n"
        "  check_out_date: '20.11.2025',\n"
        "  adults: 2,\n"
        "  rooms: 1\n"
        "})\n\n"
        "flight_weather_forecast({\n"
        "  location: 'Paris',\n"
        "  start_date: '2025-11-15',\n"
        "  end_date: '2025-11-20'\n"
        "})\n"
        "```\n\n"
        "Step 3: Wait for tool results, then use the REAL data in your final JSON plan.\n\n"
        "**NOW PROCESS THE ACTUAL REQUEST ABOVE. CALL THE TOOLS FIRST, THEN RETURN THE COMPLETE TRIPPLAN JSON.**"
    )
    
    messages = [{"role": "user", "content": user_msg}]
    tools = await get_mcp_tools_schema()
    
    # Store tool call inputs for later use (if we need to re-enrich with MCP)
    tool_call_context = {}
    
    # Tool use loop
    max_turns = 10
    for turn in range(max_turns):
        logger.info(f"generate: Turn {turn + 1}/{max_turns}")
        try:
            response = await anthropic_client.chat_with_tools(messages, tools, system)
            logger.info(f"generate: Received response with stop_reason={response.get('stop_reason')}")
        except Exception as e:
            logger.error(f"generate: Error calling Anthropic API: {e}")
            raise
        
        # Check stop reason
        stop_reason = response.get("stop_reason")
        content_blocks = response.get("content", [])
        
        # If end_turn or no tool_use, we're done
        if stop_reason == "end_turn":
            logger.info("generate: Received end_turn, extracting final response")
            # Extract text
            for block in content_blocks:
                if block.get("type") == "text":
                    raw = block.get("text", "")
                    logger.info(f"generate: Received text block (length: {len(raw)})")
                    logger.debug(f"generate: Text preview: {raw[:500]}...")
                    try:
                        obj = _json_only_guard(raw)
                        obj = normalize_to_contract(obj)
                        
                        # Check if tools were actually used
                        tool_diags = obj.get("metadata", {}).get("toolDiagnostics", [])
                        if not tool_diags or len(tool_diags) == 0:
                            logger.warning("generate: Claude did not use tools, applying manual MCP enrichment")
                            obj = await _enrich_with_mcp(obj, parsed_input, tool_call_context)
                        
                        plan = TripPlan.model_validate(obj)
                        
                        # Cache the result
                        from datetime import timedelta
                        cache.set(cache_key, plan.model_dump(), ttl=timedelta(hours=2))
                        logger.info(f"generate: Cached plan for {req.prompt[:50]}...")
                        
                        return plan
                    except Exception as e:
                        logger.error(f"generate: Error parsing/validating response: {e}")
                        logger.error(f"generate: Raw text: {raw[:1000]}")
                        raise
            # No text found, break
            logger.warning("generate: No text block found in end_turn response")
            break
        
        # Handle tool_use
        if stop_reason == "tool_use":
            logger.info("generate: Received tool_use, executing tools")
            # Append assistant message
            messages.append({"role": "assistant", "content": content_blocks})
            
            # Execute all tool calls IN PARALLEL
            tool_results = []
            tool_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
            
            # Send progress for tool execution
            tool_names = [b.get("name") for b in tool_blocks]
            if "flight_search" in tool_names:
                await send_progress("flights", "Uçuş seçenekleri aranıyor...")
            if "hotel_search" in tool_names:
                await send_progress("hotels", "Otel seçenekleri aranıyor...")
            if "flight_weather_forecast" in tool_names or "weather_forecast" in tool_names:
                await send_progress("weather", "Hava durumu bilgisi alınıyor...")
            
            # Execute tools in parallel
            async def execute_tool(block):
                tool_name = block.get("name")
                tool_input = block.get("input", {})
                tool_use_id = block.get("id")
                
                logger.info(f"generate: Executing tool '{tool_name}' with input: {tool_input}")
                
                # Store tool input for potential reuse
                tool_call_context[tool_name] = tool_input
                
                try:
                    tool_data, tool_diag = await _execute_mcp_tool(tool_name, tool_input)
                    logger.info(f"generate: Tool '{tool_name}' completed: {tool_diag}")
                    
                    # Send progress update
                    if tool_name == "flight_search":
                        await send_progress("flights", "✓ Uçuş seçenekleri bulundu", {"count": len(tool_data) if isinstance(tool_data, list) else 1})
                    elif tool_name == "hotel_search":
                        await send_progress("hotels", "✓ Otel seçenekleri bulundu", {"count": len(tool_data) if isinstance(tool_data, list) else 1})
                    elif "weather" in tool_name:
                        await send_progress("weather", "✓ Hava durumu bilgisi alındı")
                    
                    return {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(tool_data) if not isinstance(tool_data, str) else tool_data
                    }
                except Exception as e:
                    logger.error(f"generate: Tool '{tool_name}' failed: {e}")
                    tool_data = {"error": str(e)}
                    tool_diag = {"tool": tool_name, "ok": False, "error": str(e)}
                    return {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(tool_data)
                    }
            
            # Execute all tools in parallel
            tool_results = await asyncio.gather(*[execute_tool(block) for block in tool_blocks])
            
            # Send final itinerary progress after tools
            await send_progress("itinerary", "Gezi programı oluşturuluyor...")
            
            # Append tool results
            messages.append({"role": "user", "content": tool_results})
            continue
        
        # Unknown stop reason
        break
    
    # Fallback if loop exhausted without generating a valid plan
    logger.warning("generate: Loop exhausted without valid plan, creating fallback")
    obj = {"query": {"raw": req.prompt, "parsed": {}}, "summary": "Unable to generate plan", "flights": {}, "lodging": {}, "transport": {}, "weather": [], "days": [], "pricing": {}, "metadata": {}}
    obj = normalize_to_contract(obj)
    
    # Last resort: Try manual MCP enrichment
    logger.info("generate: Attempting manual MCP enrichment as fallback")
    try:
        obj = await _enrich_with_mcp(obj, parsed_input)
    except Exception as e:
        logger.error(f"generate: Manual MCP enrichment failed: {e}")
    
    return TripPlan.model_validate(obj)


async def _execute_mcp_tool(tool_name: str, tool_input: Dict[str, Any]) -> tuple[Any, Dict[str, Any]]:
    """
    Execute an MCP tool by name dynamically and return its result + diagnostic.
    This function now supports any tool available in the MCP server.
    """
    import time
    t0 = time.time()
    
    try:
        # Call the tool directly through MCP adapter
        from app.tools.adapters import _mcp_call
        data = await _mcp_call(tool_name, tool_input)
        diag = {
            "tool": tool_name, 
            "ok": True, 
            "ms": int((time.time() - t0) * 1000)
        }
        return data, diag
    except Exception as e:
        logger.error(f"Error executing MCP tool {tool_name}: {e}")
        diag = {
            "tool": tool_name, 
            "ok": False, 
            "ms": int((time.time() - t0) * 1000),
            "error": str(e)
        }
        return {}, diag


async def revise(plan_json: Dict[str, Any], req: ReviseRequest) -> TripPlan:
    """
    Revises an existing plan using Anthropic with tool calling.
    """
    system = (
        "You are an Expert Travel Planner AI revising an existing travel plan. "
        "Your goal is to apply the requested changes while maintaining plan coherence and quality.\n\n"
        
        "## REVISION PRINCIPLES:\n"
        "1. **Minimal Impact**: Make only the changes requested; preserve other aspects that work well\n"
        "2. **Cascade Effects**: Consider downstream impacts (e.g., cheaper hotel in different area → adjust activities)\n"
        "3. **Use Tools When Needed**: If revision requires new data (different hotel, new flights, etc.), use available tools\n"
        "4. **Maintain Quality**: Ensure revised plan still follows all planning rules (realistic timing, buffers, weather-awareness)\n"
        "5. **Preserve Metadata**: Keep original planId in metadata.revisionOf field\n\n"
        
        "## COMMON REVISION TYPES:\n"
        "- **Budget changes**: Find cheaper/better value options while maintaining quality\n"
        "- **Activity changes**: Add/remove/replace activities while keeping realistic schedule\n"
        "- **Date changes**: Re-search flights, hotels, weather for new dates\n"
        "- **Hotel changes**: Different location/price point → may affect activity sequence\n"
        "- **Preference changes**: Dietary, pace, interests → adjust recommendations\n\n"
        
        "## TOOL USAGE FOR REVISIONS:\n"
        "- Use flight_search if dates or destinations change\n"
        "- Use hotel_search if accommodation needs to change\n"
        "- Use flight_weather_forecast if dates change or weather impacts activities\n"
        "- Use bus_search if intercity routes change\n\n"
        
        "After making changes, return the FULL updated TripPlan JSON with all required fields."
    )
    
    user_msg = (
        f"Revise the following travel plan based on this instruction:\n\n"
        f"**Revision Request**: {req.instruction}\n\n"
        f"**Current Plan**:\n{json.dumps(plan_json, ensure_ascii=False, indent=2)}\n\n"
        "Apply the requested changes using tools if needed, then return the complete updated TripPlan JSON."
    )
    
    messages = [{"role": "user", "content": user_msg}]
    tools = await get_mcp_tools_schema()
    
    # Tool use loop
    max_turns = 10
    for turn in range(max_turns):
        response = await anthropic_client.chat_with_tools(messages, tools, system)
        
        stop_reason = response.get("stop_reason")
        content_blocks = response.get("content", [])
        
        if stop_reason == "end_turn":
            for block in content_blocks:
                if block.get("type") == "text":
                    raw = block.get("text", "")
                    obj = _json_only_guard(raw)
                    obj = normalize_to_contract(obj)
                    return TripPlan.model_validate(obj)
            break
        
        if stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": content_blocks})
            
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    tool_input = block.get("input", {})
                    tool_use_id = block.get("id")
                    
                    tool_data, tool_diag = await _execute_mcp_tool(tool_name, tool_input)
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(tool_data, ensure_ascii=False),
                    })
            
            messages.append({"role": "user", "content": tool_results})
            continue
        
        break
    
    # Fallback
    obj = plan_json
    obj = normalize_to_contract(obj)
    return TripPlan.model_validate(obj)
