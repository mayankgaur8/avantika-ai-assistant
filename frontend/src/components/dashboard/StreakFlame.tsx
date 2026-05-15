import React from 'react';
import { Flame } from 'lucide-react';

interface StreakFlameProps {
  days: number;
  active: boolean;
}

export function StreakFlame({ days, active }: StreakFlameProps) {
  return (
    <div className={`flex items-center space-x-2 px-4 py-2 rounded-full border ${active ? 'bg-orange-50 border-orange-200 dark:bg-orange-950/30 dark:border-orange-800' : 'bg-gray-50 border-gray-200 dark:bg-gray-800 dark:border-gray-700'}`}>
      <Flame className={`w-5 h-5 ${active ? 'text-orange-500 fill-orange-500 animate-pulse' : 'text-gray-400'}`} />
      <span className={`font-bold ${active ? 'text-orange-600 dark:text-orange-400' : 'text-gray-500 dark:text-gray-400'}`}>
        {days} Day Streak
      </span>
    </div>
  );
}
