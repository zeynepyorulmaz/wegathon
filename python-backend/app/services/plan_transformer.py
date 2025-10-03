"""
Transform TripPlan to InteractivePlan format for frontend.
Builds timeline from TripPlan.days blocks (morning/afternoon/evening/...).
"""
from typing import Dict, Any, List
from datetime import datetime

from app.models.interactive_plan import InteractivePlan
from app.core.logging import logger


async def transform_to_interactive(
    trip_plan: Dict[str, Any],
    language: str = "tr"
) -> InteractivePlan:
    """
    Transform a TripPlan into InteractivePlan format using existing day blocks.
    Each DayPlan.block becomes a time slot with one or more activity options.
    """
    query = trip_plan.get("query", {}).get("parsed", {})
    destination = query.get("destinationCity", "")
    start_date = query.get("startDateISO", "")
    end_date = query.get("endDateISO", "")
    days = trip_plan.get("days", []) or []
    total_days = len(days)

    # Flight times if available (to adjust first/last day windows)
    flights = trip_plan.get("flights", {}) or {}
    arrival_time = None
    departure_time = None

    try:
        outbound = flights.get("outbound") or {}
        segs = (outbound.get("segments") or [])
        if segs:
            arrive_iso = segs[-1].get("arriveISO") or ""
            if arrive_iso:
                arrival_dt = datetime.fromisoformat(arrive_iso.replace("Z", "+00:00"))
                arrival_time = arrival_dt.strftime("%H:%M")
    except Exception:
        pass

    try:
        inbound = flights.get("inbound") or {}
        segs = (inbound.get("segments") or [])
        if segs:
            depart_iso = segs[0].get("departISO") or ""
            if depart_iso:
                depart_dt = datetime.fromisoformat(depart_iso.replace("Z", "+00:00"))
                departure_time = depart_dt.strftime("%H:%M")
    except Exception:
        pass

    # Default time windows per block label
    BLOCK_WINDOWS = {
        "morning": ("09:00", "12:00"),
        "afternoon": ("13:00", "17:00"),
        "evening": ("18:00", "21:00"),
        "late-night": ("21:00", "23:59"),
        "check-in": ("12:00", "15:00"),
        "check-out": ("10:00", "12:00"),
        "transit": ("00:00", "00:00"),
    }

    time_slots: List[Dict[str, Any]] = []

    for idx, day in enumerate(days, start=1):
        blocks = day.get("blocks") or []
        for b in blocks:
            label = (b.get("label") or "morning").lower()
            start_t, end_t = BLOCK_WINDOWS.get(label, ("09:00", "12:00"))

            # Adjust first/last day boundaries with flight times when available
            if idx == 1 and arrival_time and label in ("morning", "transit", "check-in"):
                start_t = min(arrival_time, start_t)
            if idx == total_days and departure_time and label in ("afternoon", "evening", "late-night", "check-out"):
                end_t = max("00:00", departure_time)

            # Map activity items to options
            options: List[Dict[str, Any]] = []
            for item in (b.get("items") or []):
                if item.get("type") == "activity":
                    data = item.get("data") or {}
                    options.append({
                        "text": data.get("title") or "Activity",
                        "description": data.get("notes") or data.get("category"),
                        "price": data.get("price"),
                        "duration": data.get("durationMinutes"),
                        "location": (data.get("location") or {}).get("name"),
                        "booking_url": data.get("bookingUrl"),
                    })

            # Fallback option if no activities exist for the block
            if not options:
                label_title = {
                    "transit": "Transit",
                    "check-in": "Check-in",
                    "check-out": "Check-out",
                }.get(label, label.title())
                options.append({
                    "text": label_title,
                    "description": None,
                    "price": None,
                    "duration": None,
                    "location": None,
                    "booking_url": None,
                })

            time_slots.append({
                "day": idx,
                "startTime": start_t,
                "endTime": end_t,
                "options": options,
            })

    interactive = InteractivePlan(
        trip_summary=trip_plan.get("summary", ""),
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        time_slots=time_slots,
        flights=flights or None,
        lodging=trip_plan.get("lodging"),
        pricing=trip_plan.get("pricing"),
        weather=trip_plan.get("weather"),
    )

    logger.info(f"Interactive plan built: {len(time_slots)} time slots for {total_days} day(s)")
    return interactive
