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
  async getInteractivePlan(request: InteractivePlanRequest): Promise<any> {
    return this.request("/api/plan/interactive", {
      method: "POST",
      body: JSON.stringify(request),
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

