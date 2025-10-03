"""
Interactive plan models for frontend display.
Each time slot has multiple options for user to choose from.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class ActivityOption(BaseModel):
    """A single activity option within a time slot."""
    text: str = Field(..., description="Main activity description")
    description: str = Field(..., description="Why this option is good / who it's for")
    price: Optional[float] = None
    duration: Optional[int] = None  # minutes
    location: Optional[str] = None
    booking_url: Optional[str] = None


class TimeSlot(BaseModel):
    """A time slot with multiple activity options."""
    day: int = Field(..., description="Day number (1, 2, 3...)")
    startTime: str = Field(..., description="Start time in HH:MM format")
    endTime: str = Field(..., description="End time in HH:MM format")
    options: List[ActivityOption] = Field(..., description="List of activity options for this time slot")
    block_type: Optional[str] = Field(None, description="morning, afternoon, evening, etc.")


class InteractivePlan(BaseModel):
    """
    Interactive travel plan where each time slot offers multiple options.
    User can choose their preferred activities.
    """
    trip_summary: str = Field(..., description="Overall trip summary")
    destination: str
    start_date: str
    end_date: str
    total_days: int
    time_slots: List[TimeSlot] = Field(..., description="All time slots with options")
    
    # Metadata
    flights: Optional[dict] = None
    lodging: Optional[dict] = None
    pricing: Optional[dict] = None
    weather: Optional[List[dict]] = None

