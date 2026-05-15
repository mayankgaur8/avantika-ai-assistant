import React from 'react';
import { ProgressBar } from '@/components/dashboard/ProgressBar';
import { StreakFlame } from '@/components/dashboard/StreakFlame';
import { ChatUI } from '@/components/chat/ChatUI';

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6 lg:p-12 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight">
              Welcome back, Explorer! 👋
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Ready to conquer Spanish today?
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            <StreakFlame days={12} active={true} />
            <div className="w-48 hidden md:block">
              <ProgressBar currentXp={1450} xpNeeded={2000} level={4} />
            </div>
          </div>
        </header>

        {/* Mobile progress bar */}
        <div className="md:hidden">
          <ProgressBar currentXp={1450} xpNeeded={2000} level={4} />
        </div>

        {/* Main Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: AI Coach */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-800">
              <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">Conversational Practice</h2>
              <ChatUI />
            </div>
          </div>

          {/* Right Column: Gamification & Stats */}
          <div className="space-y-6">
            <div className="bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-20">
                <svg className="w-24 h-24" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/></svg>
              </div>
              <h3 className="font-bold text-lg mb-2 relative z-10">Daily Quest</h3>
              <p className="text-indigo-100 text-sm mb-4 relative z-10">Complete 3 conversational scenarios to earn the "Chatterbox" badge.</p>
              <div className="w-full bg-black/20 rounded-full h-2 mb-2 relative z-10">
                <div className="bg-white h-2 rounded-full" style={{ width: '33%' }}></div>
              </div>
              <p className="text-xs text-indigo-100 relative z-10">1 / 3 Scenarios</p>
            </div>

            <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-800">
              <h3 className="font-bold text-gray-900 dark:text-white mb-4">Your Badges</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-xl border border-orange-100 dark:border-orange-800/50 flex flex-col items-center text-center">
                  <span className="text-3xl mb-2">🔥</span>
                  <span className="text-xs font-bold text-orange-700 dark:text-orange-400">Early Bird</span>
                </div>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800/50 flex flex-col items-center text-center">
                  <span className="text-3xl mb-2">🧠</span>
                  <span className="text-xs font-bold text-blue-700 dark:text-blue-400">Grammar Master</span>
                </div>
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
