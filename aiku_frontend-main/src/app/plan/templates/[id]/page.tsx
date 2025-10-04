"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import {
  ChevronLeft,
  Heart,
  Share2,
  GitFork,
  Star,
  Clock,
  MapPin,
  DollarSign,
  Users,
  Calendar,
  Sparkles,
  Check,
} from "lucide-react";
import { templatesApi } from "@/services/api";
import type { TripTemplate } from "@/types/template";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

export default function TemplateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [template, setTemplate] = useState<TripTemplate | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [rawPlan, setRawPlan] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLiked, setIsLiked] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    loadTemplate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  async function loadTemplate() {
    setIsLoading(true);
    try {
      // Backend'den template detayını çek
      const response = await fetch(`http://localhost:4000/api/templates/${params.id}`);
      const data = await response.json();
      
      console.log('🔍 Backend Template Response:', data);
      
      if (!response.ok) {
        throw new Error(data.error || 'Template not found');
      }

      // Backend'den gelen data doğrudan template objesi olabilir
      const t = data.template || data;
      
      console.log('📦 Parsed Template:', t);
      
      // Gün sayısını hesapla - time_slots'taki unique day değerlerinden
      const uniqueDays = new Set(
        (t.plan?.time_slots || []).map((slot: { day?: number }) => slot.day).filter(Boolean)
      );
      const durationDays = uniqueDays.size > 0 ? uniqueDays.size : 
                          (t.plan?.time_slots?.length || 0);
      
      console.log('📅 Duration calculation:', {
        timeSlots: t.plan?.time_slots?.length,
        uniqueDays: Array.from(uniqueDays),
        calculatedDuration: durationDays
      });
      
      // Backend formatından frontend formatına dönüştür
      const formattedTemplate: TripTemplate = {
        id: t.id,
        title: t.title,
        description: t.description,
        destination: t.destination || 'Unknown',
        country: t.destination || 'Unknown',
        duration: durationDays,
        likes: t.likes || 0,
        rating: t.rating || 0,
        forks: 0,
        tags: t.tags || [],
        travelStyle: t.tags || [],
        bestFor: ['solo', 'couple'],
        coverImageId: Math.floor(Math.random() * 100) + 1,
        totalCost: 'moderate' as const,
        isFeatured: false,
        saves: 0,
        reviews: 0,
        isPublic: true,
        createdBy: {
          id: 'anonymous',
          name: 'Anonymous',
          avatar: `https://api.dicebear.com/7.x/avatars/svg?seed=${t.id}`,
          isVerified: false
        },
        // Plan'daki aktiviteleri parse et
        activities: (t.plan?.time_slots || []).flatMap((slot: {
          day?: number;
          startTime?: string;
          options?: Array<{
            title?: string;
            text?: string;
            description?: string;
            duration?: string;
            category?: string;
            location?: string;
            price?: number;
            booking_url?: string;
            notes?: string;
          }>;
        }) => 
          (slot.options || []).map((opt) => ({
            day: slot.day || 1,
            time: slot.startTime || '09:00',
            duration: opt.duration || '1 hour',
            title: opt.title || opt.text || 'Activity',
            description: opt.description || '',
            category: opt.category || 'other',
            location: opt.location || '',
            price: opt.price,
            bookingUrl: opt.booking_url,
            notes: opt.notes
          }))
        ),
        createdAt: t.created_at
      };
      
      // Plan verisini de state'e kaydet
      setRawPlan(t.plan);
      
      console.log('✅ Formatted Template with Plan:', formattedTemplate);
      console.log('✅ Raw Plan:', t.plan);
      console.log('🔍 Flights Check:', {
        hasFlights: !!t.plan?.flights,
        outbound: t.plan?.flights?.outbound,
        inbound: t.plan?.flights?.inbound,
        lodging: t.plan?.lodging,
        timeSlotsCount: t.plan?.time_slots?.length
      });
      
      setTemplate(formattedTemplate);
    } catch (error) {
      console.error("Failed to load template:", error);
      setTemplate(null);
    }
    setIsLoading(false);
  }

  const getCostColor = (cost?: string) => {
    switch (cost) {
      case "budget":
        return "text-green-600 bg-green-50 border-green-200";
      case "moderate":
        return "text-blue-600 bg-blue-50 border-blue-200";
      case "premium":
        return "text-purple-600 bg-purple-50 border-purple-200";
      default:
        return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  const handleFork = async () => {
    if (!template || !rawPlan) return;

    try {
      // Trip store'a kaydet ve timeline'a yönlendir
      const tripStoreData = {
        sessionId: `fork_${Date.now()}`,
        plan: rawPlan,
        prompt: template.description || template.title,
        status: 'completed'
      };
      
      // LocalStorage'a kaydet (trip-store hook bunu kullanır)
      localStorage.setItem('trip-store', JSON.stringify(tripStoreData));
      
      console.log("🔀 Forking template to timeline:", tripStoreData);
      
      // Timeline sayfasına yönlendir
      router.push('/plan/timeline');
    } catch (error) {
      console.error("Failed to fork template:", error);
      alert("Template yüklenemedi. Lütfen tekrar deneyin.");
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    alert("Link copied to clipboard!");
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!template) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <h3 className="text-lg font-semibold mb-2">Template not found</h3>
          <Button onClick={() => router.push("/plan/templates")}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            Back to Templates
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/plan/templates")}>
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back to Templates
        </Button>
      </div>

      {/* Hero Section */}
      <div className="relative h-64 sm:h-80 md:h-96 w-full rounded-2xl overflow-hidden">
        <Image
          src={`https://picsum.photos/id/${template.coverImageId}/1200/600`}
          alt={template.title}
          fill
          className="object-cover"
          priority
          sizes="100vw"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent" />

        {/* Title on Image */}
        <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-8">
          <div className="flex flex-wrap gap-2 mb-4">
            {template.isFeatured && (
              <Badge className="bg-primary text-primary-foreground">⭐ Featured</Badge>
            )}
            <Badge className={cn("font-medium border", getCostColor(template.totalCost))}>
              <DollarSign className="h-3 w-3 mr-1" />
              {template.totalCost}
            </Badge>
            <Badge variant="secondary" className="bg-white/90 backdrop-blur">
              <Clock className="h-3 w-3 mr-1" />
              {template.duration} days
            </Badge>
          </div>
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-2">
            {template.title}
          </h1>
          <p className="text-white/90 text-lg max-w-3xl">{template.description}</p>
        </div>
      </div>

      {/* Actions Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            {/* Creator & Stats */}
            <div className="flex items-center gap-6 flex-wrap">
              {/* Creator */}
              <div className="flex items-center gap-2">
                {template.createdBy.avatar && (
                  <Image
                    src={template.createdBy.avatar}
                    alt={template.createdBy.name}
                    width={40}
                    height={40}
                    className="rounded-full"
                  />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{template.createdBy.name}</span>
                    {template.createdBy.isVerified && (
                      <Badge variant="outline" className="text-xs px-1 py-0">
                        ✓ Verified
                      </Badge>
                    )}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(template.createdAt).toLocaleDateString()}
                  </div>
                </div>
              </div>

              <Separator orientation="vertical" className="h-12 hidden sm:block" />

              {/* Stats */}
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1">
                  <Heart className={cn("h-5 w-5", isLiked && "fill-red-500 text-red-500")} />
                  <span className="font-semibold">{template.likes.toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Star className="h-5 w-5 fill-amber-500 text-amber-500" />
                  <span className="font-semibold">{template.rating.toFixed(1)}</span>
                  <span className="text-muted-foreground text-sm">
                    ({template.reviews} reviews)
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <GitFork className="h-5 w-5 text-purple-500" />
                  <span className="font-semibold">{template.forks}</span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 w-full sm:w-auto">
              <Button
                variant="outline"
                onClick={async () => {
                  if (!template) return;
                  try {
                    if (isLiked) {
                      await templatesApi.unlike(template.id);
                    } else {
                      await templatesApi.like(template.id);
                    }
                    setIsLiked(!isLiked);
                  } catch (error) {
                    console.error("Failed to toggle like:", error);
                  }
                }}
                className={cn(isLiked && "border-red-500 text-red-500")}
              >
                <Heart className={cn("h-4 w-4 mr-2", isLiked && "fill-red-500")} />
                {isLiked ? "Liked" : "Like"}
              </Button>
              <Button
                variant="outline"
                onClick={() => setIsSaved(!isSaved)}
                className={cn(isSaved && "border-primary text-primary")}
              >
                {isSaved ? (
                  <Check className="h-4 w-4 mr-2" />
                ) : (
                  <Sparkles className="h-4 w-4 mr-2" />
                )}
                {isSaved ? "Saved" : "Save"}
              </Button>
              <Button variant="outline" onClick={handleShare}>
                <Share2 className="h-4 w-4 mr-2" />
                Share
              </Button>
              <Button onClick={handleFork} size="lg" className="shadow-md">
                <GitFork className="h-4 w-4 mr-2" />
                Customize This Trip
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview */}
          <Card>
            <CardHeader>
              <CardTitle>Trip Overview</CardTitle>
            </CardHeader>
            <Separator />
            <CardContent className="pt-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex items-start gap-3">
                  <MapPin className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <div className="font-semibold">Destination</div>
                    <div className="text-muted-foreground">
                      {template.destination}, {template.country}
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Clock className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <div className="font-semibold">Duration</div>
                    <div className="text-muted-foreground">{template.duration} days</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Users className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <div className="font-semibold">Best For</div>
                    <div className="text-muted-foreground capitalize">
                      {template.bestFor.join(", ")}
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <DollarSign className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <div className="font-semibold">Budget Level</div>
                    <div className="text-muted-foreground capitalize">{template.totalCost}</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Travel Style */}
          <Card>
            <CardHeader>
              <CardTitle>Travel Style</CardTitle>
              <CardDescription>What to expect from this trip</CardDescription>
            </CardHeader>
            <Separator />
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-2">
                {template.travelStyle.map((style, i) => (
                  <Badge key={i} variant="secondary" className="text-sm px-3 py-1">
                    {style}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Sample Itinerary Preview */}
          <Card>
            <CardHeader>
              <CardTitle>What&apos;s Included</CardTitle>
              <CardDescription>
                This {template.duration}-day itinerary covers all the highlights
              </CardDescription>
            </CardHeader>
            <Separator />
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                  <Calendar className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <div className="font-semibold">Day-by-Day Itinerary</div>
                    <div className="text-sm text-muted-foreground">
                      Detailed schedule for each day with timing and locations
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                  <MapPin className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <div className="font-semibold">Location Recommendations</div>
                    <div className="text-sm text-muted-foreground">
                      Restaurants, attractions, and hidden gems with addresses
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                  <Sparkles className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <div className="font-semibold">Travel Tips</div>
                    <div className="text-sm text-muted-foreground">
                      Insider advice on transportation, booking, and local customs
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Detailed Itinerary */}
          {template && rawPlan && (
            <Card>
              <CardHeader>
                <CardTitle>📅 Detailed Itinerary</CardTitle>
                <CardDescription>Day-by-day breakdown of your trip</CardDescription>
              </CardHeader>
              <Separator />
              <CardContent className="pt-6">
                <div className="space-y-6">
                  {/* Flights */}
                  {(rawPlan.flights?.outbound || rawPlan.flights?.inbound) && (
                    <div className="space-y-3">
                      <h3 className="font-semibold text-lg flex items-center gap-2">
                        ✈️ Flights
                      </h3>
                      {rawPlan.flights?.outbound && (
                        <div className="p-4 border rounded-lg bg-blue-50/50">
                          <div className="font-medium mb-2">Outbound Flight</div>
                          <div className="text-sm text-muted-foreground space-y-1">
                            {rawPlan.flights.outbound.selected?.segments?.map((seg: { fromIata: string; toIata: string; airline: string; flightNumber: string }, idx: number) => (
                              <div key={idx}>
                                {seg.fromIata} → {seg.toIata} ({seg.airline} {seg.flightNumber})
                              </div>
                            ))}
                            {rawPlan.flights.outbound.selected?.price && (
                              <div className="font-semibold text-primary mt-2">
                                Price: {rawPlan.flights.outbound.selected.currency} {rawPlan.flights.outbound.selected.price}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      {rawPlan.flights?.inbound && (
                        <div className="p-4 border rounded-lg bg-blue-50/50">
                          <div className="font-medium mb-2">Return Flight</div>
                          <div className="text-sm text-muted-foreground space-y-1">
                            {rawPlan.flights.inbound.selected?.segments?.map((seg: { fromIata: string; toIata: string; airline: string; flightNumber: string }, idx: number) => (
                              <div key={idx}>
                                {seg.fromIata} → {seg.toIata} ({seg.airline} {seg.flightNumber})
                              </div>
                            ))}
                            {rawPlan.flights.inbound.selected?.price && (
                              <div className="font-semibold text-primary mt-2">
                                Price: {rawPlan.flights.inbound.selected.currency} {rawPlan.flights.inbound.selected.price}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Hotel */}
                  {rawPlan.lodging?.selected && (
                    <div className="space-y-3">
                      <h3 className="font-semibold text-lg flex items-center gap-2">
                        🏨 Accommodation
                      </h3>
                      <div className="p-4 border rounded-lg bg-orange-50/50">
                        <div className="font-medium mb-2">
                          {rawPlan.lodging.selected.name || 'Hotel'}
                        </div>
                        <div className="text-sm text-muted-foreground space-y-1">
                          {rawPlan.lodging.selected.address && (
                            <div>📍 {rawPlan.lodging.selected.address}</div>
                          )}
                          {rawPlan.lodging.selected.checkInISO && (
                            <div>
                              📅 Check-in: {new Date(rawPlan.lodging.selected.checkInISO).toLocaleDateString()}
                            </div>
                          )}
                          {rawPlan.lodging.selected.checkOutISO && (
                            <div>
                              📅 Check-out: {new Date(rawPlan.lodging.selected.checkOutISO).toLocaleDateString()}
                            </div>
                          )}
                          {rawPlan.lodging.selected.priceTotal && (
                            <div className="font-semibold text-primary mt-2">
                              Total: {rawPlan.lodging.selected.currency} {rawPlan.lodging.selected.priceTotal}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Daily Activities */}
                  {rawPlan.time_slots && (
                    <div className="space-y-4">
                      <h3 className="font-semibold text-lg flex items-center gap-2">
                        🗓️ Daily Activities
                      </h3>
                      {Object.entries(
                        (Array.isArray(rawPlan.time_slots) ? rawPlan.time_slots : []).reduce((acc: Record<number, unknown[]>, slot: { day?: number }) => {
                          const day = slot.day || 1;
                          if (!acc[day]) acc[day] = [];
                          acc[day].push(slot);
                          return acc;
                        }, {})
                      ).map(([day, slotsGroup]: [string, unknown]) => (
                        <div key={day} className="space-y-2">
                          <div className="font-medium text-primary">Day {day}</div>
                          {(Array.isArray(slotsGroup) ? slotsGroup : []).map((slot: { 
                            startTime?: string; 
                            selected?: number;
                            options?: Array<{
                              title?: string;
                              text?: string;
                              description?: string;
                              duration?: string;
                              location?: string;
                              price?: string | number;
                            }>;
                          }, idx: number) => {
                            const activity = slot.options?.[slot.selected || 0];
                            if (!activity) return null;
                            return (
                              <div key={idx} className="p-3 border rounded-lg bg-muted/30">
                                <div className="flex justify-between items-start mb-1">
                                  <div className="font-medium">{activity.title || activity.text || 'Activity'}</div>
                                  <div className="text-xs text-muted-foreground">{slot.startTime}</div>
                                </div>
                                {activity.description && (
                                  <div className="text-sm text-muted-foreground mb-2">{activity.description}</div>
                                )}
                                <div className="flex gap-3 text-xs text-muted-foreground">
                                  {activity.duration && <span>⏱️ {activity.duration}</span>}
                                  {activity.location && <span>📍 {activity.location}</span>}
                                  {activity.price && <span>💰 {activity.price}</span>}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - CTA & Tags */}
        <div className="space-y-6">
          {/* Main CTA */}
          <Card className="border-2 border-primary/20 shadow-lg sticky top-6">
            <CardHeader>
              <CardTitle>Start Planning</CardTitle>
              <CardDescription>Customize this template for your trip</CardDescription>
            </CardHeader>
            <Separator />
            <CardContent className="pt-6 space-y-4">
              <Button onClick={handleFork} size="lg" className="w-full shadow-md">
                <GitFork className="h-5 w-5 mr-2" />
                Customize This Trip
              </Button>
              <p className="text-xs text-center text-muted-foreground">
                You can modify destinations, activities, and timing to match your preferences
              </p>
              <Separator />
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Already used by</span>
                  <span className="font-semibold">{template.forks} travelers</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Average rating</span>
                  <span className="font-semibold flex items-center gap-1">
                    <Star className="h-3 w-3 fill-amber-500 text-amber-500" />
                    {template.rating.toFixed(1)}/5.0
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tags */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Tags</CardTitle>
            </CardHeader>
            <Separator />
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-2">
                {template.tags.map((tag, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    #{tag}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
