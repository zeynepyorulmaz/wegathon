"""
Timeline Manipulation Models
Handles activity reordering, time adjustments, and alternative suggestions
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class TimeSlotUpdate(BaseModel):
    """Update a time slot's time range"""
    slot_id: str = Field(..., description="Unique slot identifier")
    day: int = Field(..., description="Day number (1-based)")
    start_time: str = Field(..., description="New start time (HH:MM)")
    end_time: str = Field(..., description="New end time (HH:MM)")


class ActivityReorder(BaseModel):
    """Reorder activities in timeline"""
    session_id: str = Field(..., description="Trip session ID")
    from_slot_id: str = Field(..., description="Source slot ID")
    to_slot_id: str = Field(..., description="Target slot ID")
    from_day: int = Field(..., description="Source day")
    to_day: int = Field(..., description="Target day")
    activity_index: int = Field(..., description="Activity index in slot")


class ActivityRemove(BaseModel):
    """Remove an activity from timeline"""
    session_id: str = Field(..., description="Trip session ID")
    slot_id: str = Field(..., description="Slot ID")
    day: int = Field(..., description="Day number")
    activity_index: int = Field(..., description="Activity index to remove")


class AlternativeRequest(BaseModel):
    """Request alternative activities for a slot"""
    session_id: str = Field(..., description="Trip session ID")
    slot_id: str = Field(..., description="Slot ID")
    day: int = Field(..., description="Day number")
    destination: str = Field(..., description="Destination city")
    time_window: str = Field(..., description="Time of day (morning/afternoon/evening)")
    preferences: List[str] = Field(default_factory=list, description="User preferences")
    exclude_ids: List[str] = Field(default_factory=list, description="Activity IDs to exclude")
    language: str = Field(default="tr", description="Response language")


class TeamShare(BaseModel):
    """Share trip plan with team members"""
    session_id: str = Field(..., description="Trip session ID")
    team_members: List[str] = Field(..., description="Email addresses of team members")
    message: Optional[str] = Field(None, description="Optional message")
    permissions: str = Field(default="view", description="Permissions: view, edit, admin")


class PublicTemplate(BaseModel):
    """Create a public template from trip"""
    session_id: str = Field(..., description="Trip session ID")
    template_name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    tags: List[str] = Field(default_factory=list, description="Template tags")
    is_public: bool = Field(default=True, description="Make template public")


class TemplateFork(BaseModel):
    """Fork an existing template"""
    template_id: str = Field(..., description="Template ID to fork")
    customize: Dict[str, Any] = Field(default_factory=dict, description="Customizations")
    start_date: Optional[str] = Field(None, description="New start date")
    end_date: Optional[str] = Field(None, description="New end date")


class TimelineUpdate(BaseModel):
    """Complete timeline update response"""
    success: bool
    message: str
    updated_timeline: Optional[Dict[str, Any]] = None
    alternatives: Optional[List[Dict[str, Any]]] = None
