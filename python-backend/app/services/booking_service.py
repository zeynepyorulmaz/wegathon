"""
Booking Service - Manages Hotel and Flight bookings in parallel.
Calls MCP tools concurrently for optimal performance.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import logger
from app.services.mcp_client import get_mcp_client


async def get_flight_options(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str],
    adults: int = 2,
    children: int = 0
) -> Dict[str, Any]:
    """
    Get flight options from MCP.
    
    Returns:
        {
            "outbound": {...},
            "inbound": {...},
            "alternatives": [...]
        }
    """
    logger.info(f"Fetching flights: {origin} → {destination} on {departure_date}")
    
    mcp = get_mcp_client()
    
    try:
        # Call MCP flight_search
        result = await mcp.call_tool(
            "flight_search",
            {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date or "",
                "adults": adults,
                "children": children
            }
        )
        
        logger.info(f"✅ Flights retrieved: {result}")
        
        # Parse MCP response
        return _parse_flight_response(result)
        
    except Exception as e:
        logger.error(f"❌ Flight search failed: {e}")
        return {
            "outbound": None,
            "inbound": None,
            "alternatives": [],
            "error": str(e)
        }


async def get_hotel_options(
    destination: str,
    check_in: str,
    check_out: str,
    adults: int = 2,
    children: int = 0
) -> Dict[str, Any]:
    """
    Get hotel options from MCP.
    
    Returns:
        {
            "selected": {...},
            "alternatives": [...]
        }
    """
    logger.info(f"Fetching hotels in {destination}: {check_in} to {check_out}")
    
    mcp = get_mcp_client()
    
    try:
        # Call MCP hotel_search
        result = await mcp.call_tool(
            "hotel_search",
            {
                "destination_name": destination,
                "check_in_date": check_in,
                "check_out_date": check_out,
                "adults": adults,
                "children": children
            }
        )
        
        logger.info(f"✅ Hotels retrieved: {result}")
        
        # Parse MCP response
        return _parse_hotel_response(result)
        
    except Exception as e:
        logger.error(f"❌ Hotel search failed: {e}")
        return {
            "selected": None,
            "alternatives": [],
            "error": str(e)
        }


async def get_bookings_parallel(
    origin: str,
    destination: str,
    start_date: str,
    end_date: str,
    adults: int = 2,
    children: int = 0
) -> Dict[str, Any]:
    """
    Get both flights and hotels in parallel for optimal performance.
    
    Args:
        origin: Departure city
        destination: Arrival city
        start_date: Trip start (YYYY-MM-DD)
        end_date: Trip end (YYYY-MM-DD)
        adults: Number of adults
        children: Number of children
    
    Returns:
        {
            "flights": {...},
            "hotels": {...},
            "pricing_estimate": {...}
        }
    """
    logger.info(f"🚀 Parallel booking search: {origin} → {destination}")
    
    # Run both searches in parallel
    flights_task = get_flight_options(
        origin=origin,
        destination=destination,
        departure_date=start_date,
        return_date=end_date,
        adults=adults,
        children=children
    )
    
    hotels_task = get_hotel_options(
        destination=destination,
        check_in=start_date,
        check_out=end_date,
        adults=adults,
        children=children
    )
    
    # Wait for both to complete
    flights, hotels = await asyncio.gather(flights_task, hotels_task)
    
    # Calculate pricing estimate
    pricing = _calculate_booking_pricing(flights, hotels, adults, children)
    
    logger.info(f"✅ Parallel booking complete. Total estimate: {pricing.get('total')}")
    
    return {
        "flights": flights,
        "hotels": hotels,
        "pricing": pricing,
        "search_params": {
            "origin": origin,
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "adults": adults,
            "children": children
        }
    }


def _parse_flight_response(mcp_result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse MCP flight response into structured format."""
    if not mcp_result:
        return {"outbound": None, "inbound": None, "alternatives": []}
    
    # Handle MCP response format (could be wrapped in content array)
    content = mcp_result.get("content", [])
    
    if content and isinstance(content, list) and len(content) > 0:
        # MCP returns JSON in content array
        try:
            import json
            text = content[0].get("text", "{}") if isinstance(content[0], dict) else "{}"
            data = json.loads(text)
        except Exception as e:
            logger.warning(f"Failed to parse flight content: {e}")
            data = {}
    else:
        data = mcp_result
    
    # Extract flights safely
    flights = data.get("flights", []) if isinstance(data, dict) else []
    
    if not flights:
        return {
            "outbound": None,
            "inbound": None,
            "alternatives": []
        }
    
    # First flight is selected, rest are alternatives
    selected = flights[0] if flights else None
    alternatives = flights[1:4] if len(flights) > 1 else []
    
    return {
        "outbound": selected,
        "inbound": None,  # TODO: Parse return flights if round-trip
        "alternatives": alternatives
    }


def _parse_hotel_response(mcp_result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse MCP hotel response into structured format."""
    if not mcp_result:
        return {"selected": None, "alternatives": []}
    
    # Handle MCP response format
    content = mcp_result.get("content", [])
    
    if content and isinstance(content, list) and len(content) > 0:
        try:
            import json
            text = content[0].get("text", "{}") if isinstance(content[0], dict) else "{}"
            data = json.loads(text)
        except Exception as e:
            logger.warning(f"Failed to parse hotel content: {e}")
            data = {}
    else:
        data = mcp_result
    
    # Extract hotels safely
    hotels = data.get("hotels", []) if isinstance(data, dict) else []
    
    if not hotels:
        return {
            "selected": None,
            "alternatives": []
        }
    
    # First hotel is selected, rest are alternatives
    selected = hotels[0] if hotels else None
    alternatives = hotels[1:4] if len(hotels) > 1 else []
    
    return {
        "selected": selected,
        "alternatives": alternatives
    }


def _calculate_booking_pricing(
    flights: Dict[str, Any],
    hotels: Dict[str, Any],
    adults: int,
    children: int
) -> Dict[str, Any]:
    """Calculate total pricing estimate from flights and hotels."""
    
    flight_price = 0.0
    hotel_price = 0.0
    
    # Get flight price safely
    if flights and isinstance(flights, dict) and flights.get("outbound"):
        try:
            flight_price = float(flights["outbound"].get("price", 0) or 0)
        except (TypeError, ValueError):
            flight_price = 0.0
    
    # Get hotel price safely  
    if hotels and isinstance(hotels, dict) and hotels.get("selected"):
        try:
            hotel_price = float(hotels["selected"].get("priceTotal", 0) or 0)
        except (TypeError, ValueError):
            hotel_price = 0.0
    
    total = flight_price + hotel_price
    
    # Prevent division by zero
    num_people = max(1, adults)
    
    return {
        "flights": flight_price,
        "hotels": hotel_price,
        "total": total,
        "currency": (flights or {}).get("outbound", {}).get("currency") or (hotels or {}).get("selected", {}).get("currency") or "TRY",
        "per_person": total / num_people,
        "breakdown": {
            "flights_per_person": flight_price / num_people,
            "hotels_total": hotel_price
        }
    }

