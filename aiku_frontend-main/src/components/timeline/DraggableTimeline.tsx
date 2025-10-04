'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Clock, MapPin, DollarSign, Star, Trash2, RefreshCw,
  GripVertical, Edit2, Check, X
} from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export interface Activity {
  id: string;
  title: string;
  description: string;
  duration?: string;
  price?: string;
  rating?: number;
  category?: string;
  location?: string;
  booking_url?: string;
}

interface TimeSlot {
  id: string;
  day: number;
  startTime: string;
  endTime: string;
  options: Activity[];
  selected?: number;
}

interface DraggableTimelineProps {
  slots: TimeSlot[];
  onReorder: (fromSlot: string, toSlot: string, activityIndex: number) => void;
  onRemove: (slotId: string, activityIndex: number) => void;
  onRequestAlternatives: (slotId: string) => void;
  onTimeAdjust: (slotId: string, startTime: string, endTime: string) => void;
  onActivitySelect: (slotId: string, activityIndex: number) => void;
}

export function DraggableTimeline({
  slots,
  onReorder: _onReorder,
  onRemove,
  onRequestAlternatives,
  onTimeAdjust,
  onActivitySelect: _onActivitySelect
}: DraggableTimelineProps) {
  const [editingTime, setEditingTime] = useState<string | null>(null);
  const [expandedSlots, setExpandedSlots] = useState<Set<string>>(new Set());

  // Initialize all slots as expanded when component mounts or slots change
  useEffect(() => {
    const allSlotIds = new Set(slots.map(slot => slot.id));
    setExpandedSlots(allSlotIds);
  }, [slots]);

  const toggleSlot = (slotId: string) => {
    const newExpanded = new Set(expandedSlots);
    if (newExpanded.has(slotId)) {
      newExpanded.delete(slotId);
    } else {
      newExpanded.add(slotId);
    }
    setExpandedSlots(newExpanded);
  };

  // Calculate unique days
  const uniqueDays = new Set(slots.map(slot => slot.day)).size;

  return (
    <div className="space-y-6">
      {/* Progress Indicator */}
      <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 rounded-lg">
        <div>
          <h3 className="font-semibold">Your Trip Timeline</h3>
          <p className="text-sm text-muted-foreground">
            Reorder with arrows • Adjust times • Build your perfect itinerary
          </p>
        </div>
        <Badge variant="secondary" className="text-lg px-4 py-2">
          {uniqueDays} {uniqueDays === 1 ? 'Day' : 'Days'}
        </Badge>
      </div>

      {/* Timeline Items */}
      {slots.map((slot, idx) => (
        <motion.div
          key={slot.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.05 }}
          className="relative"
        >
          {/* Connecting Line */}
          {idx < slots.length - 1 && (
            <div className="absolute left-8 top-full h-6 w-0.5 bg-gradient-to-b from-blue-500 to-purple-500 z-0" />
          )}

          <Card className="relative overflow-hidden border-2 hover:border-blue-300 transition-all">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                {/* Time Display */}
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  {editingTime === slot.id ? (
                    <TimeEditor
                      startTime={slot.startTime}
                      endTime={slot.endTime}
                      onSave={(start, end) => {
                        onTimeAdjust(slot.id, start, end);
                        setEditingTime(null);
                      }}
                      onCancel={() => setEditingTime(null)}
                    />
                  ) : (
                    <button
                      onClick={() => setEditingTime(slot.id)}
                      className="text-sm font-medium hover:text-blue-600 transition-colors flex items-center gap-1"
                    >
                      {slot.startTime} - {slot.endTime}
                      <Edit2 className="h-3 w-3 ml-1 opacity-50" />
                    </button>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRequestAlternatives(slot.id)}
                  >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Alternatives
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSlot(slot.id)}
                  >
                    {expandedSlots.has(slot.id) ? 'Collapse' : 'Expand'}
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              {/* All Activities - Flow View (No Selection) */}
              <AnimatePresence>
                {expandedSlots.has(slot.id) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="space-y-3 overflow-hidden"
                  >
                    {slot.options.map((activity, i) => (
                      <motion.div
                        key={activity.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="relative"
                      >
                        {/* Connecting Arrow */}
                        {i < slot.options.length - 1 && (
                          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 z-10">
                            <div className="text-blue-500">↓</div>
                          </div>
                        )}
                        
                        <ActivityCard
                          activity={activity}
                          isSelected={false}
                          onSelect={() => {}}
                          onRemove={() => onRemove(slot.id, i)}
                          showGrip={false}
                          showRemove={true}
                        />
                      </motion.div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}

// Get category icon and color
function getCategoryStyle(category?: string) {
  const styles: Record<string, { icon: string; gradient: string; bg: string }> = {
    museum: { icon: '🏛️', gradient: 'from-purple-500 to-pink-500', bg: 'bg-purple-50 dark:bg-purple-950/20' },
    food: { icon: '🍝', gradient: 'from-orange-500 to-red-500', bg: 'bg-orange-50 dark:bg-orange-950/20' },
    culture: { icon: '🎭', gradient: 'from-blue-500 to-purple-500', bg: 'bg-blue-50 dark:bg-blue-950/20' },
    nature: { icon: '🌳', gradient: 'from-green-500 to-teal-500', bg: 'bg-green-50 dark:bg-green-950/20' },
    shopping: { icon: '🛍️', gradient: 'from-pink-500 to-purple-500', bg: 'bg-pink-50 dark:bg-pink-950/20' },
    landmark: { icon: '🗼', gradient: 'from-yellow-500 to-orange-500', bg: 'bg-yellow-50 dark:bg-yellow-950/20' },
    entertainment: { icon: '🎪', gradient: 'from-red-500 to-pink-500', bg: 'bg-red-50 dark:bg-red-950/20' },
    default: { icon: '📍', gradient: 'from-gray-500 to-gray-600', bg: 'bg-gray-50 dark:bg-gray-950/20' }
  };
  return styles[category?.toLowerCase() || ''] || styles.default;
}

// Activity Card Component
function ActivityCard({
  activity,
  isSelected,
  onSelect,
  onRemove,
  showGrip = false,
  showRemove = false
}: {
  activity: Activity;
  isSelected: boolean;
  onSelect: () => void;
  onRemove: () => void;
  showGrip?: boolean;
  showRemove?: boolean;
}) {
  const categoryStyle = getCategoryStyle(activity.category);
  
  return (
    <motion.div
      whileHover={{ scale: showGrip ? 1.01 : 1.02 }}
      whileTap={{ scale: 0.99 }}
      onClick={onSelect}
      className={`
        relative rounded-xl overflow-hidden cursor-pointer transition-all
        ${isSelected 
          ? 'ring-2 ring-blue-500 shadow-lg' 
          : 'border-2 border-gray-200 hover:border-blue-300 hover:shadow-md'
        }
      `}
    >
      {/* Drag Handle */}
      {showGrip && (
        <div className="absolute left-2 top-1/2 -translate-y-1/2 cursor-grab active:cursor-grabbing z-10">
          <GripVertical className="h-5 w-5 text-white opacity-80" />
        </div>
      )}

      {/* Gradient Header */}
      <div className={`bg-gradient-to-r ${categoryStyle.gradient} px-4 py-3 text-white relative`}>
        <div className="flex items-start justify-between">
          <div className={`flex items-center gap-2 ${showGrip ? 'ml-6' : ''}`}>
            <span className="text-2xl">{categoryStyle.icon}</span>
            <div className="flex-1">
              <h4 className="font-bold text-sm mb-0.5">{activity.title}</h4>
              {activity.category && (
                <Badge variant="secondary" className="text-xs bg-white/20 hover:bg-white/30 border-0">
                  {activity.category}
                </Badge>
              )}
            </div>
          </div>
          
          {/* Remove Button */}
          {showRemove && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 hover:bg-white/20 text-white"
              onClick={(e) => {
                e.stopPropagation();
                onRemove();
              }}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Card Body */}
      <div className={`p-4 ${categoryStyle.bg}`}>
        {/* Description */}
        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
          {activity.description}
        </p>

        {/* Metadata */}
        <div className="flex items-center gap-4 text-xs">
          {activity.duration && (
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {activity.duration}
            </div>
          )}
          {activity.price && (
            <div className="flex items-center gap-1 text-green-600 dark:text-green-400 font-medium">
              <DollarSign className="h-3 w-3" />
              {activity.price}
            </div>
          )}
          {activity.rating && (
            <div className="flex items-center gap-1">
              <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
              {activity.rating}
            </div>
          )}
          {activity.location && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <MapPin className="h-3 w-3" />
              {activity.location}
            </div>
          )}
        </div>
      </div>

      {/* Selected Checkmark */}
      <AnimatePresence>
        {isSelected && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            className="absolute top-2 right-2 bg-blue-500 text-white rounded-full p-1.5"
          >
            <Check className="h-4 w-4" />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// Time Editor Component
function TimeEditor({
  startTime,
  endTime,
  onSave,
  onCancel
}: {
  startTime: string;
  endTime: string;
  onSave: (start: string, end: string) => void;
  onCancel: () => void;
}) {
  const [start, setStart] = useState(startTime);
  const [end, setEnd] = useState(endTime);

  return (
    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
      <input
        type="time"
        value={start}
        onChange={(e) => setStart(e.target.value)}
        className="px-2 py-1 text-sm border rounded"
      />
      <span>-</span>
      <input
        type="time"
        value={end}
        onChange={(e) => setEnd(e.target.value)}
        className="px-2 py-1 text-sm border rounded"
      />
      <Button
        size="sm"
        variant="ghost"
        onClick={() => onSave(start, end)}
        className="h-7 w-7 p-0"
      >
        <Check className="h-4 w-4 text-green-600" />
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={onCancel}
        className="h-7 w-7 p-0"
      >
        <X className="h-4 w-4 text-destructive" />
      </Button>
    </div>
  );
}
