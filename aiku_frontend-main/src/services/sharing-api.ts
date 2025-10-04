/**
 * API service for trip sharing and collaboratiexport interface CreateShareRequest {
  trip_id: string;
  permission_level: 'view' | 'suggest' | 'edit';
  is_public?: boolean;
  expires_in_days?: number;
  owner_name?: string;
  trip_data?: Record<string, unknown>;  // Optional trip data to cache
}ures
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

export interface SharedTrip {
  id: string;
  trip_id: string;
  owner_id: string;
  owner_name: string;
  share_token: string;
  permission_level: 'view' | 'suggest' | 'edit';
  is_public: boolean;
  created_at: string;
  expires_at: string | null;
  allowed_users: string[];
  view_count: number;
}

export interface TripSuggestion {
  id: string;
  shared_trip_id: string;
  trip_id: string;
  suggested_by_id: string | null;
  suggested_by_name: string;
  time_slot_id: string;
  day: number;
  original_activity_index: number;
  original_activity: Record<string, unknown>;
  suggested_activity: Record<string, unknown>;
  reason: string | null;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
  reviewed_at: string | null;
  review_note: string | null;
}

export interface Notification {
  id: string;
  user_id: string;
  trip_id: string;
  type: 'new_suggestion' | 'suggestion_accepted' | 'suggestion_rejected' | 'trip_shared' | 'trip_updated';
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  data: Record<string, unknown>;
  action_url: string | null;
}

export interface CreateShareRequest {
  trip_id: string;
  permission_level?: 'view' | 'suggest' | 'edit';
  is_public?: boolean;
  expires_in_days?: number;
  owner_name?: string;
}

export interface CreateShareResponse {
  share_id: string;
  share_token: string;
  share_url: string;
  permission_level: string;
  expires_at: string | null;
}

export interface SharedTripResponse {
  share: SharedTrip;
  trip: Record<string, unknown>;
  permissions: {
    can_view: boolean;
    can_suggest: boolean;
    can_edit: boolean;
  };
  suggestions: TripSuggestion[];
  pending_count: number;
  accepted_count: number;
  rejected_count: number;
}

export interface CreateSuggestionRequest {
  time_slot_id: string;
  day: number;
  original_activity_index: number;
  original_activity: Record<string, unknown>;
  suggested_activity: Record<string, unknown>;
  reason?: string;
  suggested_by_name?: string;
  suggested_by_id?: string;
}

// === SHARING API ===

export async function createShareLink(
  request: CreateShareRequest,
  ownerId: string = 'anonymous'
): Promise<CreateShareResponse> {
  const response = await fetch(`${API_BASE}/api/plan/trips/${request.trip_id}/share?owner_id=${ownerId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to create share link' }));
    throw new Error(error.detail || 'Failed to create share link');
  }

  return response.json();
}

export async function getSharedTrip(shareToken: string): Promise<SharedTripResponse> {
  const response = await fetch(`${API_BASE}/api/plan/shared/${shareToken}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to load shared trip' }));
    throw new Error(error.detail || 'Failed to load shared trip');
  }

  return response.json();
}

export async function getTripShares(tripId: string): Promise<{ shares: SharedTrip[]; count: number }> {
  const response = await fetch(`${API_BASE}/api/plan/trips/${tripId}/shares`);

  if (!response.ok) {
    throw new Error('Failed to load trip shares');
  }

  return response.json();
}

export async function revokeShareLink(shareToken: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/plan/shared/${shareToken}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('Failed to revoke share link');
  }
}

// === SUGGESTION API ===

export async function createSuggestion(
  shareToken: string,
  request: CreateSuggestionRequest
): Promise<TripSuggestion> {
  const response = await fetch(`${API_BASE}/api/plan/shared/${shareToken}/suggestions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to create suggestion' }));
    throw new Error(error.detail || 'Failed to create suggestion');
  }

  return response.json();
}

export async function getTripSuggestions(
  tripId: string,
  status?: 'pending' | 'accepted' | 'rejected'
): Promise<{ suggestions: TripSuggestion[]; count: number; pending: number; accepted: number; rejected: number }> {
  const url = new URL(`${API_BASE}/api/plan/trips/${tripId}/suggestions`);
  if (status) {
    url.searchParams.set('status', status);
  }

  const response = await fetch(url.toString());

  if (!response.ok) {
    throw new Error('Failed to load suggestions');
  }

  return response.json();
}

export async function reviewSuggestion(
  suggestionId: string,
  action: 'accept' | 'reject',
  reviewNote?: string
): Promise<TripSuggestion> {
  const response = await fetch(`${API_BASE}/api/plan/suggestions/${suggestionId}/review`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, review_note: reviewNote }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to review suggestion' }));
    throw new Error(error.detail || 'Failed to review suggestion');
  }

  return response.json();
}

// === NOTIFICATION API ===

export async function getNotifications(
  userId: string,
  unreadOnly: boolean = false
): Promise<Notification[]> {
  const url = new URL(`${API_BASE}/api/plan/notifications`);
  url.searchParams.set('user_id', userId);
  url.searchParams.set('unread_only', unreadOnly.toString());

  const response = await fetch(url.toString());

  if (!response.ok) {
    throw new Error('Failed to load notifications');
  }

  return response.json();
}

export async function markNotificationRead(userId: string, notificationId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/plan/notifications/${notificationId}/read?user_id=${userId}`,
    {
      method: 'PATCH',
    }
  );

  if (!response.ok) {
    throw new Error('Failed to mark notification as read');
  }
}

export async function deleteNotification(userId: string, notificationId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/plan/notifications/${notificationId}?user_id=${userId}`,
    {
      method: 'DELETE',
    }
  );

  if (!response.ok) {
    throw new Error('Failed to delete notification');
  }
}

export async function getUnreadCount(userId: string): Promise<number> {
  const url = new URL(`${API_BASE}/api/plan/notifications/unread-count`);
  url.searchParams.set('user_id', userId);

  const response = await fetch(url.toString());

  if (!response.ok) {
    return 0;
  }

  const data = await response.json();
  return data.count || 0;
}
