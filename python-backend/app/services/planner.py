import json
from datetime import datetime
from typing import Dict, Any, List
from app.models.plan import TripPlan, PlanRequest, ReviseRequest
from app.core.logging import logger
from app.services import anthropic_client
from app.tools import adapters
from app.tools.adapters import get_mcp_tools_schema

SYSTEM = (
    "You are Trip Planner AI. Always return ONLY the strict JSON object specified. "
    "No markdown. Keys must match the contract."
)

CONTRACT_HINT = (
    "JSON keys required: query, summary, flights, lodging, transport, weather, days, pricing, metadata."
)


def _json_only_guard(text: str) -> Dict[str, Any]:
    try:
        if not text or not text.strip():
            logger.error("_json_only_guard: Empty text received")
            raise ValueError("Empty text received")
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"_json_only_guard: Initial JSON parse failed, trying to extract JSON block. Error: {e}")
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1:
            extracted = text[s : e + 1]
            logger.info(f"_json_only_guard: Extracted JSON block (length: {len(extracted)})")
            return json.loads(extracted)
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
    parsed.setdefault("originCity", parsed.get("from") or obj.get("from") or "")
    parsed.setdefault("destinationCity", parsed.get("to") or obj.get("to") or "")
    parsed.setdefault("startDateISO", parsed.get("startDate") or obj.get("startDate") or obj.get("date") or "")
    parsed.setdefault("endDateISO", parsed.get("endDate") or obj.get("endDate") or "")
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
        return {"provider": provider, "currency": val.get("currency"), "price": val.get("price"), "segments": segs, "bookingUrl": val.get("bookingUrl")}

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
        return {
            "provider": val.get("provider") or "unknown",
            "name": val.get("name") or val.get("hotel") or "",
            "address": val.get("address"),
            "checkInISO": val.get("checkInISO") or val.get("checkIn") or "",
            "checkOutISO": val.get("checkOutISO") or val.get("checkOut") or "",
            "priceTotal": val.get("priceTotal") or val.get("price"),
            "currency": val.get("currency"),
            "rating": val.get("rating"),
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
        label = b.get("label") or b.get("time") or "morning"
        items = _as_list(b.get("items"))
        return {"label": label, "items": items, "notes": b.get("notes")}

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
    breakdown = pricing_src.get("breakdown")
    if not isinstance(breakdown, dict):
        breakdown = {
            "flights": pricing_src.get("flights") or pricing_src.get("flights_try"),
            "lodging": pricing_src.get("lodging") or pricing_src.get("lodging_try"),
            "activities": pricing_src.get("activities") or pricing_src.get("activities_try"),
            "transport": pricing_src.get("transport") or pricing_src.get("transport_try"),
            "feesAndTaxes": pricing_src.get("feesAndTaxes") or pricing_src.get("fees_try"),
        }
    pricing_norm = {
        "currency": pricing_src.get("currency") or obj.get("currency") or "USD",
        "breakdown": breakdown,
        "totalEstimated": pricing_src.get("totalEstimated") or pricing_src.get("total") or None,
        "confidence": pricing_src.get("confidence") or "low",
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
            return ""
        # incoming format DD.MM.YYYY and HH:MM
        dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        return dt.isoformat() + "Z"
    except Exception:
        return ""


def _map_mcp_flights(data: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        # Support both direct and wrapped under "data"
        root = data.get("data") if isinstance(data, dict) and "data" in data else data
        flights = root.get("flights") if isinstance(root, dict) else None
        if not flights:
            return None
        dep_list = _as_list(flights.get("departure"))
        ret_list = _as_list(flights.get("return"))

        def map_option(opt: Dict[str, Any]) -> Dict[str, Any]:
            segs = []
            for s in _as_list(opt.get("segments")):
                dep = s.get("departure_datetime", {})
                arr = s.get("arrival_datetime", {})
                segs.append({
                    "fromIata": s.get("origin") or "",
                    "toIata": s.get("destination") or "",
                    "departISO": _parse_dt(dep.get("date"), dep.get("time")),
                    "arriveISO": _parse_dt(arr.get("date"), arr.get("time")),
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


def _map_mcp_hotels(data: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        options = data.get("options") or data.get("results") or []
        if not options:
            return None
        first = options[0]
        return {
            "selected": {
                "provider": first.get("provider") or "mcp",
                "name": first.get("name") or "",
                "address": first.get("address"),
                "checkInISO": first.get("checkInISO") or "",
                "checkOutISO": first.get("checkOutISO") or "",
                "priceTotal": first.get("priceTotal") or first.get("price"),
                "currency": first.get("currency"),
                "rating": first.get("rating"),
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


async def _enrich_with_mcp(plan: Dict[str, Any]) -> Dict[str, Any]:
    parsed = plan.get("query", {}).get("parsed", {})
    origin = parsed.get("originIata") or parsed.get("originCity") or ""
    dest = parsed.get("destinationIata") or parsed.get("destinationCity") or ""
    depart = parsed.get("startDateISO") or ""
    ret = parsed.get("endDateISO") or ""

    diagnostics: List[Dict[str, Any]] = []

    # Flights
    try:
        flights_data, flights_diag = await adapters.flights_search({
            "origin": origin,
            "destination": dest,
            "departDateISO": depart,
            "returnDateISO": ret,
            "adults": parsed.get("adults") or 1,
        })
        diagnostics.append(flights_diag)
        mapped = _map_mcp_flights(flights_data) or plan.get("flights")
        if mapped:
            plan["flights"] = mapped
    except Exception as e:
        diagnostics.append({"tool":"flights.search","ok":False,"error":str(e)})

    # Hotels (left as-is; requires real shape)
    try:
        hotels_data, hotels_diag = await adapters.hotels_search({
            "city": dest or parsed.get("destinationCity") or "",
            "checkInISO": depart,
            "checkOutISO": ret,
            "rooms": 1,
            "occupants": parsed.get("adults") or 1,
        })
        diagnostics.append(hotels_diag)
        mapped_h = _map_mcp_hotels(hotels_data) or plan.get("lodging")
        if mapped_h:
            plan["lodging"] = mapped_h
    except Exception as e:
        diagnostics.append({"tool":"hotels.search","ok":False,"error":str(e)})

    # Weather
    try:
        weather_data, weather_diag = await adapters.weather_forecast({
            "city": dest or parsed.get("destinationCity") or "",
            "startDateISO": depart,
            "endDateISO": ret,
        })
        diagnostics.append(weather_diag)
        mapped_w = _map_mcp_weather(weather_data, depart, ret)
        if mapped_w:
            plan["weather"] = mapped_w
    except Exception as e:
        diagnostics.append({"tool":"weather.forecast","ok":False,"error":str(e)})

    plan.setdefault("metadata", {})
    md = plan["metadata"]
    md["toolDiagnostics"] = _as_list(md.get("toolDiagnostics")) + diagnostics
    return plan


async def generate(req: PlanRequest) -> TripPlan:
    """
    Uses Anthropic with tool use to generate a TripPlan, calling MCP tools as needed.
    """
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
        
        "## TOOL USAGE STRATEGY:\n"
        "1. **Always search flights first** to understand actual arrival/departure times\n"
        "2. **Search hotels** based on flight times and traveler preferences (location, amenities, budget)\n"
        "3. **Check weather forecast** to inform activity planning and packing recommendations\n"
        "4. **Search intercity transport** if the itinerary involves multiple cities\n"
        "5. Use tool results to create a realistic, optimized itinerary\n\n"
        
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
        "- **days**: Detailed day-by-day itinerary with blocks (morning/afternoon/evening) and realistic activities\n"
        "- **pricing**: Breakdown with confidence level and notes about variable costs\n"
        "- **metadata.warnings**: Include any important notes (visa requirements, peak season, health advisories, etc.)\n\n"
        
        "Be thorough, realistic, and delightful. Create a plan the traveler will be excited to follow!"
    )
    
    user_msg = (
        f"Create a comprehensive travel plan for: {req.prompt}\n\n"
        f"Language for responses: {req.language or 'en'}\n"
        f"Currency for pricing: {req.currency or 'TRY'}\n\n"
        "**IMPORTANT: If dates are not specified in the prompt, assume a trip starting 7-14 days from today. "
        "If duration is not specified, assume 3-5 days. "
        "Make reasonable assumptions to create a complete plan.**\n\n"
        "Steps:\n"
        "1. Parse the prompt and extract/assume: origin, destination, dates, duration, travelers\n"
        "2. Try using flight_search, hotel_search, and weather tools (but if they fail, continue with estimated data)\n"
        "3. Create a detailed day-by-day itinerary considering all factors\n"
        "4. Return a COMPLETE TripPlan JSON object with ALL required fields filled\n\n"
        "**You MUST return JSON, not conversational text. Start your response with { and end with }**"
    )
    
    messages = [{"role": "user", "content": user_msg}]
    tools = await get_mcp_tools_schema()
    
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
                        return TripPlan.model_validate(obj)
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
            
            # Execute all tool calls
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    tool_input = block.get("input", {})
                    tool_use_id = block.get("id")
                    
                    logger.info(f"generate: Executing tool '{tool_name}' with input: {tool_input}")
                    
                    # Execute tool
                    try:
                        tool_data, tool_diag = await _execute_mcp_tool(tool_name, tool_input)
                        logger.info(f"generate: Tool '{tool_name}' completed: {tool_diag}")
                    except Exception as e:
                        logger.error(f"generate: Tool '{tool_name}' failed: {e}")
                        tool_data = {"error": str(e)}
                        tool_diag = {"tool": tool_name, "ok": False, "error": str(e)}
                    
                    # Append result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(tool_data, ensure_ascii=False),
                    })
            
            # Append tool results
            messages.append({"role": "user", "content": tool_results})
            continue
        
        # Unknown stop reason
        break
    
    # Fallback if loop exhausted
    obj = {"query": {"raw": req.prompt, "parsed": {}}, "summary": "Unable to generate plan", "flights": {}, "lodging": {}, "transport": {}, "weather": [], "days": [], "pricing": {}, "metadata": {}}
    obj = normalize_to_contract(obj)
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
