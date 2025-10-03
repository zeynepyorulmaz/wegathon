import json
from datetime import datetime
from typing import Dict, Any, List
from app.models.plan import TripPlan, PlanRequest, ReviseRequest
from app.core.logging import logger
from app.services.openai_client import chat

SYSTEM = (
    "You are Trip Planner AI. Always return ONLY the strict JSON object specified. "
    "No markdown. Keys must match the contract."
)

CONTRACT_HINT = (
    "JSON keys required: query, summary, flights, lodging, transport, weather, days, pricing, metadata."
)


def _json_only_guard(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1:
            return json.loads(text[s : e + 1])
        raise


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


async def generate(req: PlanRequest) -> TripPlan:
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"User prompt: {req.prompt}\n"
                f"Language: {req.language or 'en'}\n"
                f"Currency: {req.currency or 'TRY'}\n"
                f"{CONTRACT_HINT}\n"
                "Apply planning rules: day1 flight+check-in, realistic buffers, last day checkout+return, weather-aware, budget-aware."
            ),
        },
    ]
    raw = await chat(messages)
    obj = _json_only_guard(raw)
    obj = normalize_to_contract(obj)
    return TripPlan.model_validate(obj)


async def revise(plan_json: Dict[str, Any], req: ReviseRequest) -> TripPlan:
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"Revise the following TripPlan with minimal deltas. Instruction: {req.instruction}. "
                "Return a full refreshed TripPlan JSON.\n" + json.dumps(plan_json, ensure_ascii=False)
            ),
        },
    ]
    raw = await chat(messages)
    obj = _json_only_guard(raw)
    obj = normalize_to_contract(obj)
    return TripPlan.model_validate(obj)
