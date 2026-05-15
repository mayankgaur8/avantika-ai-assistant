import React from 'react';

interface ProgressBarProps {
  currentXp: number;
  xpNeeded: number;
  level: number;
}

export function ProgressBar({ currentXp, xpNeeded, level }: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (currentXp / xpNeeded) * 100));

  return (
    <div className="w-full bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-bold text-gray-700 dark:text-gray-200">Level {level}</span>
        <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
          {currentXp} / {xpNeeded} XP
        </span>
      </div>
      <div className="h-3 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div 
          className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="text-xs text-right mt-2 text-gray-500 dark:text-gray-400">
        {xpNeeded - currentXp} XP to next level
      </p>
    </div>
  );
}
