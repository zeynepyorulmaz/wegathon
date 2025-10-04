"""
API endpoints for trip sharing and collaboration
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.sharing import (
    CreateShareRequest,
    CreateShareResponse,
    CreateSuggestionRequest,
    ReviewSuggestionRequest,
    SharedTripResponse,
    TripSuggestion,
    Notification
)
from app.services.sharing_service import sharing_service
from app.routers.plan import conversation_sessions  # Import session storage

router = APIRouter(tags=["sharing"])


# === SHARING ENDPOINTS ===

@router.post("/trips/{trip_id}/share", response_model=CreateShareResponse)
async def create_share_link(
    trip_id: str,
    request: CreateShareRequest,
    owner_id: str = Query(default="anonymous", description="User ID of trip owner")
):
    """
    Create a shareable link for a trip
    
    - **trip_id**: ID of the trip to share
    - **permission_level**: view, suggest, or edit
    - **is_public**: Whether anyone with link can access
    - **expires_in_days**: Optional expiration in days
    """
    try:
        # Get trip data - try from request body first, then sessions, then templates
        trip_data = request.dict().get('trip_data')  # Frontend can send trip data directly
        
        print(f"🔍 Looking for trip_id: {trip_id}")
        print(f"📦 Trip data from request body: {'YES' if trip_data else 'NO'}")
        
        # If not provided in request, try to get from active sessions
        if not trip_data:
            print(f"📋 Active sessions: {list(conversation_sessions.keys())}")
            if trip_id in conversation_sessions:
                session = conversation_sessions[trip_id]
                print(f"✅ Found session for {trip_id}")
                if session.final_plan:
                    trip_data = session.final_plan
                    print(f"📦 Got trip_data from session")
                else:
                    print(f"⚠️ Session has no final_plan")
            else:
                print(f"❌ Trip {trip_id} not in active sessions")
        
        # If still not found, try templates
        if not trip_data:
            try:
                from app.routers.plan import load_templates
                templates = load_templates()
                template = templates.get(trip_id)
                if template:
                    trip_data = template.get('plan')
                    print(f"📄 Got trip_data from template")
            except Exception as e:
                print(f"❌ Template lookup failed: {e}")
                pass
        
        response = sharing_service.create_share(request, owner_id, trip_data)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shared/{share_token}")
async def get_shared_trip(share_token: str):
    """
    Get a shared trip by its token
    
    Returns trip data, permissions, and all suggestions
    """
    try:
        print(f"🔎 Fetching shared trip: {share_token}")
        # Get shared trip metadata
        shared_trip = sharing_service.get_shared_trip(share_token)
        print(f"📦 Shared trip found: {shared_trip is not None}")
        if shared_trip:
            print(f"📊 Has trip_data: {shared_trip.trip_data is not None}")
        if not shared_trip:
            print(f"❌ Share link not found or expired")
            raise HTTPException(status_code=404, detail="Share link not found or expired")
        
        # Get trip data (cached, sessions, or templates)
        trip_data = shared_trip.trip_data  # Try cached data first
        
        # If no cached data, try to get from active sessions
        if not trip_data and shared_trip.trip_id in conversation_sessions:
            session = conversation_sessions[shared_trip.trip_id]
            if session.final_plan:
                trip_data = session.final_plan
        
        # If not in sessions, try templates
        if not trip_data:
            try:
                from app.routers.plan import load_templates
                templates = load_templates()
                template = templates.get(shared_trip.trip_id)
                if template:
                    trip_data = template.get('plan')
            except:
                pass
        
        if not trip_data:
            raise HTTPException(status_code=404, detail="Trip data not found")
        
        # Get suggestions
        suggestions = sharing_service.get_trip_suggestions(shared_trip.trip_id)
        
        # Count by status
        pending = sum(1 for s in suggestions if s.status == "pending")
        accepted = sum(1 for s in suggestions if s.status == "accepted")
        rejected = sum(1 for s in suggestions if s.status == "rejected")
        
        # Determine permissions
        permissions = {
            "can_view": True,
            "can_suggest": shared_trip.permission_level in ["suggest", "edit"],
            "can_edit": shared_trip.permission_level == "edit"
        }
        
        return {
            "share": shared_trip,
            "trip": trip_data,
            "permissions": permissions,
            "suggestions": suggestions,
            "pending_count": pending,
            "accepted_count": accepted,
            "rejected_count": rejected
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trips/{trip_id}/shares")
async def get_trip_shares(trip_id: str):
    """Get all active share links for a trip"""
    try:
        shares = sharing_service.get_trip_shares(trip_id)
        return {"shares": shares, "count": len(shares)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/shared/{share_token}")
async def revoke_share_link(share_token: str):
    """Revoke a share link"""
    try:
        success = sharing_service.revoke_share(share_token)
        if not success:
            raise HTTPException(status_code=404, detail="Share link not found")
        return {"message": "Share link revoked", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === SUGGESTION ENDPOINTS ===

@router.post("/shared/{share_token}/suggestions", response_model=TripSuggestion)
async def create_suggestion(
    share_token: str,
    request: CreateSuggestionRequest
):
    """
    Create a suggestion for an activity change
    
    - **time_slot_id**: ID of the time slot to modify
    - **day**: Day number
    - **original_activity_index**: Index of activity to replace
    - **suggested_activity**: New activity data
    - **reason**: Optional explanation
    """
    try:
        suggestion = sharing_service.create_suggestion(share_token, request)
        return suggestion
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trips/{trip_id}/suggestions")
async def get_trip_suggestions(
    trip_id: str,
    status: Optional[str] = Query(default=None, description="Filter by status: pending, accepted, rejected")
):
    """Get all suggestions for a trip (for trip owner)"""
    try:
        suggestions = sharing_service.get_trip_suggestions(trip_id, status)
        return {
            "suggestions": suggestions,
            "count": len(suggestions),
            "pending": sum(1 for s in suggestions if s.status == "pending"),
            "accepted": sum(1 for s in suggestions if s.status == "accepted"),
            "rejected": sum(1 for s in suggestions if s.status == "rejected")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/{suggestion_id}")
async def get_suggestion(suggestion_id: str):
    """Get a specific suggestion"""
    try:
        suggestion = sharing_service.get_suggestion(suggestion_id)
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        return suggestion
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/suggestions/{suggestion_id}/review", response_model=TripSuggestion)
async def review_suggestion(
    suggestion_id: str,
    request: ReviewSuggestionRequest
):
    """
    Accept or reject a suggestion
    
    - **action**: "accept" or "reject"
    - **review_note**: Optional note for the suggester
    """
    try:
        suggestion = sharing_service.review_suggestion(suggestion_id, request)
        
        # If accepted, update the actual trip data
        if request.action == "accept":
            # Update the shared trip's cached trip_data
            shared_trip = sharing_service.get_shared_trip(suggestion.shared_trip_id)
            if shared_trip and shared_trip.trip_data:
                trip_data = shared_trip.trip_data
                # Find time slot and update activity
                for slot in trip_data.get('time_slots', []):
                    if slot.get('id') == suggestion.time_slot_id:
                        if 'options' in slot and len(slot['options']) > suggestion.original_activity_index:
                            slot['options'][suggestion.original_activity_index] = suggestion.suggested_activity
                            # Save updated trip data back to shared trip
                            shared_trip.trip_data = trip_data
                            sharing_service.update_shared_trip(shared_trip)
                            break
            
            # Also update session data if exists
            if suggestion.trip_id in conversation_sessions:
                session = conversation_sessions[suggestion.trip_id]
                if session.final_plan:
                    trip_data = session.final_plan
                    # Find time slot and update activity
                    for slot in trip_data.get('time_slots', []):
                        if slot.get('id') == suggestion.time_slot_id:
                            if 'options' in slot and len(slot['options']) > suggestion.original_activity_index:
                                slot['options'][suggestion.original_activity_index] = suggestion.suggested_activity
                                # Update session
                                session.final_plan = trip_data
                                conversation_sessions[suggestion.trip_id] = session
                                break
        
        return suggestion
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === NOTIFICATION ENDPOINTS ===

@router.get("/notifications", response_model=List[Notification])
async def get_notifications(
    user_id: str = Query(..., description="User ID"),
    unread_only: bool = Query(default=False, description="Only unread notifications")
):
    """Get notifications for a user"""
    try:
        notifications = sharing_service.get_user_notifications(user_id, unread_only)
        return notifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: str = Query(..., description="User ID")
):
    """Mark a notification as read"""
    try:
        success = sharing_service.mark_notification_read(user_id, notification_id)
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"message": "Notification marked as read", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    user_id: str = Query(..., description="User ID")
):
    """Delete a notification"""
    try:
        success = sharing_service.delete_notification(user_id, notification_id)
        return {"message": "Notification deleted", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/unread-count")
async def get_unread_count(user_id: str = Query(..., description="User ID")):
    """Get count of unread notifications"""
    try:
        notifications = sharing_service.get_user_notifications(user_id, unread_only=True)
        return {"count": len(notifications)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
