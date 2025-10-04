"""
Sharing and collaboration models for trip planning
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class SharedTrip(BaseModel):
    """Represents a shared trip link"""
    id: str = Field(..., description="Unique share ID")
    trip_id: str = Field(..., description="Original trip/template ID")
    owner_id: str = Field(..., description="Trip owner user ID")
    owner_name: str = Field(default="Anonymous", description="Trip owner display name")
    share_token: str = Field(..., description="Unique shareable token")
    permission_level: Literal["view", "suggest", "edit"] = Field(
        default="suggest",
        description="Permission level for shared users"
    )
    is_public: bool = Field(default=True, description="Public link or private")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None, description="Optional expiration")
    allowed_users: List[str] = Field(
        default_factory=list,
        description="Empty = anyone with link, else only these user IDs"
    )
    view_count: int = Field(default=0, description="Number of views")
    trip_data: Optional[Dict[str, Any]] = Field(default=None, description="Cached trip data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "share-abc123",
                "trip_id": "trip-xyz789",
                "owner_id": "user-001",
                "owner_name": "Zeynep",
                "share_token": "abc123def456",
                "permission_level": "suggest",
                "is_public": True,
                "created_at": "2025-10-04T10:00:00Z",
                "expires_at": None,
                "allowed_users": [],
                "view_count": 0
            }
        }


class TripSuggestion(BaseModel):
    """Represents a suggestion to modify an activity"""
    id: str = Field(..., description="Unique suggestion ID")
    shared_trip_id: str = Field(..., description="Reference to shared trip")
    trip_id: str = Field(..., description="Original trip ID")
    suggested_by_id: Optional[str] = Field(default=None, description="User ID if logged in")
    suggested_by_name: str = Field(default="Anonymous", description="Display name")
    time_slot_id: str = Field(..., description="Which time slot to modify")
    day: int = Field(..., description="Day number")
    original_activity_index: int = Field(..., description="Index in options array")
    original_activity: Dict[str, Any] = Field(..., description="Original activity data")
    suggested_activity: Dict[str, Any] = Field(..., description="Suggested activity data")
    reason: Optional[str] = Field(default=None, description="Why this suggestion?")
    status: Literal["pending", "accepted", "rejected"] = Field(default="pending")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = Field(default=None)
    review_note: Optional[str] = Field(default=None, description="Owner's note on review")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "sugg-001",
                "shared_trip_id": "share-abc123",
                "trip_id": "trip-xyz789",
                "suggested_by_id": None,
                "suggested_by_name": "Ali",
                "time_slot_id": "slot-456",
                "day": 2,
                "original_activity_index": 0,
                "original_activity": {
                    "title": "Colosseum Tour",
                    "price": "€25",
                    "duration": "2 hours"
                },
                "suggested_activity": {
                    "title": "Roman Forum Tour",
                    "price": "€15",
                    "duration": "1.5 hours"
                },
                "reason": "Daha az kalabalık ve ucuz",
                "status": "pending",
                "created_at": "2025-10-04T10:30:00Z"
            }
        }


class Notification(BaseModel):
    """User notification"""
    id: str = Field(..., description="Unique notification ID")
    user_id: str = Field(..., description="Recipient user ID")
    trip_id: str = Field(..., description="Related trip ID")
    type: Literal[
        "new_suggestion",
        "suggestion_accepted",
        "suggestion_rejected",
        "trip_shared",
        "trip_updated"
    ] = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context data"
    )
    action_url: Optional[str] = Field(default=None, description="URL to navigate to")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "notif-001",
                "user_id": "user-001",
                "trip_id": "trip-xyz789",
                "type": "new_suggestion",
                "title": "Yeni Öneri",
                "message": "Ali, Day 2 için bir aktivite önerdi",
                "read": False,
                "created_at": "2025-10-04T10:30:00Z",
                "data": {
                    "suggestion_id": "sugg-001",
                    "suggested_by": "Ali"
                },
                "action_url": "/shared/abc123"
            }
        }


# Request/Response schemas
class CreateShareRequest(BaseModel):
    """Request to create a share link"""
    trip_id: str
    permission_level: Literal["view", "suggest", "edit"] = "suggest"
    is_public: bool = True
    expires_in_days: Optional[int] = None
    owner_name: str = "Anonymous"
    trip_data: Optional[Dict[str, Any]] = None  # Trip data to cache


class CreateShareResponse(BaseModel):
    """Response after creating share link"""
    share_id: str
    share_token: str
    share_url: str
    permission_level: str
    expires_at: Optional[datetime] = None


class CreateSuggestionRequest(BaseModel):
    """Request to create a suggestion"""
    time_slot_id: str
    day: int
    original_activity_index: int
    original_activity: Dict[str, Any]
    suggested_activity: Dict[str, Any]
    reason: Optional[str] = None
    suggested_by_name: str = "Anonymous"
    suggested_by_id: Optional[str] = None


class ReviewSuggestionRequest(BaseModel):
    """Request to accept/reject suggestion"""
    action: Literal["accept", "reject"]
    review_note: Optional[str] = None


class SharedTripResponse(BaseModel):
    """Complete shared trip data with suggestions"""
    share: SharedTrip
    trip: Dict[str, Any]
    permissions: Dict[str, bool]
    suggestions: List[TripSuggestion]
    pending_count: int
    accepted_count: int
    rejected_count: int
