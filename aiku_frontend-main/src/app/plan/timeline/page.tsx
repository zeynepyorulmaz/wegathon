"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Calendar, ChevronLeft, Share2, Save, Check, Copy, Link2 } from "lucide-react";
import { backendApi, type ProgressEvent } from "@/services/backend-api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { PlanLoading } from "@/components/loading/PlanLoading";
import { DraggableTimeline } from "@/components/timeline/DraggableTimeline";
import { AlternativesModal } from "@/components/timeline/AlternativesModal";
import { FlightCard } from "@/components/booking/FlightCard";
import { HotelCard } from "@/components/booking/HotelCard";

// Types
interface RawActivity {
  text?: string;
  title?: string;
  description?: string;
  duration?: number;
  price?: number;
  location?: string;
  booking_url?: string;
}

interface RawTimeSlot {
  day: number;
  startTime: string;
  endTime: string;
  options: RawActivity[];
}

interface FlightSegment {
  fromIata: string;
  toIata: string;
  departISO: string;
  arriveISO: string;
  airline: string;
  flightNumber: string;
  durationMinutes: number;
}

interface FlightOption {
  provider: string;
  price?: number;
  currency?: string;
  segments: FlightSegment[];
  baggage?: string;
  refundable?: boolean;
  bookingUrl?: string;
}

interface HotelOption {
  provider: string;
  name: string;
  address?: string;
  checkInISO: string;
  checkOutISO: string;
  priceTotal?: number;
  currency?: string;
  rating?: number;
  amenities?: string[];
  neighborhood?: string;
  bookingUrl?: string;
}

interface ProcessedPlan {
  time_slots: Array<{
    id: string;
    day: number;
    startTime: string;
    endTime: string;
    selected?: number;
    options: Array<{
      id: string;
      title: string;
      description: string;
      duration?: string;
      price?: string;
      rating?: number;
      category?: string;
      location?: string;
      booking_url?: string;
    }>;
  }>;
  flights?: {
    outbound?: FlightOption;
    inbound?: FlightOption;
  };
  lodging?: {
    selected?: HotelOption;
  };
  destination?: string;
  start_date?: string;
  end_date?: string;
  total_days?: number;
  trip_summary?: string;
  preferences?: string;
}

export default function TimelinePage() {
  const search = useSearchParams();
  const router = useRouter();
  const prompt = search.get("prompt") || "";

  const [plan, setPlan] = useState<ProcessedPlan | null>(null);
  const [sessionId, setSessionId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAlternatives, setShowAlternatives] = useState<string | null>(null);
  const [alternatives, setAlternatives] = useState<Array<{
    id: string;
    title: string;
    description: string;
    duration?: string;
    price?: string;
    rating?: number;
    category?: string;
    location?: string;
    booking_url?: string;
  }>>([]);
  const [loadingAlternatives, setLoadingAlternatives] = useState(false);
  
  // Real-time progress state
  const [progressStage, setProgressStage] = useState<string>("");
  const [progressMessage, setProgressMessage] = useState<string>("");
  const [progressPercent, setProgressPercent] = useState<number>(0);

  // Share modal state
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareUrl, setShareUrl] = useState("");
  const [shareLoading, setShareLoading] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);

  // Template modal state
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [templateTitle, setTemplateTitle] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [templateTags, setTemplateTags] = useState<string[]>([]);
  const [templateSaving, setTemplateSaving] = useState(false);

  useEffect(() => {
    async function load() {
      if (!prompt) return;
      setIsLoading(true);
      setError(null);
      setProgressStage("starting");
      setProgressMessage("Başlatılıyor...");
      setProgressPercent(0);
      
      // Generate session ID first
      const newSessionId = `session_${Date.now()}`;
      setSessionId(newSessionId);
      
      try {
        // Start SSE connection for progress
        const progressPromise = backendApi.streamPlanProgress(newSessionId, (event: ProgressEvent) => {
          setProgressStage(event.stage);
          setProgressMessage(event.message);
          
          // Update progress percentage based on stage
          const stageProgress: Record<string, number> = {
            parsing: 10,
            planning: 20,
            flights: 40,
            hotels: 60,
            weather: 70,
            itinerary: 85,
            formatting: 95,
            complete: 100,
            cache: 100
          };
          
          setProgressPercent(stageProgress[event.stage] || 0);
        });
        
        // Start plan generation with session ID
        const planPromise = backendApi.getInteractivePlan({ 
          prompt, 
          language: "tr", 
          currency: "TRY" 
        }, newSessionId);
        
        // Wait for both to complete
        await progressPromise;
        const data = await planPromise;
        
        // Debug: Check what we're receiving from backend
        console.group('🔍 Backend Response Debug');
        console.log('Full Data:', data);
        console.log('Flights:', {
          outbound: data.flights?.outbound,
          inbound: data.flights?.inbound
        });
        console.log('Lodging:', data.lodging);
        console.groupEnd();
        
        // Add unique IDs to time slots and activities
        const processedData: ProcessedPlan = {
          ...data,
          time_slots: (data.time_slots || []).map((slot: RawTimeSlot, slotIdx: number) => ({
            ...slot,
            id: `slot_${slot.day}_${slot.startTime}_${slotIdx}`,
            options: (slot.options || []).map((activity: RawActivity, actIdx: number) => ({
              ...activity,
              id: `activity_${slot.day}_${slotIdx}_${actIdx}`,
              title: activity.text || activity.title || "Activity",
              description: activity.description || "",
              duration: activity.duration ? `${activity.duration}min` : undefined,
              price: activity.price ? `$${activity.price}` : undefined
            }))
          }))
        };
        
        setPlan(processedData);
      } catch (e: unknown) {
        const err = e as Error;
        let errorMsg = err?.message || "Failed to generate plan";
        
        // Parse backend error messages
        if (errorMsg.includes("valid travel request")) {
          errorMsg = "Please enter a valid travel request. Example: 'Istanbul to Paris for 5 days'";
        } else if (errorMsg.includes("temporarily busy")) {
          errorMsg = "AI service is temporarily busy. Please try again in a few seconds.";
        } else if (errorMsg.includes("Unable to understand")) {
          errorMsg = "Unable to understand your request. Please include: origin city, destination, and dates.";
        }
        
        setError(errorMsg);
        setProgressStage("error");
        setProgressMessage(errorMsg);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [prompt]);

  // Load alternatives when slot is selected
  useEffect(() => {
    async function loadAlternatives() {
      if (!showAlternatives || !sessionId || !plan) return;
      
      // Find the slot to get day and time window info
      const slot = plan.time_slots?.find(s => s.id === showAlternatives);
      if (!slot) return;
      
      // Determine time window from startTime
      const hour = parseInt(slot.startTime.split(':')[0]);
      let timeWindow = 'morning';
      if (hour >= 12 && hour < 18) timeWindow = 'afternoon';
      else if (hour >= 18) timeWindow = 'evening';
      
      setLoadingAlternatives(true);
      try {
        const result = await backendApi.timelineGetAlternatives({
          session_id: sessionId,
          slot_id: showAlternatives,
          day: slot.day,
          destination: plan.destination || 'Unknown',
          time_window: timeWindow,
          preferences: (plan.preferences || '').split(',').filter(Boolean),
          exclude_ids: slot.options.map(opt => opt.id),
          language: 'tr'
        });
        
        // Add unique IDs to alternatives
        const processedAlternatives = (result.alternatives || []).map((activity: RawActivity, idx: number) => ({
          ...activity,
          id: `alt_${showAlternatives}_${idx}`,
          title: activity.text || activity.title || "Activity",
          description: activity.description || "",
          duration: activity.duration ? `${activity.duration}min` : undefined,
          price: activity.price ? `$${activity.price}` : undefined
        }));
        
        setAlternatives(processedAlternatives);
      } catch (e: unknown) {
        const err = e as Error;
        console.error("Failed to load alternatives:", err);
        setAlternatives([]);
      } finally {
        setLoadingAlternatives(false);
      }
    }
    
    loadAlternatives();
  }, [showAlternatives, sessionId, plan]);

  // Share plan handler
  const handleShare = async () => {
    if (!plan) return;
    
    setShareLoading(true);
    try {
      const data = await backendApi.sharePlan({
        session_id: sessionId,
        plan: plan,
        title: `${plan.destination} - ${plan.total_days} Days`,
        description: plan.trip_summary || prompt
      });

      if (data.success) {
        const fullUrl = `${window.location.origin}${data.share_url}`;
        setShareUrl(fullUrl);
        setShowShareModal(true);
      }
    } catch (error) {
      console.error("Share failed:", error);
      alert("Paylaşım başarısız oldu. Lütfen tekrar deneyin.");
    } finally {
      setShareLoading(false);
    }
  };

  // Copy share URL to clipboard
  const handleCopyLink = async () => {
    if (!shareUrl) return;
    
    try {
      await navigator.clipboard.writeText(shareUrl);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    } catch (error) {
      console.error("Copy failed:", error);
    }
  };

  // Save as template handler
  const handleSaveTemplate = async () => {
    if (!plan || !templateTitle.trim()) {
      alert("Lütfen şablon başlığı girin!");
      return;
    }

    setTemplateSaving(true);
    try {
      // Extract destination from prompt or plan
      const destination = plan.destination || 
                         prompt.split(" ").find(word => word.length > 3) || 
                         "Unknown";
      
      const response = await fetch("http://localhost:4000/api/plan/save-template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          plan: plan,
          title: templateTitle,
          description: templateDescription,
          destination: destination,
          tags: templateTags,
          is_public: true
        })
      });

      const data = await response.json();
      if (data.success) {
        alert("✅ " + data.message);
        setShowTemplateModal(false);
        setTemplateTitle("");
        setTemplateDescription("");
        setTemplateTags([]);
      }
    } catch (error) {
      console.error("Save template failed:", error);
      alert("Şablon kaydedilemedi. Lütfen tekrar deneyin.");
    } finally {
      setTemplateSaving(false);
    }
  };

  // Group activities by day and calculate time ranges
  const groupedByDay = (plan?.time_slots || []).reduce((acc, slot) => {
    if (!acc[slot.day]) {
      acc[slot.day] = [];
    }
    acc[slot.day].push(slot);
    return acc;
  }, {} as Record<number, Array<{
    id: string;
    day: number;
    startTime: string;
    endTime: string;
    options: Array<{
      id: string;
      title: string;
      description: string;
      duration?: string;
      price?: string;
      rating?: number;
      category?: string;
      location?: string;
      booking_url?: string;
    }>;
    selected?: number;
  }>>);

  // Calculate day time range
  const getDayTimeRange = (daySlots: Array<{ startTime: string; endTime: string }>) => {
    if (daySlots.length === 0) return "";
    const start = daySlots[0].startTime;
    const end = daySlots[daySlots.length - 1].endTime;
    return `${start} - ${end}`;
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">Timeline Plan</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => router.push("/plan/templates")}
            className="gap-2"
          >
            📚 View Templates
          </Button>
          <Button variant="ghost" size="sm" onClick={() => router.push("/")}> 
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generated from your prompt</CardTitle>
          <CardDescription className="truncate">{prompt}</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="space-y-4">
              <PlanLoading 
                currentStage={progressStage as "flights" | "hotels" | "itinerary"} 
                progress={progressPercent} 
              />
              <div className="text-center space-y-2">
                <p className="text-sm font-medium">{progressMessage}</p>
                <Progress value={progressPercent} className="h-2" />
                <p className="text-xs text-muted-foreground">
                  {progressStage === "flights" && "✈️ Uçuş seçenekleri aranıyor..."}
                  {progressStage === "hotels" && "🏨 Otel seçenekleri aranıyor..."}
                  {progressStage === "weather" && "🌤️ Hava durumu kontrol ediliyor..."}
                  {progressStage === "itinerary" && "📅 Gezi programı hazırlanıyor..."}
                  {progressStage === "cache" && "⚡ Önbellekten yükleniyor..."}
                </p>
              </div>
            </div>
          )}
          {error && (
            <Card className="border-destructive bg-destructive/5">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-destructive/20 flex items-center justify-center">
                    <span className="text-destructive text-xl">⚠️</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-destructive mb-1">Oops! Something went wrong</h4>
                    <p className="text-sm text-muted-foreground mb-3">{error}</p>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => window.location.reload()}>
                        Try Again
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => router.push("/")}>
                        Go Back
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          {!isLoading && plan && (
            <div className="space-y-6">
              {/* Trip Summary */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm text-muted-foreground">
                    {plan.destination} • {plan.start_date} → {plan.end_date} • {plan.total_days} days
                  </div>
                  <p className="mt-2 text-sm">{plan.trip_summary}</p>
                </div>
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleShare}
                    disabled={shareLoading}
                  >
                    <Share2 className="h-4 w-4 mr-2" />
                    {shareLoading ? "Paylaşılıyor..." : "Share"}
                  </Button>
                  <Button 
                    size="sm"
                    onClick={() => {
                      setTemplateTitle(`${plan.destination} - ${plan.total_days} Days`);
                      setTemplateDescription(plan.trip_summary || "");
                      setShowTemplateModal(true);
                    }}
                  >
                    <Save className="h-4 w-4 mr-2" />
                    Save as Template
                  </Button>
                </div>
              </div>

              {/* Flights */}
              {plan.flights && (plan.flights.outbound || plan.flights.inbound) && (
                <div className="grid md:grid-cols-2 gap-4">
                  {plan.flights.outbound && (
                    <FlightCard flight={plan.flights.outbound} type="outbound" />
                  )}
                  {plan.flights.inbound && (
                    <FlightCard flight={plan.flights.inbound} type="inbound" />
                  )}
                </div>
              )}

              {/* Hotel */}
              {plan.lodging?.selected && (
                <HotelCard hotel={plan.lodging.selected} />
              )}

              {/* Interactive Timeline with Day Grouping */}
              {Object.entries(groupedByDay).map(([day, daySlots]) => (
                <div key={`day-${day}`} className="space-y-4">
                  {/* Day Header */}
                  <div className="flex items-center gap-3 mt-6">
                    <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-full w-12 h-12 flex items-center justify-center font-bold shadow-lg">
                      Day {day}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm text-muted-foreground">
                        {getDayTimeRange(daySlots)}
                      </div>
                    </div>
                  </div>
                  
                  {/* Day Activities */}
                  <DraggableTimeline
                    slots={daySlots}
                    onReorder={async (from, to, idx) => {
                  try {
                    await backendApi.timelineReorder({
                      session_id: sessionId,
                      from_slot: from,
                      to_slot: to,
                      activity_index: idx,
                    });
                    // Optimistic update
                    const updatedPlan = { ...plan };
                    // TODO: Update local state based on response
                    setPlan(updatedPlan);
                  } catch (e: unknown) {
                    const err = e as Error;
                    console.error("Reorder failed:", err);
                  }
                }}
                onRemove={async (slotId, idx) => {
                  try {
                    // Find slot to get day number
                    const slot = plan.time_slots?.find((s: { id: string }) => s.id === slotId);
                    if (!slot) return;

                    await backendApi.timelineRemove({
                      session_id: sessionId,
                      slot_id: slotId,
                      day: slot.day,
                      activity_index: idx,
                    });
                    
                    // Optimistic update
                    const updatedPlan = { ...plan };
                    const updatedSlot = updatedPlan.time_slots?.find((s: { id: string }) => s.id === slotId);
                    if (updatedSlot && updatedSlot.options) {
                      updatedSlot.options.splice(idx, 1);
                      setPlan(updatedPlan);
                    }
                  } catch (e: unknown) {
                    const err = e as Error;
                    console.error("Remove failed:", err);
                  }
                }}
                onRequestAlternatives={(slotId) => {
                  setShowAlternatives(slotId);
                }}
                onTimeAdjust={async (slotId, start, end) => {
                  try {
                    await backendApi.timelineUpdateTime({
                      session_id: sessionId,
                      slot_id: slotId,
                      new_start_time: start,
                      new_end_time: end,
                    });
                    // Optimistic update
                    const updatedPlan = { ...plan };
                    const slot = updatedPlan.time_slots?.find((s: { id: string }) => s.id === slotId);
                    if (slot) {
                      slot.startTime = start;
                      slot.endTime = end;
                      setPlan(updatedPlan);
                    }
                  } catch (e: unknown) {
                    const err = e as Error;
                    console.error("Time adjust failed:", err);
                  }
                }}
                onActivitySelect={(slotId, idx) => {
                  const updatedPlan = { ...plan };
                  const slot = updatedPlan.time_slots?.find((s: { id: string }) => s.id === slotId);
                  if (slot) {
                    slot.selected = idx;
                    setPlan(updatedPlan);
                  }
                }}
              />
                </div>
              ))}

              {/* Share Modal */}
              {showShareModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                  <Card className="w-full max-w-md">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Share2 className="h-5 w-5 text-blue-500" />
                        Plan Paylaşıldı! 🎉
                      </CardTitle>
                      <CardDescription>
                        Planınız başarıyla paylaşıldı. Bu linki herkesle paylaşabilirsiniz.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                        <input
                          type="text"
                          value={shareUrl}
                          readOnly
                          className="flex-1 bg-transparent outline-none text-sm"
                        />
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={handleCopyLink}
                        >
                          {shareCopied ? (
                            <>
                              <Check className="h-4 w-4 mr-1 text-green-500" />
                              Kopyalandı!
                            </>
                          ) : (
                            <>
                              <Copy className="h-4 w-4 mr-1" />
                              Kopyala
                            </>
                          )}
                        </Button>
                      </div>
                      
                      <div className="flex gap-2">
                        <Button
                          className="flex-1"
                          onClick={() => window.open(shareUrl, '_blank')}
                        >
                          <Link2 className="h-4 w-4 mr-2" />
                          Önizleme
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => setShowShareModal(false)}
                        >
                          Kapat
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Save as Template Modal */}
              {showTemplateModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                  <Card className="w-full max-w-md">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Save className="h-5 w-5 text-purple-500" />
                        Şablon Olarak Kaydet
                      </CardTitle>
                      <CardDescription>
                        Bu planı şablon olarak kaydedin ve gelecekte tekrar kullanın.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Şablon Başlığı *</label>
                        <input
                          type="text"
                          value={templateTitle}
                          onChange={(e) => setTemplateTitle(e.target.value)}
                          placeholder="ör: 3 Günlük Roma Kültür Turu"
                          className="w-full px-3 py-2 border rounded-lg outline-none focus:ring-2 focus:ring-purple-500"
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium">Açıklama</label>
                        <textarea
                          value={templateDescription}
                          onChange={(e) => setTemplateDescription(e.target.value)}
                          placeholder="Şablon hakkında kısa bir açıklama..."
                          rows={3}
                          className="w-full px-3 py-2 border rounded-lg outline-none focus:ring-2 focus:ring-purple-500"
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium">Etiketler</label>
                        <input
                          type="text"
                          placeholder="kültür, sanat, tarih (virgülle ayırın)"
                          onChange={(e) => setTemplateTags(e.target.value.split(',').map(t => t.trim()).filter(Boolean))}
                          className="w-full px-3 py-2 border rounded-lg outline-none focus:ring-2 focus:ring-purple-500"
                        />
                      </div>

                      <div className="flex gap-2 pt-2">
                        <Button
                          className="flex-1"
                          onClick={handleSaveTemplate}
                          disabled={templateSaving || !templateTitle.trim()}
                        >
                          {templateSaving ? "Kaydediliyor..." : "Kaydet"}
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setShowTemplateModal(false);
                            setTemplateTitle("");
                            setTemplateDescription("");
                            setTemplateTags([]);
                          }}
                        >
                          İptal
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Alternatives Modal */}
              <AlternativesModal
                isOpen={!!showAlternatives}
                onClose={() => {
                  setShowAlternatives(null);
                  setAlternatives([]);
                }}
                alternatives={alternatives}
                currentActivity={
                  showAlternatives 
                    ? plan.time_slots?.find((s: { id: string }) => s.id === showAlternatives)?.options?.[0]
                    : undefined
                }
                onSelect={async (activity) => {
                  if (!showAlternatives) return;
                  
                  // Update local state
                  const updatedPlan = { ...plan };
                  const slot = updatedPlan.time_slots?.find((s: { id: string }) => s.id === showAlternatives);
                  if (slot && slot.options) {
                    slot.options = [activity, ...slot.options];
                    slot.selected = 0;
                    setPlan(updatedPlan);
                  }
                }}
                isLoading={loadingAlternatives}
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


