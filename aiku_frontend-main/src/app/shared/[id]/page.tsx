"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Calendar, MapPin, Clock, Users, ArrowLeft } from "lucide-react";
import { backendApi } from "@/services/backend-api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FlightCard } from "@/components/booking/FlightCard";
import { HotelCard } from "@/components/booking/HotelCard";

export default function SharedPlanPage() {
  const params = useParams();
  const router = useRouter();
  const shareId = params?.id as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sharedData, setSharedData] = useState<any>(null);

  useEffect(() => {
    async function loadSharedPlan() {
      if (!shareId) return;

      try {
        const data = await backendApi.getSharedPlan(shareId);
        setSharedData(data);
      } catch (err: any) {
        setError(err?.message || "Plan bulunamadı");
      } finally {
        setLoading(false);
      }
    }

    loadSharedPlan();
  }, [shareId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground">Plan yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !sharedData) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardHeader>
            <CardTitle className="text-destructive">Plan Bulunamadı</CardTitle>
            <CardDescription>{error || "Bu plan artık mevcut değil."}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push("/")} className="w-full">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Ana Sayfaya Dön
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const plan = sharedData.plan;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/")}
            className="mb-4"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Kendi planını oluştur
          </Button>

          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <Badge variant="secondary" className="text-lg px-3 py-1">
                  Paylaşılan Plan
                </Badge>
                <Badge variant="outline">
                  <Users className="mr-1 h-3 w-3" />
                  {sharedData.views} görüntülenme
                </Badge>
              </div>
              <h1 className="text-3xl font-bold mb-2">{sharedData.title}</h1>
              <p className="text-muted-foreground">{sharedData.description}</p>
            </div>
          </div>
        </div>

        {/* Trip Info Card */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="grid md:grid-cols-3 gap-6">
              <div className="flex items-start gap-3">
                <MapPin className="h-5 w-5 text-blue-500 mt-1" />
                <div>
                  <p className="text-sm text-muted-foreground">Destination</p>
                  <p className="font-semibold">{plan.destination}</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Calendar className="h-5 w-5 text-purple-500 mt-1" />
                <div>
                  <p className="text-sm text-muted-foreground">Dates</p>
                  <p className="font-semibold">
                    {plan.start_date} → {plan.end_date}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Clock className="h-5 w-5 text-green-500 mt-1" />
                <div>
                  <p className="text-sm text-muted-foreground">Duration</p>
                  <p className="font-semibold">{plan.total_days} Days</p>
                </div>
              </div>
            </div>
            {plan.trip_summary && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-sm">{plan.trip_summary}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Flights */}
        {plan.flights && (plan.flights.outbound || plan.flights.inbound) && (
          <div className="mb-6">
            <h2 className="text-xl font-bold mb-4">Flights</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {plan.flights.outbound && (
                <FlightCard flight={plan.flights.outbound} type="outbound" />
              )}
              {plan.flights.inbound && (
                <FlightCard flight={plan.flights.inbound} type="inbound" />
              )}
            </div>
          </div>
        )}

        {/* Hotel */}
        {plan.lodging?.selected && (
          <div className="mb-6">
            <h2 className="text-xl font-bold mb-4">Accommodation</h2>
            <HotelCard hotel={plan.lodging.selected} />
          </div>
        )}

        {/* Itinerary */}
        {plan.time_slots && plan.time_slots.length > 0 && (
          <div>
            <h2 className="text-xl font-bold mb-4">Day-by-Day Itinerary</h2>
            <div className="space-y-6">
              {Object.entries(
                plan.time_slots.reduce((acc: any, slot: any) => {
                  if (!acc[slot.day]) acc[slot.day] = [];
                  acc[slot.day].push(slot);
                  return acc;
                }, {})
              ).map(([day, slots]: [string, any]) => (
                <Card key={`day-${day}`}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-3">
                      <div className="bg-gradient-to-br from-blue-500 to-purple-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold">
                        {day}
                      </div>
                      Day {day}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {slots.map((slot: any) => (
                      <div key={slot.id} className="space-y-2">
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Clock className="h-4 w-4" />
                          {slot.startTime} - {slot.endTime}
                        </div>
                        {slot.options.map((activity: any) => (
                          <Card key={activity.id} className="border-l-4 border-l-blue-500">
                            <CardContent className="pt-4">
                              <h4 className="font-semibold mb-1">{activity.title}</h4>
                              <p className="text-sm text-muted-foreground mb-2">
                                {activity.description}
                              </p>
                              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                {activity.duration && (
                                  <span>⏱️ {activity.duration}</span>
                                )}
                                {activity.price && <span>💰 {activity.price}</span>}
                                {activity.location && (
                                  <span>📍 {activity.location}</span>
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* CTA */}
        <Card className="mt-8 bg-gradient-to-r from-blue-500 to-purple-600 text-white">
          <CardContent className="pt-6 text-center">
            <h3 className="text-xl font-bold mb-2">Bu planı beğendin mi?</h3>
            <p className="mb-4 opacity-90">
              Kendi seyahat planını oluşturmak için AI destekli planlayıcımızı kullan!
            </p>
            <Button
              size="lg"
              variant="secondary"
              onClick={() => router.push("/")}
            >
              Kendi Planını Oluştur
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
