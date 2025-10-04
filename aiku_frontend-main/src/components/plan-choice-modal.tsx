"use client";

import { Layers, Library, X, Calendar } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

type Mode = "chat" | "step" | "templates" | "timeline";

interface PlanChoiceModalProps {
  onClose: () => void;
  onChoose: (mode: Mode) => void;
}

export function PlanChoiceModal({ onClose, onChoose }: PlanChoiceModalProps) {
  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 z-50 animate-in fade-in duration-300"
      role="dialog"
      aria-modal="true"
      aria-labelledby="plan-choice-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-6xl animate-in zoom-in-95 duration-300"
        role="document"
        onClick={(e) => e.stopPropagation()}
      >
        <Card className="border-2 shadow-2xl">
          <CardHeader className="relative">
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-2 sm:right-4 top-2 sm:top-4"
              onClick={onClose}
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </Button>
            <CardTitle id="plan-choice-title" className="text-xl sm:text-2xl pr-10">
              Choose Your Planning Style
            </CardTitle>
            <CardDescription className="text-sm sm:text-base">
              Select the approach that works best for you
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* 3 Options */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {/* AI Chat Option */}
              <Card
                className="cursor-pointer transition-all duration-300 hover:shadow-xl hover:scale-[1.02] hover:border-primary border-2 group"
                onClick={() => onChoose("chat" as Mode)}
              >
                <CardHeader className="space-y-3 pb-3">
                  <div className="flex flex-col items-center text-center gap-3">
                    <div className="h-16 w-16 rounded-xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                      <Layers className="h-8 w-8 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-lg mb-1">AI Chat</CardTitle>
                      <Badge variant="default" className="text-xs">
                        ✨ Recommended
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
                  <CardDescription className="text-sm leading-relaxed text-center">
                    Chat with AI to create your perfect trip - it asks, you answer!
                  </CardDescription>
                  <div className="space-y-2">
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-primary font-bold">✓</span>
                      <span>Guided conversation</span>
                    </div>
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-primary font-bold">✓</span>
                      <span>Real flights & hotels</span>
                    </div>
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-primary font-bold">✓</span>
                      <span>Easy to customize</span>
                    </div>
                  </div>
                  <Button className="w-full mt-4" size="sm">
                    <Layers className="h-4 w-4 mr-2" />
                    Start Chat
                  </Button>
                </CardContent>
              </Card>
              {/* Timeline Plan Option */}
              <Card
                className="cursor-pointer transition-all duration-300 hover:shadow-xl hover:scale-[1.02] hover:border-blue-200 border-2 group relative overflow-hidden"
                onClick={() => onChoose("timeline" as Mode)}
              >
                <CardHeader className="space-y-3 pb-3">
                  <div className="flex flex-col items-center text-center gap-3">
                    <div className="h-16 w-16 rounded-xl bg-blue-200/20 flex items-center justify-center group-hover:bg-blue-200/30 transition-colors">
                      <Calendar className="h-8 w-8 text-blue-300" />
                    </div>
                    <div>
                      <CardTitle className="text-lg mb-1">Timeline Plan</CardTitle>
                      <Badge variant="default" className="text-xs bg-blue-300">
                        Throughout Trip
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
                  <CardDescription className="text-sm leading-relaxed text-center">
                    Create a full trip plan from your prompt and view it as a timeline
                  </CardDescription>
                  <div className="space-y-2">
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-blue-300 font-bold">✓</span>
                      <span>Real flights & hotels</span>
                    </div>
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-blue-300 font-bold">✓</span>
                      <span>Day-by-day timeline</span>
                    </div>
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-blue-300 font-bold">✓</span>
                      <span>Drag & drop activities</span>
                    </div>
                  </div>
                  <Button className="w-full mt-4 bg-blue-300 hover:bg-blue-400" size="sm">
                    <Calendar className="h-4 w-4 mr-2" />
                    Generate Timeline
                  </Button>
                </CardContent>
              </Card>
              {/* Step by Step Option */}
              {/* <Card
                className="cursor-pointer transition-all duration-300 hover:shadow-xl hover:scale-[1.02] hover:border-primary border-2 group"
                onClick={() => onChoose("step")}
              >
                <CardHeader className="space-y-3 pb-3">
                  <div className="flex flex-col items-center text-center gap-3">
                    <div className="h-16 w-16 rounded-xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                      <Layers className="h-8 w-8 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-lg mb-1">Step by Step</CardTitle>
                      <Badge variant="secondary" className="text-xs">
                        Most Popular
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
                  <CardDescription className="text-sm leading-relaxed text-center">
                    Answer guided questions to build your perfect itinerary
                  </CardDescription>
                  <div className="space-y-2">
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-primary font-bold">✓</span>
                      <span>Interactive questionnaire</span>
                    </div>
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-primary font-bold">✓</span>
                      <span>Visual timeline</span>
                    </div>
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-primary font-bold">✓</span>
                      <span>Full control</span>
                    </div>
                  </div>
                  <Button className="w-full mt-4" size="sm">
                    <Layers className="h-4 w-4 mr-2" />
                    Start Planning
                  </Button>
                </CardContent>
              </Card> */}

              {/* Browse Templates Option */}
              <Card
                className="cursor-pointer transition-all duration-300 hover:shadow-xl hover:scale-[1.02] hover:border-primary border-2 group relative overflow-hidden"
                onClick={() => onChoose("templates")}
              >
              
                <CardHeader className="space-y-3 pb-3">
                  <div className="flex flex-col items-center text-center gap-3">
                    <div className="h-16 w-16 rounded-xl bg-purple-500/10 flex items-center justify-center group-hover:bg-purple-500/20 transition-colors">
                      <Library className="h-8 w-8 text-purple-600" />
                    </div>
                    <div>
                      <CardTitle className="text-lg mb-1">Browse Templates</CardTitle>
                      <Badge variant="outline" className="text-xs">
                        Community
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
                  <CardDescription className="text-sm leading-relaxed text-center">
                    Explore trips shared by other travelers and customize them
                  </CardDescription>
                  <div className="space-y-2">
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-purple-600 font-bold">✓</span>
                      <span>Real traveler experiences</span>
                    </div>
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-purple-600 font-bold">✓</span>
                      <span>Customize any template</span>
                    </div>
                    <div className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="text-purple-600 font-bold">✓</span>
                      <span>Save time planning</span>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    className="w-full mt-4 border-purple-200 hover:bg-purple-50"
                    size="sm"
                  >
                    <Library className="h-4 w-4 mr-2" />
                    Browse Templates
                  </Button>
                </CardContent>
              </Card>
            </div>

            <p className="text-center text-sm text-muted-foreground pt-6">
              You can switch between modes anytime during planning
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
