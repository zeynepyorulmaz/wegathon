"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Send, Sparkles, Loader2, Plane, Hotel, Calendar } from "lucide-react";
import { backendApi, type ChatResponse } from "@/services/backend-api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function ChatPlanPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPlan, setCurrentPlan] = useState<any>(null);
  const [collectedData, setCollectedData] = useState<Record<string, any>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      let response: ChatResponse;

      if (!sessionId) {
        // Start new conversation
        response = await backendApi.chatStart({
          initial_message: input,
          language: "tr",
          currency: "TRY",
        });
        setSessionId(response.session_id);
      } else {
        // Continue conversation
        response = await backendApi.chatContinue({
          session_id: sessionId,
          message: input,
        });
      }

      // Add AI response
      const aiMessage: Message = {
        role: "assistant",
        content: response.message,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);

      // Update state
      setCollectedData(response.collected_data);
      if (response.plan) {
        setCurrentPlan(response.plan);
      }
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: `❌ Üzgünüm, bir hata oluştu: ${error instanceof Error ? error.message : "Bilinmeyen hata"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyPress(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-primary" />
            AI Travel Chat
          </h1>
          <p className="text-muted-foreground">
            Konuşarak seyahat planınızı oluşturun - AI size yol gösterecek!
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
          <ChevronLeft className="h-4 w-4 mr-1" />
          Ana Sayfa
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Area */}
        <div className="lg:col-span-2">
          <Card className="h-[600px] flex flex-col">
            <CardHeader>
              <CardTitle>Sohbet</CardTitle>
              <CardDescription>
                {sessionId
                  ? "Planınızı oluşturmak için soruları yanıtlayın"
                  : "Seyahatinizi anlatarak başlayın"}
              </CardDescription>
            </CardHeader>
            <Separator />

            {/* Messages */}
            <CardContent className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.length === 0 && (
                <div className="flex items-center justify-center h-full text-center">
                  <div className="space-y-4">
                    <Sparkles className="h-12 w-12 text-primary mx-auto" />
                    <div>
                      <h3 className="font-semibold text-lg mb-2">Seyahatinizi Planlayalım!</h3>
                      <p className="text-sm text-muted-foreground max-w-md">
                        "Berlin'e gitmek istiyorum" gibi bir mesajla başlayın.<br />
                        AI size rehberlik edecek ve mükemmel planınızı oluşturacak!
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-3 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                    <div
                      className={`text-xs mt-1 ${
                        message.role === "user" ? "text-primary-foreground/70" : "text-muted-foreground"
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString("tr-TR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-lg px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-sm">AI düşünüyor...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </CardContent>

            {/* Input */}
            <div className="p-4 border-t">
              <div className="flex gap-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Mesajınızı yazın... (Enter ile gönder)"
                  className="flex-1 min-h-[60px] max-h-[120px] resize-none px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                  disabled={isLoading}
                />
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  size="lg"
                  className="h-[60px] px-6"
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar - Info & Plan */}
        <div className="space-y-4">
          {/* Collected Data */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Toplanan Bilgiler</CardTitle>
            </CardHeader>
            <Separator />
            <CardContent className="pt-4 space-y-2 text-sm">
              {Object.keys(collectedData).length === 0 ? (
                <p className="text-muted-foreground text-center py-4">
                  Henüz bilgi toplanmadı
                </p>
              ) : (
                <>
                  {collectedData.destination && (
                    <div className="flex items-center gap-2">
                      <Plane className="h-4 w-4 text-primary" />
                      <span className="font-medium">Hedef:</span>
                      <span>{collectedData.destination}</span>
                    </div>
                  )}
                  {collectedData.origin && (
                    <div className="flex items-center gap-2">
                      <Plane className="h-4 w-4 text-primary rotate-180" />
                      <span className="font-medium">Nereden:</span>
                      <span>{collectedData.origin}</span>
                    </div>
                  )}
                  {collectedData.start_date && (
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-primary" />
                      <span className="font-medium">Tarih:</span>
                      <span>{collectedData.start_date}</span>
                    </div>
                  )}
                  {collectedData.end_date && (
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-primary" />
                      <span className="font-medium">Dönüş:</span>
                      <span>{collectedData.end_date}</span>
                    </div>
                  )}
                  {collectedData.adults && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium">👥 Yolcular:</span>
                      <span>
                        {collectedData.adults} yetişkin
                        {collectedData.children > 0 && `, ${collectedData.children} çocuk`}
                      </span>
                    </div>
                  )}
                  {collectedData.preferences && collectedData.preferences.length > 0 && (
                    <div className="pt-2">
                      <span className="font-medium block mb-1">🎯 Tercihler:</span>
                      <div className="flex flex-wrap gap-1">
                        {collectedData.preferences.map((pref: string, i: number) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {pref}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Current Plan */}
          {currentPlan && (
            <Card className="border-2 border-primary/20">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  ✅ Plan Hazır!
                </CardTitle>
              </CardHeader>
              <Separator />
              <CardContent className="pt-4 space-y-3">
                {/* Flight */}
                {currentPlan.flights?.outbound && (
                  <div className="p-3 bg-muted rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Plane className="h-4 w-4 text-primary" />
                      <span className="font-medium text-sm">Uçuş</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {currentPlan.flights.outbound.segments?.[0]?.airline}{" "}
                      {currentPlan.flights.outbound.segments?.[0]?.flightNumber}
                    </div>
                    <div className="text-sm font-semibold text-primary mt-1">
                      {currentPlan.flights.outbound.price} {currentPlan.flights.outbound.currency}
                    </div>
                  </div>
                )}

                {/* Hotel */}
                {currentPlan.lodging?.selected?.name && (
                  <div className="p-3 bg-muted rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Hotel className="h-4 w-4 text-primary" />
                      <span className="font-medium text-sm">Otel</span>
                    </div>
                    <div className="text-xs">{currentPlan.lodging.selected.name}</div>
                    <div className="text-sm font-semibold text-primary mt-1">
                      {currentPlan.lodging.selected.priceTotal}{" "}
                      {currentPlan.lodging.selected.currency}
                    </div>
                  </div>
                )}

                {/* Total */}
                {currentPlan.pricing?.totalEstimated && (
                  <div className="pt-2 border-t">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold">Toplam:</span>
                      <span className="text-lg font-bold text-primary">
                        {currentPlan.pricing.totalEstimated.toFixed(0)}{" "}
                        {currentPlan.pricing.currency}
                      </span>
                    </div>
                  </div>
                )}

                <Button
                  className="w-full"
                  onClick={() => {
                    // TODO: Navigate to full plan view
                    console.log("View full plan:", currentPlan);
                  }}
                >
                  Planın Tamamını Gör
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hızlı Mesajlar</CardTitle>
            </CardHeader>
            <Separator />
            <CardContent className="pt-4 space-y-2">
              {!sessionId ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => setInput("Berlin'e gitmek istiyorum")}
                  >
                    Berlin'e gitmek istiyorum
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => setInput("Paris romantik tatil")}
                  >
                    Paris romantik tatil
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => setInput("Tokyo 5 gün")}
                  >
                    Tokyo 5 gün
                  </Button>
                </>
              ) : (
                <>
                  {currentPlan && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => setInput("uçuşu değiştir")}
                      >
                        ✈️ Uçuşu değiştir
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => setInput("oteli değiştir")}
                      >
                        🏨 Oteli değiştir
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => setInput("2. günü daha rahat yap")}
                      >
                        🗓️ 2. günü rahatlatı
                      </Button>
                    </>
                  )}
                  {!currentPlan && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => setInput("3 gün")}
                      >
                        3 gün
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => setInput("2 kişi")}
                      >
                        2 kişi
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => setInput("20 Kasım")}
                      >
                        20 Kasım
                      </Button>
                    </>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

