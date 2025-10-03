"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Calendar, ChevronLeft, Loader2 } from "lucide-react";
import { backendApi } from "@/services/backend-api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export default function TimelinePage() {
  const search = useSearchParams();
  const router = useRouter();
  const prompt = search.get("prompt") || "";

  const [plan, setPlan] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!prompt) return;
      setIsLoading(true);
      setError(null);
      try {
        const data = await backendApi.getInteractivePlan({ prompt, language: "tr", currency: "TRY" });
        setPlan(data);
      } catch (e: any) {
        setError(e?.message || "Failed to generate plan");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [prompt]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">Timeline Plan</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={() => router.push("/")}> 
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generated from your prompt</CardTitle>
          <CardDescription className="truncate">{prompt}</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating your trip plan...
            </div>
          )}
          {error && (
            <div className="text-destructive text-sm">{error}</div>
          )}
          {!isLoading && plan && (
            <div className="space-y-6">
              <div>
                <div className="text-sm text-muted-foreground">
                  {plan.destination} • {plan.start_date} → {plan.end_date} • {plan.total_days} days
                </div>
                <p className="mt-2 text-sm">{plan.trip_summary}</p>
              </div>
              <Separator />
              {/* Timeline */}
              <div className="space-y-4">
                {plan.time_slots?.map((slot: any, idx: number) => (
                  <Card key={idx} className="border-2">
                    <CardHeader>
                      <CardTitle className="text-base">Day {slot.day} • {slot.startTime} - {slot.endTime}</CardTitle>
                      <CardDescription>Choose one of the suggested activities</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {slot.options?.map((opt: any, i: number) => (
                        <div key={i} className="p-3 rounded-lg border hover:border-primary transition-colors">
                          <div className="font-medium text-sm">{opt.text}</div>
                          {opt.description && (
                            <div className="text-xs text-muted-foreground mt-1">{opt.description}</div>
                          )}
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


