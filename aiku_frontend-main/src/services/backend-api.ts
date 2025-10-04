/**
 * Backend API Client
 * Connects to Python FastAPI backend for trip planning
 */

import { getApiUrl } from "@/lib/config";

// ==================== TYPES ====================

export interface ChatStartRequest {
  initial_message: string;
  language?: string;
  currency?: string;
}

export interface ChatContinueRequest {
  session_id: string;
  message: string;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  plan: any | null;
  collected_data: Record<string, any>;
  needs_more_info: boolean;
  conversation_complete: boolean;
}

export interface BookingRequest {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  adults?: number;
  children?: number;
}

export interface ActivityRequest {
  destination: string;
  start_date: string;
  end_date: string;
  adults?: number;
  children?: number;
  preferences?: string[];
  budget?: string;
  language?: string;
}

export interface ProgressEvent {
  stage: "parsing" | "planning" | "flights" | "hotels" | "weather" | "itinerary" | "formatting" | "complete" | "error" | "cache";
  message: string;
  data?: Record<string, any>;
}

export interface SelectionRequest {
  session_id: string;
  alternative_index: number;
  day?: number;
  time_slot?: string;
}

export interface InteractivePlanRequest {
  prompt: string;
  language?: string;
  currency?: string;
}

// ==================== API CLIENT ====================

class BackendApiClient {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = getApiUrl(endpoint);
    console.log("📡 Backend API:", options?.method || "GET", url);

    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.message || "Backend API error");
    }

    return data;
  }

  // ==================== CHAT APIs ====================

  /**
   * Start conversational trip planning
   */
  async chatStart(request: ChatStartRequest): Promise<ChatResponse> {
    return this.request("/api/chat/start", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Continue conversation
   */
  async chatContinue(request: ChatContinueRequest): Promise<ChatResponse> {
    return this.request("/api/chat/continue", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Get interactive plan from conversation
   */
  async chatInteractive(sessionId: string): Promise<any> {
    return this.request("/api/chat/interactive", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  // ==================== PLANNING APIs ====================

  /**
   * Get flight + hotel options (parallel)
   */
  async getBookings(request: BookingRequest): Promise<any> {
    return this.request("/api/bookings", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Get activity plan
   */
  async getActivities(request: ActivityRequest): Promise<any> {
    return this.request("/api/activities", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Get interactive plan directly
   */
  async getInteractivePlan(request: InteractivePlanRequest, sessionId?: string): Promise<any> {
    const url = sessionId 
      ? `/api/plan/interactive?session_id=${sessionId}`
      : "/api/plan/interactive";
    
    return this.request(url, {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Stream plan generation progress via SSE
   * @param sessionId - Session ID for tracking progress
   * @param onProgress - Callback for each progress event
   * @returns Promise that resolves when stream completes
   */
  async streamPlanProgress(
    sessionId: string,
    onProgress: (event: ProgressEvent) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = getApiUrl(`/api/plan/progress/${sessionId}`);
      const eventSource = new EventSource(url);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onProgress(data);

          // Close connection on completion or error
          if (data.stage === "complete" || data.stage === "error") {
            eventSource.close();
            resolve();
          }
        } catch (error) {
          console.error("Error parsing SSE event:", error);
        }
      };

      eventSource.onerror = (error) => {
        console.error("SSE connection error:", error);
        eventSource.close();
        reject(error);
      };

      // Timeout after 2 minutes
      setTimeout(() => {
        eventSource.close();
        reject(new Error("SSE timeout"));
      }, 120000);
    });
  }

  // ==================== SELECTION APIs ====================

  /**
   * Select alternative flight
   */
  async selectFlight(request: SelectionRequest): Promise<any> {
    return this.request("/api/select/flight", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Select alternative hotel
   */
  async selectHotel(request: SelectionRequest): Promise<any> {
    return this.request("/api/select/hotel", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Select alternative activity
   */
  async selectActivity(request: SelectionRequest): Promise<any> {
    return this.request("/api/select/activity", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  // ==================== TIMELINE APIs ====================

  /**
   * Reorder activity within timeline
   */
  async timelineReorder(data: {
    session_id: string;
    from_slot: string;
    to_slot: string;
    activity_index: number;
  }): Promise<any> {
    return this.request("/api/timeline/reorder", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Update time slot
   */
  async timelineUpdateTime(data: {
    session_id: string;
    slot_id: string;
    new_start_time: string;
    new_end_time: string;
  }): Promise<any> {
    return this.request("/api/timeline/update-time", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Remove activity from timeline
   */
  async timelineRemove(data: {
    session_id: string;
    slot_id: string;
    day: number;
    activity_index: number;
  }): Promise<any> {
    return this.request("/api/timeline/remove", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Get alternative activities for a slot
   */
  async timelineGetAlternatives(data: {
    session_id: string;
    slot_id: string;
    day: number;
    destination: string;
    time_window: string;
    preferences?: string[];
    exclude_ids?: string[];
    language?: string;
  }): Promise<any> {
    return this.request("/api/timeline/alternatives", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // ==================== SHARE APIs ====================

  /**
   * Share plan publicly (with optional password)
   */
  async sharePlan(data: {
    session_id: string;
    plan: any;
    title?: string;
    description?: string;
    password?: string;
    allow_edit?: boolean;
  }): Promise<{
    success: boolean;
    share_id: string;
    share_url: string;
    has_password: boolean;
    allow_edit: boolean;
    message: string;
  }> {
    return this.request("/api/plan/share", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Get shared plan info (check if password required)
   */
  async getSharedPlanInfo(share_id: string): Promise<{
    exists: boolean;
    requires_password: boolean;
    title: string;
    description: string;
    allow_edit: boolean;
    views: number;
  }> {
    return this.request(`/api/plan/shared/${share_id}/info`);
  }

  /**
   * Get shared plan by ID (with password if required)
   */
  async getSharedPlan(share_id: string, password?: string): Promise<any> {
    return this.request(`/api/plan/shared/${share_id}`, {
      method: "POST",
      body: JSON.stringify({ password }),
    });
  }

  // ==================== UTILITY APIs ====================

  /**
   * Get available MCP tools
   */
  async getTools(): Promise<any> {
    return this.request("/api/tools");
  }

  /**
   * Health check
   */
  async health(): Promise<{ status: string; version: string; service: string }> {
    return this.request("/health");
  }
}

// Export singleton instance
export const backendApi = new BackendApiClient();

