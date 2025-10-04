'use client';

import { motion } from 'framer-motion';
import { Loader2, Plane, Building, MapPin, Sparkles, Check } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface LoadingStage {
  id: string;
  label: string;
  icon: typeof Loader2;
}

const stages: LoadingStage[] = [
  { id: 'connecting', label: 'Connecting to travel services...', icon: Sparkles },
  { id: 'flights', label: 'Finding best flight options...', icon: Plane },
  { id: 'hotels', label: 'Searching hotels...', icon: Building },
  { id: 'activities', label: 'Planning activities...', icon: MapPin },
  { id: 'finalizing', label: 'Finalizing your perfect trip...', icon: Check },
];

interface PlanLoadingProps {
  currentStage?: string;
  progress?: number;
}

export function PlanLoading({ currentStage = 'connecting', progress = 0 }: PlanLoadingProps) {
  const currentIndex = stages.findIndex(s => s.id === currentStage);

  return (
    <div className="max-w-md mx-auto py-12 space-y-8">
      {/* Animated Logo */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        className="w-16 h-16 mx-auto"
      >
        <Loader2 className="w-full h-full text-blue-500" />
      </motion.div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <Progress value={progress} className="h-2" />
        <p className="text-sm text-center text-muted-foreground">
          {progress}% Complete
        </p>
      </div>

      {/* Stage List */}
      <div className="space-y-3">
        {stages.map((stage, i) => {
          const isActive = currentIndex === i;
          const isComplete = currentIndex > i;
          const Icon = stage.icon;

          return (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`
                flex items-center gap-3 p-3 rounded-lg transition-colors
                ${isActive ? 'bg-blue-50 dark:bg-blue-950' : ''}
              `}
            >
              <div
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center
                  ${isComplete ? 'bg-green-500 text-white' : ''}
                  ${isActive ? 'bg-blue-500 text-white' : 'bg-gray-200'}
                `}
              >
                {isComplete ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Icon className="h-4 w-4" />
                )}
              </div>

              <span className={`text-sm ${isActive ? 'font-medium' : 'text-muted-foreground'}`}>
                {stage.label}
              </span>

              {isActive && (
                <motion.div
                  animate={{ opacity: [0, 1, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="ml-auto"
                >
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                </motion.div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
