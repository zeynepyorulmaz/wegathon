"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronLeft, ChevronRight, Check, MapPin, Clock, DollarSign, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity } from "@/components/timeline/DraggableTimeline";

interface AlternativesModalProps {
  isOpen: boolean;
  onClose: () => void;
  alternatives: Activity[];
  currentActivities?: Activity[]; // All activities in the slot
  onSelect: (activity: Activity, replaceIndex: number) => void;
  isLoading?: boolean;
}

export function AlternativesModal({
  isOpen,
  onClose,
  alternatives,
  currentActivities = [],
  onSelect,
  isLoading = false,
}: AlternativesModalProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedReplaceIndex, setSelectedReplaceIndex] = useState<number | null>(null);
  const [step, setStep] = useState<'select-activity' | 'select-alternative'>('select-activity');

  if (!isOpen) return null;

  const currentAlternative = alternatives[currentIndex];
  const hasAlternatives = alternatives.length > 0;
  const hasMultipleActivities = currentActivities.length > 1;

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : alternatives.length - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < alternatives.length - 1 ? prev + 1 : 0));
  };

  const handleActivitySelect = (index: number) => {
    setSelectedReplaceIndex(index);
    setStep('select-alternative');
  };

  const handleAlternativeSelect = () => {
    if (currentAlternative && selectedReplaceIndex !== null) {
      onSelect(currentAlternative, selectedReplaceIndex);
      onClose();
      // Reset state for next time
      setStep('select-activity');
      setSelectedReplaceIndex(null);
      setCurrentIndex(0);
    }
  };

  const handleBack = () => {
    setStep('select-activity');
    setSelectedReplaceIndex(null);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="relative w-full max-w-3xl"
          onClick={(e) => e.stopPropagation()}
        >
          <Card className="border-2">
            <div className="flex items-center justify-between p-4 border-b">
              <div className="flex items-center gap-3">
                {step === 'select-alternative' && (
                  <Button variant="ghost" size="icon" onClick={handleBack}>
                    <ChevronLeft className="h-5 w-5" />
                  </Button>
                )}
                <div>
                  <h3 className="text-lg font-semibold">
                    {step === 'select-activity' 
                      ? 'Hangi Aktiviteyi Değiştirmek İstiyorsunuz?' 
                      : 'Alternatif Seçin'}
                  </h3>
                  {step === 'select-alternative' && selectedReplaceIndex !== null && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Değiştirilecek: <span className="font-medium text-foreground">{currentActivities[selectedReplaceIndex]?.title}</span>
                    </p>
                  )}
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="h-5 w-5" />
              </Button>
            </div>

            <CardContent className="p-6">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                    className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full"
                  />
                  <p className="mt-4 text-muted-foreground">Finding alternatives...</p>
                </div>
              ) : step === 'select-activity' ? (
                /* Step 1: Select which activity to replace */
                <div className="space-y-3">
                  {currentActivities.map((activity, index) => (
                    <Card 
                      key={index}
                      className="border-2 hover:border-primary/50 cursor-pointer transition-all"
                      onClick={() => handleActivitySelect(index)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-semibold mb-1">{activity.title}</h4>
                            {activity.description && (
                              <p className="text-sm text-muted-foreground line-clamp-2">{activity.description}</p>
                            )}
                            <div className="flex items-center gap-4 mt-2">
                              {activity.duration && (
                                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                  <Clock className="h-3 w-3" />
                                  <span>{activity.duration}</span>
                                </div>
                              )}
                              {activity.price && (
                                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                  <DollarSign className="h-3 w-3" />
                                  <span>{activity.price}</span>
                                </div>
                              )}
                            </div>
                          </div>
                          {activity.category && (
                            <Badge variant="secondary" className="ml-2">
                              {activity.category}
                            </Badge>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : !hasAlternatives ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground">No alternatives available</p>
                </div>
              ) : (
                <>
                  {/* Carousel */}
                  <div className="relative min-h-[300px]">
                    <AnimatePresence mode="wait">
                      <motion.div
                        key={currentIndex}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.2 }}
                      >
                        <Card className="border-2 border-primary/20">
                          <CardContent className="p-6">
                            {/* Header */}
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex-1">
                                <h4 className="text-xl font-semibold mb-2">{currentAlternative.title}</h4>
                                {currentAlternative.category && (
                                  <Badge variant="secondary" className="mb-2">
                                    {currentAlternative.category}
                                  </Badge>
                                )}
                              </div>
                              {currentAlternative.rating && (
                                <div className="flex items-center gap-1 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded">
                                  <Star className="h-4 w-4 fill-amber-500 text-amber-500" />
                                  <span className="font-medium">{currentAlternative.rating.toFixed(1)}</span>
                                </div>
                              )}
                            </div>

                            {/* Description */}
                            <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                              {currentAlternative.description}
                            </p>

                            {/* Metadata */}
                            <div className="grid grid-cols-2 gap-4 mb-4">
                              {currentAlternative.duration && (
                                <div className="flex items-center gap-2 text-sm">
                                  <Clock className="h-4 w-4 text-muted-foreground" />
                                  <span>{currentAlternative.duration}</span>
                                </div>
                              )}
                              {currentAlternative.price && (
                                <div className="flex items-center gap-2 text-sm">
                                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                                  <span>{currentAlternative.price}</span>
                                </div>
                              )}
                              {currentAlternative.location && (
                                <div className="flex items-center gap-2 text-sm col-span-2">
                                  <MapPin className="h-4 w-4 text-muted-foreground" />
                                  <span className="text-muted-foreground">{currentAlternative.location}</span>
                                </div>
                              )}
                            </div>

                            {/* Booking URL */}
                            {currentAlternative.booking_url && (
                              <a
                                href={currentAlternative.booking_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-primary hover:underline"
                              >
                                View booking details →
                              </a>
                            )}
                          </CardContent>
                        </Card>
                      </motion.div>
                    </AnimatePresence>

                    {/* Navigation Arrows */}
                    {alternatives.length > 1 && (
                      <>
                        <Button
                          variant="outline"
                          size="icon"
                          className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 rounded-full shadow-lg"
                          onClick={handlePrevious}
                        >
                          <ChevronLeft className="h-5 w-5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 rounded-full shadow-lg"
                          onClick={handleNext}
                        >
                          <ChevronRight className="h-5 w-5" />
                        </Button>
                      </>
                    )}
                  </div>

                  {/* Indicators */}
                  {alternatives.length > 1 && (
                    <div className="flex justify-center gap-2 mt-6">
                      {alternatives.map((_, index) => (
                        <button
                          key={index}
                          onClick={() => setCurrentIndex(index)}
                          className={`h-2 rounded-full transition-all ${
                            index === currentIndex ? "w-8 bg-primary" : "w-2 bg-muted-foreground/30"
                          }`}
                        />
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3 mt-6">
                    <Button variant="outline" onClick={onClose} className="flex-1">
                      İptal
                    </Button>
                    <Button onClick={handleAlternativeSelect} className="flex-1 gap-2">
                      <Check className="h-4 w-4" />
                      Bu Aktiviteyi Seç
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
