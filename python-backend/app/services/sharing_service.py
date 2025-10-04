"""
Service layer for trip sharing and collaboration
"""
import json
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.models.sharing import (
    SharedTrip,
    TripSuggestion,
    Notification,
    CreateShareRequest,
    CreateShareResponse,
    CreateSuggestionRequest,
    ReviewSuggestionRequest,
    SharedTripResponse
)

# Storage paths
DATA_DIR = Path(__file__).parent.parent / "data"
SHARED_TRIPS_FILE = DATA_DIR / "shared_trips.json"
SUGGESTIONS_FILE = DATA_DIR / "suggestions.json"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"


class SharingService:
    """Service for managing trip sharing and suggestions"""
    
    def __init__(self):
        self._ensure_data_files()
    
    def _ensure_data_files(self):
        """Ensure data directory and files exist"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        for file_path in [SHARED_TRIPS_FILE, SUGGESTIONS_FILE, NOTIFICATIONS_FILE]:
            if not file_path.exists():
                file_path.write_text("{}")
    
    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON data from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_json(self, file_path: Path, data: Dict):
        """Save JSON data to file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    # === SHARING ===
    
    def create_share(
        self,
        request: CreateShareRequest,
        owner_id: str = "anonymous",
        trip_data: Optional[Dict[str, Any]] = None
    ) -> CreateShareResponse:
        """Create a new share link for a trip"""
        # Generate unique token
        share_token = secrets.token_urlsafe(16)
        share_id = f"share-{secrets.token_urlsafe(8)}"
        
        # Calculate expiration
        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        # Create shared trip
        shared_trip = SharedTrip(
            id=share_id,
            trip_id=request.trip_id,
            owner_id=owner_id,
            owner_name=request.owner_name,
            share_token=share_token,
            permission_level=request.permission_level,
            is_public=request.is_public,
            expires_at=expires_at,
            trip_data=trip_data
        )
        
        # Save to storage
        shared_trips = self._load_json(SHARED_TRIPS_FILE)
        shared_trips[share_token] = shared_trip.model_dump(mode='json')
        self._save_json(SHARED_TRIPS_FILE, shared_trips)
        
        return CreateShareResponse(
            share_id=share_id,
            share_token=share_token,
            share_url=f"/shared/{share_token}",
            permission_level=request.permission_level,
            expires_at=expires_at
        )
    
    def get_shared_trip(self, share_token: str) -> Optional[SharedTrip]:
        """Get shared trip by token"""
        print(f"🔍 SharingService: Looking for token: {share_token}")
        shared_trips = self._load_json(SHARED_TRIPS_FILE)
        print(f"📚 Total shared trips in file: {len(shared_trips)}")
        print(f"🔑 Available tokens: {list(shared_trips.keys())[:5]}...")  # Show first 5
        trip_data = shared_trips.get(share_token)
        print(f"✅ Found trip data: {trip_data is not None}")
        if not trip_data:
            return None
        
        shared_trip = SharedTrip(**trip_data)
        print(f"🎯 Created SharedTrip object successfully")
        
        # Check expiration
        if shared_trip.expires_at and shared_trip.expires_at < datetime.utcnow():
            return None
        
        # Increment view count
        shared_trip.view_count += 1
        shared_trips[share_token] = shared_trip.model_dump(mode='json')
        self._save_json(SHARED_TRIPS_FILE, shared_trips)
        
        return shared_trip
    
    def update_shared_trip(self, shared_trip: SharedTrip) -> None:
        """Update shared trip data in storage"""
        shared_trips = self._load_json(SHARED_TRIPS_FILE)
        shared_trips[shared_trip.share_token] = shared_trip.model_dump(mode='json')
        self._save_json(SHARED_TRIPS_FILE, shared_trips)
        print(f"✅ Updated shared trip: {shared_trip.share_token}")
    
    def get_trip_shares(self, trip_id: str) -> List[SharedTrip]:
        """Get all share links for a trip"""
        shared_trips = self._load_json(SHARED_TRIPS_FILE)
        result = []
        
        for trip_data in shared_trips.values():
            if trip_data.get('trip_id') == trip_id:
                shared_trip = SharedTrip(**trip_data)
                # Skip expired
                if shared_trip.expires_at and shared_trip.expires_at < datetime.utcnow():
                    continue
                result.append(shared_trip)
        
        return result
    
    def revoke_share(self, share_token: str) -> bool:
        """Revoke a share link"""
        shared_trips = self._load_json(SHARED_TRIPS_FILE)
        if share_token in shared_trips:
            del shared_trips[share_token]
            self._save_json(SHARED_TRIPS_FILE, shared_trips)
            return True
        return False
    
    # === SUGGESTIONS ===
    
    def create_suggestion(
        self,
        share_token: str,
        request: CreateSuggestionRequest
    ) -> TripSuggestion:
        """Create a new activity suggestion"""
        shared_trip = self.get_shared_trip(share_token)
        if not shared_trip:
            raise ValueError("Invalid or expired share link")
        
        if shared_trip.permission_level not in ["suggest", "edit"]:
            raise ValueError("No permission to suggest")
        
        # Create suggestion
        suggestion_id = f"sugg-{secrets.token_urlsafe(8)}"
        suggestion = TripSuggestion(
            id=suggestion_id,
            shared_trip_id=shared_trip.id,
            trip_id=shared_trip.trip_id,
            suggested_by_id=request.suggested_by_id,
            suggested_by_name=request.suggested_by_name,
            time_slot_id=request.time_slot_id,
            day=request.day,
            original_activity_index=request.original_activity_index,
            original_activity=request.original_activity,
            suggested_activity=request.suggested_activity,
            reason=request.reason
        )
        
        # Save suggestion
        suggestions = self._load_json(SUGGESTIONS_FILE)
        suggestions[suggestion_id] = suggestion.model_dump(mode='json')
        self._save_json(SUGGESTIONS_FILE, suggestions)
        
        # Create notification for trip owner
        self._create_notification(
            user_id=shared_trip.owner_id,
            trip_id=shared_trip.trip_id,
            notif_type="new_suggestion",
            title="Yeni Öneri",
            message=f"{request.suggested_by_name}, Day {request.day} için bir aktivite önerdi",
            data={
                "suggestion_id": suggestion_id,
                "suggested_by": request.suggested_by_name,
                "day": request.day
            },
            action_url=f"/shared/{share_token}"
        )
        
        return suggestion
    
    def get_trip_suggestions(
        self,
        trip_id: str,
        status: Optional[str] = None
    ) -> List[TripSuggestion]:
        """Get all suggestions for a trip"""
        suggestions = self._load_json(SUGGESTIONS_FILE)
        result = []
        
        for sugg_data in suggestions.values():
            if sugg_data.get('trip_id') == trip_id:
                if status and sugg_data.get('status') != status:
                    continue
                result.append(TripSuggestion(**sugg_data))
        
        # Sort by created_at descending
        result.sort(key=lambda x: x.created_at, reverse=True)
        return result
    
    def get_suggestion(self, suggestion_id: str) -> Optional[TripSuggestion]:
        """Get a specific suggestion"""
        suggestions = self._load_json(SUGGESTIONS_FILE)
        sugg_data = suggestions.get(suggestion_id)
        if not sugg_data:
            return None
        return TripSuggestion(**sugg_data)
    
    def review_suggestion(
        self,
        suggestion_id: str,
        request: ReviewSuggestionRequest
    ) -> TripSuggestion:
        """Accept or reject a suggestion"""
        suggestion = self.get_suggestion(suggestion_id)
        if not suggestion:
            raise ValueError("Suggestion not found")
        
        if suggestion.status != "pending":
            raise ValueError("Suggestion already reviewed")
        
        # Update suggestion
        suggestion.status = request.action + "ed"  # accepted/rejected
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.review_note = request.review_note
        
        # Save
        suggestions = self._load_json(SUGGESTIONS_FILE)
        suggestions[suggestion_id] = suggestion.model_dump(mode='json')
        self._save_json(SUGGESTIONS_FILE, suggestions)
        
        # Notify suggester (if has ID)
        if suggestion.suggested_by_id:
            notif_type = "suggestion_accepted" if request.action == "accept" else "suggestion_rejected"
            title = "Öneri Kabul Edildi! 🎉" if request.action == "accept" else "Öneri Reddedildi"
            message = f"Day {suggestion.day} için öneriniz kabul edildi" if request.action == "accept" else f"Day {suggestion.day} için öneriniz reddedildi"
            
            self._create_notification(
                user_id=suggestion.suggested_by_id,
                trip_id=suggestion.trip_id,
                notif_type=notif_type,
                title=title,
                message=message,
                data={
                    "suggestion_id": suggestion_id,
                    "review_note": request.review_note
                }
            )
        
        return suggestion
    
    # === NOTIFICATIONS ===
    
    def _create_notification(
        self,
        user_id: str,
        trip_id: str,
        notif_type: str,
        title: str,
        message: str,
        data: Dict[str, Any] = None,
        action_url: Optional[str] = None
    ) -> Notification:
        """Create a notification"""
        notif_id = f"notif-{secrets.token_urlsafe(8)}"
        notification = Notification(
            id=notif_id,
            user_id=user_id,
            trip_id=trip_id,
            type=notif_type,
            title=title,
            message=message,
            data=data or {},
            action_url=action_url
        )
        
        notifications = self._load_json(NOTIFICATIONS_FILE)
        if user_id not in notifications:
            notifications[user_id] = []
        notifications[user_id].append(notification.model_dump(mode='json'))
        self._save_json(NOTIFICATIONS_FILE, notifications)
        
        return notification
    
    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False
    ) -> List[Notification]:
        """Get notifications for a user"""
        notifications = self._load_json(NOTIFICATIONS_FILE)
        user_notifs = notifications.get(user_id, [])
        
        result = []
        for notif_data in user_notifs:
            notif = Notification(**notif_data)
            if unread_only and notif.read:
                continue
            result.append(notif)
        
        # Sort by created_at descending
        result.sort(key=lambda x: x.created_at, reverse=True)
        return result
    
    def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read"""
        notifications = self._load_json(NOTIFICATIONS_FILE)
        user_notifs = notifications.get(user_id, [])
        
        for notif_data in user_notifs:
            if notif_data.get('id') == notification_id:
                notif_data['read'] = True
                self._save_json(NOTIFICATIONS_FILE, notifications)
                return True
        
        return False
    
    def delete_notification(self, user_id: str, notification_id: str) -> bool:
        """Delete a notification"""
        notifications = self._load_json(NOTIFICATIONS_FILE)
        user_notifs = notifications.get(user_id, [])
        
        notifications[user_id] = [
            n for n in user_notifs if n.get('id') != notification_id
        ]
        self._save_json(NOTIFICATIONS_FILE, notifications)
        return True


# Singleton instance
sharing_service = SharingService()
