/**
 * TypeScript Interfaces for Interactive Travel Plan
 * 
 * Usage:
 * 1. Copy these interfaces to your frontend project
 * 2. Call POST /api/plan/interactive
 * 3. Use the returned data with these types
 */

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface ActivityOption {
  text: string;           // Main activity description
  description: string;    // Why this is good / who it's for
  price?: number;         // Optional price
  duration?: number;      // Optional duration in minutes
  location?: string;      // Optional location
  booking_url?: string;   // Optional booking link
}

export interface TimeSlot {
  day: number;            // Day number (1, 2, 3...)
  startTime: string;      // Start time (HH:MM format)
  endTime: string;        // End time (HH:MM format)
  options: ActivityOption[]; // 4 activity options
  block_type?: string;    // morning, afternoon, evening, etc.
}

export interface InteractivePlan {
  trip_summary: string;
  destination: string;
  start_date: string;     // YYYY-MM-DD
  end_date: string;       // YYYY-MM-DD
  total_days: number;
  time_slots: TimeSlot[];
  
  // Optional metadata
  flights?: any;
  lodging?: any;
  pricing?: any;
  weather?: any[];
}

export interface PlanRequest {
  prompt: string;
  language?: string;      // 'tr' or 'en'
  currency?: string;      // 'TRY', 'EUR', 'USD'
}

// ============================================================================
// API SERVICE
// ============================================================================

export class TravelPlannerAPI {
  private baseURL: string;

  constructor(baseURL: string = 'http://localhost:4000/api') {
    this.baseURL = baseURL;
  }

  /**
   * Create interactive travel plan
   */
  async createInteractivePlan(request: PlanRequest): Promise<InteractivePlan> {
    const response = await fetch(`${this.baseURL}/plan/interactive`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Start conversational planning
   */
  async startChat(initialMessage: string, language: string = 'tr'): Promise<any> {
    const response = await fetch(`${this.baseURL}/chat/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        initial_message: initialMessage,
        language,
        currency: 'TRY',
      }),
    });

    return await response.json();
  }

  /**
   * Continue conversation
   */
  async continueChat(sessionId: string, message: string): Promise<any> {
    const response = await fetch(`${this.baseURL}/chat/continue`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
      }),
    });

    return await response.json();
  }

  /**
   * Get interactive plan from chat session
   */
  async getInteractiveFromChat(sessionId: string): Promise<InteractivePlan> {
    const response = await fetch(`${this.baseURL}/chat/interactive`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
      }),
    });

    return await response.json();
  }
}

// ============================================================================
// REACT HOOKS (Optional)
// ============================================================================

import { useState, useCallback } from 'react';

export function useInteractivePlan() {
  const [plan, setPlan] = useState<InteractivePlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selections, setSelections] = useState<Record<number, number>>({});

  const api = new TravelPlannerAPI();

  const fetchPlan = useCallback(async (prompt: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const planData = await api.createInteractivePlan({
        prompt,
        language: 'tr',
        currency: 'TRY',
      });
      setPlan(planData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  const selectOption = useCallback((slotIndex: number, optionIndex: number) => {
    setSelections(prev => ({
      ...prev,
      [slotIndex]: optionIndex,
    }));
  }, []);

  const getSelectedPlan = useCallback(() => {
    if (!plan) return null;
    
    return plan.time_slots.map((slot, index) => ({
      ...slot,
      selectedOption: selections[index] !== undefined 
        ? slot.options[selections[index]] 
        : null,
    }));
  }, [plan, selections]);

  return {
    plan,
    loading,
    error,
    selections,
    fetchPlan,
    selectOption,
    getSelectedPlan,
  };
}

// ============================================================================
// USAGE EXAMPLES
// ============================================================================

/*

// Example 1: React Component
import { useInteractivePlan } from './types';

function TravelPlanner() {
  const { plan, loading, fetchPlan, selectOption, selections } = useInteractivePlan();

  const handleSearch = () => {
    fetchPlan("İstanbul'dan Berlin'e 3 gün 2 kişi");
  };

  return (
    <div>
      <button onClick={handleSearch}>Search Trip</button>
      
      {loading && <p>Loading...</p>}
      
      {plan && (
        <div>
          <h1>{plan.trip_summary}</h1>
          
          {plan.time_slots.map((slot, slotIdx) => (
            <div key={slotIdx}>
              <h3>Day {slot.day} • {slot.startTime} - {slot.endTime}</h3>
              
              {slot.options.map((option, optIdx) => (
                <div 
                  key={optIdx}
                  onClick={() => selectOption(slotIdx, optIdx)}
                  className={selections[slotIdx] === optIdx ? 'selected' : ''}
                >
                  <h4>{option.text}</h4>
                  <p>{option.description}</p>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


// Example 2: Direct API Call
async function example() {
  const api = new TravelPlannerAPI('http://localhost:4000/api');
  
  const plan = await api.createInteractivePlan({
    prompt: "Berlin'e 3 günlük gezi",
    language: 'tr',
    currency: 'EUR'
  });
  
  console.log(plan.time_slots);
}


// Example 3: With Conversation
async function conversationalExample() {
  const api = new TravelPlannerAPI();
  
  // Start chat
  const chatStart = await api.startChat("Berlin'e gitmek istiyorum");
  console.log(chatStart.message); // AI's question
  
  // Continue
  const chatContinue = await api.continueChat(chatStart.session_id, "3 gün");
  
  // Get interactive plan when ready
  if (chatContinue.conversation_complete) {
    const plan = await api.getInteractiveFromChat(chatStart.session_id);
    console.log(plan.time_slots);
  }
}

*/

// ============================================================================
// SAMPLE DATA (for testing without backend)
// ============================================================================

export const SAMPLE_PLAN: InteractivePlan = {
  trip_summary: "3 günlük Berlin seyahati - Tarihi yerler, müzeler ve yerel kültür",
  destination: "Berlin",
  start_date: "2023-11-20",
  end_date: "2023-11-23",
  total_days: 3,
  time_slots: [
    {
      day: 1,
      startTime: "08:00",
      endTime: "10:00",
      block_type: "morning",
      options: [
        {
          text: "Berlin'da yerel bir kafede kahvaltı",
          description: "Yerel lezzetleri deneyimlemek isteyenler için ideal."
        },
        {
          text: "Otelde kahvaltı sonrası şehir yürüyüşü",
          description: "Rahat başlangıç; şehri tanımak isteyenler için mükemmel."
        },
        {
          text: "Berlin'nın ünlü müzelerini ziyaret",
          description: "Kültür ve sanat meraklıları için harika bir seçenek."
        },
        {
          text: "Yerel pazarları keşfetme turu",
          description: "Otantik deneyim arayanlar için eğlenceli bir başlangıç."
        }
      ]
    }
  ]
};

