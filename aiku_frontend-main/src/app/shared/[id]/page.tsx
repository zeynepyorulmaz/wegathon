"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Calendar, MapPin, Clock, Users, ArrowLeft, Sparkles, Edit2, Eye, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { backendApi } from "@/services/backend-api";
import { reviewSuggestion, createSuggestion } from "@/services/sharing-api";
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
  const [processingAction, setProcessingAction] = useState<string | null>(null);
  
  // Alternative suggestion modal
  const [showAlternativeModal, setShowAlternativeModal] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState<any>(null);
  const [alternatives, setAlternatives] = useState<any[]>([]);
  const [loadingAlternatives, setLoadingAlternatives] = useState(false);
  const [selectedAlternative, setSelectedAlternative] = useState<any>(null);

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

  // Handle suggestion review (accept/reject)
  const handleReviewSuggestion = async (
    suggestionId: string, 
    action: 'accept' | 'reject'
  ) => {
    setProcessingAction(suggestionId);
    try {
      await reviewSuggestion(suggestionId, action);
      
      // Reload data to show updated suggestions
      const data = await backendApi.getSharedPlan(shareId);
      setSharedData(data);
      
      // Show success message
      alert(action === 'accept' ? '✅ Öneri kabul edildi!' : '❌ Öneri reddedildi!');
    } catch (err: any) {
      alert(err?.message || 'İşlem başarısız oldu');
    } finally {
      setProcessingAction(null);
    }
  };

  // Request alternatives for an activity
  const handleRequestAlternatives = async (activity: any, timeSlotId: string, day: number, activityIndex: number, isEditMode: boolean = false) => {
    setSelectedActivity({ ...activity, timeSlotId, day, activityIndex, isEditMode });
    setShowAlternativeModal(true);
    setLoadingAlternatives(true);
    setAlternatives([]);
    setSelectedAlternative(null);

    try {
      const tripId = sharedData.share.trip_id;
      const slot = plan.time_slots?.find((s: any) => s.id === timeSlotId);
      
      const response = await backendApi.timelineGetAlternatives({
        session_id: tripId,
        slot_id: timeSlotId,
        day: day,
        destination: plan.destination || 'destination',
        time_window: slot ? `${slot.startTime}-${slot.endTime}` : '09:00-18:00',
        exclude_ids: [activity.id],
        language: 'tr'
      });
      
      setAlternatives(response.alternatives || []);
    } catch (err: any) {
      alert(err?.message || 'Alternatifler yüklenemedi');
      setShowAlternativeModal(false);
    } finally {
      setLoadingAlternatives(false);
    }
  };

  // Submit alternative suggestion
  const handleSubmitAlternative = async () => {
    if (!selectedAlternative) {
      alert('Lütfen bir alternatif seçin');
      return;
    }

    try {
      const isEditMode = selectedActivity.isEditMode || false;

      console.log('🔍 Submitting suggestion:', {
        timeSlotId: selectedActivity.timeSlotId,
        day: selectedActivity.day,
        activityIndex: selectedActivity.activityIndex,
        isEditMode,
        originalActivity: selectedActivity.title,
        suggestedActivity: selectedAlternative.title
      });

      // Create the suggestion
      const suggestion = await createSuggestion(shareId, {
        time_slot_id: selectedActivity.timeSlotId,
        day: selectedActivity.day,
        original_activity_index: selectedActivity.activityIndex,
        original_activity: selectedActivity,
        suggested_activity: selectedAlternative,
        reason: `Alternative suggestion for ${selectedActivity.title}`,
        suggested_by_name: 'Anonymous',
        suggested_by_id: 'anonymous'
      });
      
      console.log('✅ Suggestion created:', suggestion);

      // If edit mode, auto-accept the suggestion immediately
      if (isEditMode) {
        await reviewSuggestion(suggestion.id, 'accept' as 'accept' | 'reject');
        alert('✅ Aktivite başarıyla değiştirildi!');
      } else {
        alert('✅ Öneri gönderildi!');
      }

      setShowAlternativeModal(false);
      
      // Reload to show changes
      const data = await backendApi.getSharedPlan(shareId);
      setSharedData(data);
    } catch (err: unknown) {
      const error = err as { message?: string };
      alert(error?.message || 'İşlem başarısız oldu');
    }
  };

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

  // Extract data from the response
  const plan = sharedData.trip;
  const shareInfo = sharedData.share;
  const permissions = sharedData.permissions;
  const suggestions = sharedData.suggestions || [];

  return (
    <>
      {/* Alternative Suggestion Modal */}
      {showAlternativeModal && selectedActivity && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <Card className="max-w-5xl w-full my-8">
            <CardHeader>
              <CardTitle>
                {selectedActivity.isEditMode ? 'Aktivite Değiştir' : 'Alternatif Öneri'}
              </CardTitle>
              <CardDescription>
                &quot;{selectedActivity.title}&quot; için alternatif seçenekler
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Original Activity */}
              <div>
                <h4 className="font-semibold mb-2">Mevcut Aktivite:</h4>
                <Card className="border-orange-200 bg-orange-50/30">
                  <CardContent className="pt-4">
                    <h5 className="font-semibold mb-1">{selectedActivity.title}</h5>
                    <p className="text-sm text-muted-foreground">{selectedActivity.description}</p>
                  </CardContent>
                </Card>
              </div>

              {/* Alternatives */}
              {loadingAlternatives ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center space-y-4">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto text-blue-500" />
                    <p className="text-muted-foreground">Alternatifler yükleniyor...</p>
                  </div>
                </div>
              ) : alternatives.length > 0 ? (
                <div>
                  <h4 className="font-semibold mb-2">Alternatif Seçenekler:</h4>
                  <div className="grid md:grid-cols-2 gap-4 max-h-[400px] overflow-y-auto">
                    {alternatives.map((alt: any, idx: number) => (
                      <Card
                        key={idx}
                        className={`cursor-pointer transition-all ${
                          selectedAlternative?.id === alt.id
                            ? 'border-green-500 bg-green-50 ring-2 ring-green-500'
                            : 'border-gray-200 hover:border-blue-300'
                        }`}
                        onClick={() => setSelectedAlternative(alt)}
                      >
                        <CardContent className="pt-4">
                          <div className="flex items-start justify-between mb-2">
                            <h5 className="font-semibold">{alt.title}</h5>
                            {selectedAlternative?.id === alt.id && (
                              <CheckCircle className="h-5 w-5 text-green-600" />
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{alt.description}</p>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            {alt.duration && <span>⏱️ {alt.duration}</span>}
                            {alt.price && <span>💰 {alt.price}</span>}
                            {alt.location && <span>📍 {alt.location}</span>}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  Alternatif bulunamadı
                </div>
              )}

              <div className="flex gap-2 justify-end pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowAlternativeModal(false);
                    setSelectedActivity(null);
                    setAlternatives([]);
                    setSelectedAlternative(null);
                  }}
                >
                  İptal
                </Button>
                <Button
                  onClick={handleSubmitAlternative}
                  disabled={!selectedAlternative || loadingAlternatives}
                >
                  {selectedActivity?.isEditMode ? (
                    <>
                      <Edit2 className="mr-2 h-4 w-4" />
                      Değiştir
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Öneriyi Gönder
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
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

          <div>
            <div className="flex items-center gap-2 mb-4 flex-wrap">
              <Badge variant="secondary" className="text-lg px-3 py-1">
                Paylaşılan Plan
              </Badge>
              <Badge variant="outline">
                <Users className="mr-1 h-3 w-3" />
                {shareInfo?.view_count || 0} görüntülenme
              </Badge>
              
              {/* Permission Badges */}
              {permissions?.can_view && (
                <Badge variant="outline" className="bg-blue-50">
                  <Eye className="mr-1 h-3 w-3" />
                  Görüntüleme
                </Badge>
              )}
              {permissions?.can_suggest && (
                <Badge variant="outline" className="bg-green-50">
                  <Sparkles className="mr-1 h-3 w-3" />
                  Öneri Yetkisi
                </Badge>
              )}
              {permissions?.can_edit && (
                <Badge variant="outline" className="bg-purple-50">
                  <Edit2 className="mr-1 h-3 w-3" />
                  Düzenleme Yetkisi
                </Badge>
              )}
            </div>
            <h1 className="text-3xl font-bold mb-2">
              {plan?.destination || 'Seyahat Planı'}
            </h1>
            <p className="text-muted-foreground">
              {plan?.trip_summary || 'Paylaşılan seyahat planı'}
            </p>
            {(permissions?.can_suggest || permissions?.can_edit) && (
              <p className="text-sm text-muted-foreground mt-2">
                💡 Her aktivitenin yanındaki butonları kullanarak {permissions?.can_edit ? 'düzenleme yapabilir veya' : ''} alternatif önerebilirsiniz
              </p>
            )}
          </div>
        </div>

        {/* Suggestions Summary */}
        {suggestions.length > 0 && (
          <Card className="mb-6 border-blue-200 bg-blue-50/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <Clock className="h-5 w-5 text-yellow-600" />
                    <div>
                      <p className="text-sm font-medium">{sharedData.pending_count || 0} Bekleyen</p>
                      <p className="text-xs text-muted-foreground">Öneri</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    <div>
                      <p className="text-sm font-medium">{sharedData.accepted_count || 0} Kabul</p>
                      <p className="text-xs text-muted-foreground">Edildi</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <XCircle className="h-5 w-5 text-red-600" />
                    <div>
                      <p className="text-sm font-medium">{sharedData.rejected_count || 0} Reddedildi</p>
                      <p className="text-xs text-muted-foreground">Öneri</p>
                    </div>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    // TODO: Scroll to suggestions section
                    document.getElementById('suggestions')?.scrollIntoView({ behavior: 'smooth' });
                  }}
                >
                  Önerileri Gör
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

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
                        {slot.options.map((activity: any, activityIndex: number) => (
                          <Card key={activity.id} className="border-l-4 border-l-blue-500">
                            <CardContent className="pt-4">
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
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
                                </div>

                                {/* Action Buttons Based on Permissions */}
                                <div className="flex flex-col gap-2 shrink-0">
                                  {permissions?.can_suggest && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="bg-purple-50 hover:bg-purple-100"
                                      onClick={() => handleRequestAlternatives(activity, slot.id, parseInt(day), activityIndex)}
                                    >
                                      <Sparkles className="h-4 w-4 mr-1" />
                                      Alternatif Öner
                                    </Button>
                                  )}
                                  {permissions?.can_edit && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="bg-blue-50 hover:bg-blue-100"
                                      onClick={() => handleRequestAlternatives(activity, slot.id, parseInt(day), activityIndex, true)}
                                    >
                                      <Edit2 className="h-4 w-4 mr-1" />
                                      Düzenle
                                    </Button>
                                  )}
                                </div>
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

        {/* Suggestions Section */}
        {suggestions.length > 0 && (
          <div id="suggestions" className="mt-8">
            <h2 className="text-2xl font-bold mb-4">Öneriler</h2>
            <div className="space-y-4">
              {suggestions.map((suggestion: any) => (
                <Card 
                  key={suggestion.id}
                  className={
                    suggestion.status === 'pending' 
                      ? 'border-yellow-300 bg-yellow-50/30' 
                      : suggestion.status === 'accepted'
                      ? 'border-green-300 bg-green-50/30'
                      : 'border-red-300 bg-red-50/30'
                  }
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex flex-col">
                          <CardTitle className="text-lg">
                            {suggestion.suggestion_type === 'alternative' 
                              ? '🔄 Alternatif Öneri' 
                              : suggestion.suggestion_type === 'addition'
                              ? '➕ Ekleme Önerisi'
                              : '✏️ Değişiklik Önerisi'}
                          </CardTitle>
                          <CardDescription>
                            {suggestion.suggested_by} tarafından önerildi
                          </CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            suggestion.status === 'pending'
                              ? 'default'
                              : suggestion.status === 'accepted'
                              ? 'default'
                              : 'destructive'
                          }
                          className={
                            suggestion.status === 'pending'
                              ? 'bg-yellow-500'
                              : suggestion.status === 'accepted'
                              ? 'bg-green-500'
                              : ''
                          }
                        >
                          {suggestion.status === 'pending' && '⏳ Bekliyor'}
                          {suggestion.status === 'accepted' && '✅ Kabul'}
                          {suggestion.status === 'rejected' && '❌ Red'}
                        </Badge>
                        {suggestion.status === 'pending' && permissions?.can_edit && (
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              className="bg-green-50 hover:bg-green-100"
                              disabled={processingAction === suggestion.id}
                              onClick={() => handleReviewSuggestion(suggestion.id, 'accept')}
                            >
                              <CheckCircle className="h-4 w-4 mr-1" />
                              {processingAction === suggestion.id ? 'İşleniyor...' : 'Kabul'}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="bg-red-50 hover:bg-red-100"
                              disabled={processingAction === suggestion.id}
                              onClick={() => handleReviewSuggestion(suggestion.id, 'reject')}
                            >
                              <XCircle className="h-4 w-4 mr-1" />
                              {processingAction === suggestion.id ? 'İşleniyor...' : 'Reddet'}
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {/* Side-by-side comparison for alternative suggestions */}
                    {suggestion.original_activity && suggestion.suggested_activity && (
                      <div className="grid md:grid-cols-2 gap-4 mb-4">
                        {/* Original Activity */}
                        <div>
                          <h5 className="font-semibold text-sm mb-2 text-orange-700">📍 Mevcut Aktivite:</h5>
                          <Card className="border-orange-200 bg-orange-50/30">
                            <CardContent className="p-4">
                              <div className="space-y-2">
                                <h6 className="font-bold text-sm">{suggestion.original_activity.title}</h6>
                                {suggestion.original_activity.description && (
                                  <p className="text-xs text-gray-600 line-clamp-2">{suggestion.original_activity.description}</p>
                                )}
                                <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                                  {suggestion.original_activity.duration && (
                                    <span className="flex items-center">
                                      ⏱️ {suggestion.original_activity.duration}
                                    </span>
                                  )}
                                  {suggestion.original_activity.price_level && (
                                    <span>💰 {suggestion.original_activity.price_level}</span>
                                  )}
                                </div>
                                {suggestion.original_activity.location && (
                                  <p className="text-xs text-gray-500">📍 {suggestion.original_activity.location}</p>
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        </div>

                        {/* Suggested Activity */}
                        <div>
                          <h5 className="font-semibold text-sm mb-2 text-green-700">✨ Önerilen Aktivite:</h5>
                          <Card className="border-green-200 bg-green-50/30">
                            <CardContent className="p-4">
                              <div className="space-y-2">
                                <h6 className="font-bold text-sm">{suggestion.suggested_activity.title}</h6>
                                {suggestion.suggested_activity.description && (
                                  <p className="text-xs text-gray-600 line-clamp-2">{suggestion.suggested_activity.description}</p>
                                )}
                                <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                                  {suggestion.suggested_activity.duration && (
                                    <span className="flex items-center">
                                      ⏱️ {suggestion.suggested_activity.duration}
                                    </span>
                                  )}
                                  {suggestion.suggested_activity.price_level && (
                                    <span>💰 {suggestion.suggested_activity.price_level}</span>
                                  )}
                                </div>
                                {suggestion.suggested_activity.location && (
                                  <p className="text-xs text-gray-500">📍 {suggestion.suggested_activity.location}</p>
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        </div>
                      </div>
                    )}

                    {/* Original comment/description display */}
                    {suggestion.comment && (
                      <div className="mb-4">
                        <p className="text-sm font-medium mb-1">Açıklama:</p>
                        <p className="text-sm text-muted-foreground">{suggestion.comment}</p>
                      </div>
                    )}
                    
                    {suggestion.target_activity_id && (
                      <div className="text-sm text-muted-foreground mb-2">
                        🎯 Hedef Aktivite: {suggestion.target_activity_id}
                      </div>
                    )}

                    {/* Fallback for non-alternative suggestions */}
                    {suggestion.suggested_data && suggestion.suggestion_type !== 'alternative' && (
                      <div className="bg-white rounded-lg p-4 border">
                        <p className="text-sm font-medium mb-2">Önerilen Değişiklik:</p>
                        <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
                          {JSON.stringify(suggestion.suggested_data, null, 2)}
                        </pre>
                      </div>
                    )}

                    {suggestion.reviewed_at && (
                      <div className="mt-3 pt-3 border-t text-xs text-muted-foreground">
                        {suggestion.status === 'accepted' ? '✅ Kabul edildi' : '❌ Reddedildi'} • {new Date(suggestion.reviewed_at).toLocaleDateString('tr-TR')}
                        {suggestion.review_comment && (
                          <p className="mt-1">Yorum: {suggestion.review_comment}</p>
                        )}
                      </div>
                    )}
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
    </>
  );
}
