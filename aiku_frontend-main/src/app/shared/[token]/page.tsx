"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Calendar, Users, Share2, ThumbsUp, AlertCircle, ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DraggableTimeline } from "@/components/timeline/DraggableTimeline";
import { FlightCard } from "@/components/booking/FlightCard";
import { HotelCard } from "@/components/booking/HotelCard";
import { getSharedTrip, type SharedTripResponse } from "@/services/sharing-api";

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
    outbound?: unknown;
    inbound?: unknown;
  };
  lodging?: {
    selected?: unknown;
  };
  destination?: string;
  start_date?: string;
  end_date?: string;
  total_days?: number;
  trip_summary?: string;
}

export default function SharedTripPage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sharedData, setSharedData] = useState<SharedTripResponse | null>(null);
  const [plan, setPlan] = useState<ProcessedPlan | null>(null);

  useEffect(() => {
    if (token) {
      loadSharedTrip();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const loadSharedTrip = async () => {
    if (!token) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await getSharedTrip(token);
      setSharedData(data);
      setPlan(data.trip as unknown as ProcessedPlan);
    } catch (err) {
      console.error("Failed to load shared trip:", err);
      setError(err instanceof Error ? err.message : "Failed to load trip");
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestAlternative = (timeSlotId: string) => {
    // TODO: Open suggestion modal
    console.log("Suggest alternative for slot:", timeSlotId);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin w-12 h-12 border-4 border-primary border-t-transparent rounded-full mx-auto" />
          <p className="text-muted-foreground">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !sharedData || !plan) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardHeader>
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <CardTitle>Hata</CardTitle>
            </div>
            <CardDescription>
              {error || "Gezi planı yüklenemedi"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push("/")} className="w-full">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Ana Sayfaya Dön
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { share, permissions, suggestions, pending_count } = sharedData;

  return (
    <div className="min-h-screen bg-gradient-to-b from-purple-50 via-blue-50 to-white dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={() => router.push("/")}
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Geri
          </Button>

          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold">
                  {plan.destination} Gezisi
                </h1>
                <Badge variant="secondary" className="flex items-center gap-1">
                  <Share2 className="h-3 w-3" />
                  Paylaşılan Plan
                </Badge>
              </div>
              <p className="text-muted-foreground">
                {share.owner_name} tarafından paylaşıldı
              </p>
              {plan.trip_summary && (
                <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
                  {plan.trip_summary}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="outline">
                <Users className="h-3 w-3 mr-1" />
                {share.view_count} görüntülenme
              </Badge>
              <Badge variant={permissions.can_suggest ? "default" : "secondary"}>
                {permissions.can_edit
                  ? "Düzenleme Yetkisi"
                  : permissions.can_suggest
                  ? "Öneri Yetkisi"
                  : "Görüntüleme"}
              </Badge>
            </div>
          </div>

          {/* Trip Info */}
          <div className="flex gap-4 mt-4 text-sm">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span>
                {plan.start_date} → {plan.end_date}
              </span>
            </div>
            <div>•</div>
            <div>{plan.total_days} gün</div>
          </div>

          {/* Suggestions Summary */}
          {(permissions.can_suggest || pending_count > 0) && (
            <Card className="mt-4 border-2 border-primary/20">
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <ThumbsUp className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold">Öneri Sistemi</h3>
                      <p className="text-sm text-muted-foreground">
                        {permissions.can_suggest
                          ? "Aktivitelere alternatif önerebilirsiniz"
                          : `${pending_count} bekleyen öneri var`}
                      </p>
                    </div>
                  </div>
                  {pending_count > 0 && (
                    <Badge variant="secondary" className="text-lg px-4 py-1">
                      {pending_count}
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Main Content */}
        <div className="space-y-8">
          {/* Flights */}
          {plan.flights && (plan.flights.outbound || plan.flights.inbound) && (
            <div>
              <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                ✈️ Uçuşlar
              </h2>
              <div className="grid md:grid-cols-2 gap-4">
                {plan.flights.outbound && (
                  <FlightCard flight={plan.flights.outbound as never} type="outbound" />
                )}
                {plan.flights.inbound && (
                  <FlightCard flight={plan.flights.inbound as never} type="inbound" />
                )}
              </div>
            </div>
          )}

          {/* Hotel */}
          {plan.lodging?.selected && (
            <div>
              <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                🏨 Konaklama
              </h2>
              <HotelCard hotel={plan.lodging.selected as never} />
            </div>
          )}

          {/* Timeline */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold flex items-center gap-2">
                📅 Günlük Plan
              </h2>
              {permissions.can_suggest && (
                <p className="text-sm text-muted-foreground">
                  Aktivitelere tıklayarak alternatif önerebilirsiniz
                </p>
              )}
            </div>

            <DraggableTimeline
              slots={plan.time_slots || []}
              onReorder={() => {/* Read-only */}}
              onRemove={() => {/* Read-only */}}
              onRequestAlternatives={
                permissions.can_suggest
                  ? handleSuggestAlternative
                  : () => {/* No permission */}
              }
              onTimeAdjust={() => {/* Read-only */}}
              onActivitySelect={() => {/* Read-only */}}
            />
          </div>

          {/* Pending Suggestions (for owner) */}
          {suggestions.length > 0 && (
            <div>
              <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                💡 Öneriler
              </h2>
              <div className="space-y-4">
                {suggestions
                  .filter((s) => s.status === "pending")
                  .map((suggestion) => (
                    <Card key={suggestion.id} className="border-2 border-yellow-200 dark:border-yellow-900">
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <div>
                            <CardTitle className="text-lg">
                              Day {suggestion.day} - Aktivite Önerisi
                            </CardTitle>
                            <CardDescription>
                              {suggestion.suggested_by_name} tarafından önerildi
                            </CardDescription>
                          </div>
                          <Badge variant="secondary">Beklemede</Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid md:grid-cols-2 gap-4 mb-4">
                          <div>
                            <h4 className="font-semibold text-sm text-muted-foreground mb-2">
                              Mevcut
                            </h4>
                            <Card className="bg-muted/50">
                              <CardContent className="p-3">
                                <p className="font-medium">
                                  {(suggestion.original_activity as { title?: string })?.title || "Aktivite"}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                  {(suggestion.original_activity as { description?: string })?.description}
                                </p>
                              </CardContent>
                            </Card>
                          </div>
                          <div>
                            <h4 className="font-semibold text-sm text-muted-foreground mb-2">
                              Önerilen
                            </h4>
                            <Card className="bg-primary/5 border-primary/20">
                              <CardContent className="p-3">
                                <p className="font-medium">
                                  {(suggestion.suggested_activity as { title?: string })?.title || "Aktivite"}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                  {(suggestion.suggested_activity as { description?: string })?.description}
                                </p>
                              </CardContent>
                            </Card>
                          </div>
                        </div>

                        {suggestion.reason && (
                          <div className="mb-4">
                            <h4 className="font-semibold text-sm mb-2">Neden?</h4>
                            <p className="text-sm text-muted-foreground italic">
                              &ldquo;{suggestion.reason}&rdquo;
                            </p>
                          </div>
                        )}

                        <div className="flex gap-2">
                          <Button className="flex-1">
                            Kabul Et
                          </Button>
                          <Button variant="outline" className="flex-1">
                            Reddet
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
              </div>

              {/* Accepted/Rejected Suggestions */}
              {suggestions.filter((s) => s.status !== "pending").length > 0 && (
                <div className="mt-6">
                  <h3 className="text-lg font-semibold mb-3">İncelenmiş Öneriler</h3>
                  <div className="space-y-2">
                    {suggestions
                      .filter((s) => s.status !== "pending")
                      .map((suggestion) => (
                        <Card key={suggestion.id} className="bg-muted/30">
                          <CardContent className="py-3">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium">
                                  Day {suggestion.day} - {(suggestion.suggested_activity as { title?: string })?.title}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                  {suggestion.suggested_by_name}
                                </p>
                              </div>
                              <Badge
                                variant={
                                  suggestion.status === "accepted"
                                    ? "default"
                                    : "secondary"
                                }
                              >
                                {suggestion.status === "accepted"
                                  ? "✓ Kabul Edildi"
                                  : "✗ Reddedildi"}
                              </Badge>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
