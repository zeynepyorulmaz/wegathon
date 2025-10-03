"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ChevronLeft, Loader2, Sparkles, Calendar, MapPin } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

function FullPlanContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const prompt = searchParams.get("prompt");
  const [isLoading, setIsLoading] = useState(true);
  const [plan, setPlan] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!prompt) {
      router.push("/");
      return;
    }

    fetchPlan();
  }, [prompt, router]);

  async function fetchPlan() {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:4000/api/plan/interactive", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: prompt,
          language: "tr",
          currency: "TRY",
        }),
      });

      if (!response.ok) {
        throw new Error("Plan oluşturulamadı");
      }

      const data = await response.json();
      setPlan(data);

      // Initialize selected options (default: first option for each slot)
      const defaultSelections: Record<string, number> = {};
      data.time_slots?.forEach((slot: any) => {
        const key = `${slot.day}-${slot.startTime}-${slot.endTime}`;
        defaultSelections[key] = 0; // First option selected by default
      });
      setSelectedOptions(defaultSelections);
    } catch (err) {
      console.error("Error fetching plan:", err);
      setError(err instanceof Error ? err.message : "Bir hata oluştu");
    } finally {
      setIsLoading(false);
    }
  }

  function handleOptionSelect(slotKey: string, optionIndex: number) {
    setSelectedOptions((prev) => ({
      ...prev,
      [slotKey]: optionIndex,
    }));
  }

  if (isLoading) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-3xl font-bold">Full Trip Plan</h1>
          <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
        </div>

        <Card className="border-2 border-primary/20">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 text-primary animate-spin" />
              <CardTitle>Planınız Oluşturuluyor</CardTitle>
            </div>
            <CardDescription>
              AI ekibimiz size özel bir plan hazırlıyor... (Bu 30-60 saniye sürebilir)
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-3xl font-bold">Full Trip Plan</h1>
          <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
        </div>

        <Card className="border-2 border-destructive/20">
          <CardHeader>
            <CardTitle>Hata Oluştu</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => fetchPlan()}>Tekrar Dene</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!plan) {
    return null;
  }

  // Group time slots by day
  const dayGroups = plan.time_slots?.reduce((acc: any, slot: any) => {
    if (!acc[slot.day]) {
      acc[slot.day] = [];
    }
    acc[slot.day].push(slot);
    return acc;
  }, {});

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold">
            {plan.destination} Seyahat Planı
          </h1>
          {prompt && (
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              {prompt}
            </p>
          )}
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              <Calendar className="h-3 w-3 mr-1" />
              {plan.total_days} Gün
            </Badge>
            <Badge variant="outline">{plan.time_slots?.length || 0} Zaman Dilimi</Badge>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
          <ChevronLeft className="h-4 w-4 mr-1" />
          Ana Sayfa
        </Button>
      </div>

      {/* Summary */}
      {plan.trip_summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Plan Özeti</CardTitle>
          </CardHeader>
          <Separator />
          <CardContent className="pt-4">
            <p className="text-muted-foreground leading-relaxed">{plan.trip_summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Day by Day */}
      {dayGroups &&
        Object.entries(dayGroups).map(([day, slots]: [string, any]) => (
          <Card key={day}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Gün {day}</CardTitle>
                <Badge variant="secondary">{slots.length} aktivite</Badge>
              </div>
            </CardHeader>
            <Separator />
            <CardContent className="pt-6 space-y-6">
              {slots.map((slot: any, idx: number) => {
                const slotKey = `${slot.day}-${slot.startTime}-${slot.endTime}`;
                const selectedIndex = selectedOptions[slotKey] || 0;

                return (
                  <div key={idx} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{slot.startTime}</Badge>
                        <span className="text-muted-foreground">→</span>
                        <Badge variant="outline">{slot.endTime}</Badge>
                        <Badge>{slot.block_type}</Badge>
                      </div>
                    </div>

                    {/* Options */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {slot.options?.map((option: any, optIdx: number) => (
                        <div
                          key={optIdx}
                          onClick={() => handleOptionSelect(slotKey, optIdx)}
                          className={`cursor-pointer p-4 rounded-lg border-2 transition-all ${
                            selectedIndex === optIdx
                              ? "border-primary bg-primary/5"
                              : "border-border hover:border-primary/50 hover:bg-muted/50"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <div
                              className={`mt-1 h-5 w-5 rounded-full border-2 flex items-center justify-center ${
                                selectedIndex === optIdx
                                  ? "border-primary bg-primary"
                                  : "border-border"
                              }`}
                            >
                              {selectedIndex === optIdx && (
                                <div className="h-2 w-2 bg-white rounded-full" />
                              )}
                            </div>
                            <div className="flex-1">
                              <div className="font-medium mb-1">{option.text}</div>
                              <div className="text-sm text-muted-foreground">
                                {option.description}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        ))}

      {/* Actions */}
      <Card className="border-2 border-primary/20">
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button size="lg" onClick={() => router.push("/")}>
              <MapPin className="h-4 w-4 mr-2" />
              Yeni Plan Oluştur
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => {
                console.log("Selected plan:", {
                  plan,
                  selections: selectedOptions,
                });
                alert("Plan seçimleriniz konsola yazdırıldı!");
              }}
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Planı Kaydet
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function FullPlan() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Full Trip Plan</CardTitle>
              <CardDescription>Yükleniyor...</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
              </div>
            </CardContent>
          </Card>
        </div>
      }
    >
      <FullPlanContent />
    </Suspense>
  );
}
